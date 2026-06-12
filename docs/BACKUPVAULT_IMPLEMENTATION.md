# BackupVault — step-by-step integration with telegram-uploader

> **Status: SIDE PROJECT (future) — not part of telegram-uploader v1**
>
> This document is a **planned joint project** with a DevOps partner (separate `backupvault` repo).  
> **Do not implement** anything from this guide while finishing [PROJECT.md](PROJECT.md) / [BACKLOG.md](BACKLOG.md).  
> Return here **after** telegram-uploader v1 is stable (backup happy path, restore, P-demo).  
> telegram-uploader stays a **standalone system**; BackupVault connects externally later (read-only Postgres DSN only).

How to build **BackupVault** as a separate service that protects the **restore catalog** of `telegram-uploader`: PostgreSQL metadata (`upload_sessions`, `source_items`, `archive_volumes`) plus optional **E2E drills** against Telegram volumes.

**Not in scope:** OwnCloud, syncing user source files, or replacing Telegram as cold storage.  
**In scope:** scheduled `pg_dump`, object storage, automated restore drills, alerts when the chain *catalog → Telegram download* breaks.

**Related:**

| Document | Role |
|----------|------|
| [PROJECT.md](PROJECT.md) | What telegram-uploader is, stack, upgrade order |
| [INTERNAL_SPEC.md](INTERNAL_SPEC.md) | Restore metadata fields that drills must validate |
| [PROJECT.md](PROJECT.md) §10 | Gate + smoke rules (mandatory) |
| [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) | Bot, group, `.env` for E2E drills |

---

## 0) Problem statement (why this exists)

`telegram-uploader` stores **two assets**:

| Asset | Location | If lost |
|-------|----------|---------|
| Encrypted archive volumes | Telegram group | Files exist but are unmapped noise |
| Restore catalog | PostgreSQL (`postgres-data` volume) | You know *what* to restore but lose `encryption_key`, `external_file_id`, `display_name` |

BackupVault answers: **«Will I actually recover after `docker volume rm postgres-data` or a dead laptop?»**

Current project status (see [PROJECT.md](PROJECT.md)): backup path works; restore download may return **HTTP 404**. BackupVault E2E drills surface that **before** a disaster.

---

## 0.5) Collaboration model — who does what, who pushes what

**Common confusion:** BackupVault is **not** «Roman's app builds itself through Roman's app».  
**Reality:** two Git repos, two runtimes, one integration point (read-only Postgres + Telegram probe).

### What Roman pushes (Git)

| Repo | Contents | Who deploys |
|------|----------|-------------|
| `telegram-uploader` | GUI, workers, Telegram provider, migrations | Roman → **weak PC** (app host) |
| `backupvault` | FastAPI, Celery jobs, SQL validators, tests | Roman writes code → **friend deploys** to server PC |

Roman does **not** send dump files to the friend. Roman pushes **code**. Automation pulls dumps from a **running** Postgres.

### What the friend configures (no Git — secrets & infra)

| Item | Where stored | Example |
|------|--------------|---------|
| `backupvault_ro` password | server PC `.env` / Ansible vault | never in Git |
| DSN to Roman's Postgres | BackupVault secrets | `postgresql://backupvault_ro:***@192.168.1.20:5433/telegram_uploader` |
| Telegram tokens (E2E drill) | BackupVault secrets | copy from Roman's `.env` once |
| MinIO keys, Grafana admin | server PC | friend manages |
| Firewall rules | weak PC + server PC | friend manages |

### Weekly sync (30 min)

1. Roman demos: GUI session / API status / pytest green  
2. Friend demos: Grafana panel / last backup job / alert test  
3. One gate from phase map — close or block next phase  
4. Update shared doc: IPs, hostnames, open issues  

### What DevOps is **not** here

| ❌ Not the job | ✅ Actual DevOps job |
|---------------|---------------------|
| «Store files in OwnCloud» | Run platform: MinIO + workers + monitoring 24/7 |
| «Receive dumps from Roman» | Worker pulls `pg_dump` over network on schedule |
| «Build telegram-uploader» | Optional separate CI track (`.deb` / images) |
| «Click in GUI» | DR runbook, alerts, sandbox isolation, Terraform/Ansible |

**Resume one-liner for friend:** *Built multi-host backup observability platform: automated PostgreSQL backups, restore drills, E2E integrity checks, Grafana alerting — protecting a production-like Telegram backup application.*

---

## 1) Architecture overview

```mermaid
flowchart LR
    subgraph tu["telegram-uploader (existing repo)"]
        PG[(Postgres catalog)]
        TG[Telegram volumes]
        W[Celery workers]
        W --> PG
        W --> TG
    end

    subgraph bv["backupvault (new repo)"]
        API[FastAPI API]
        BVDB[(backupvault Postgres)]
        BW[backup worker]
        RW[restore-drill worker]
        EW[e2e-verify worker]
        API --> BVDB
        BW --> API
        RW --> API
        EW --> API
    end

    subgraph ops["infra (friend)"]
        S3[(MinIO / S3)]
        MON[Grafana + alerts]
    end

    BW -->|pg_dump read-only| PG
    BW --> S3
    RW -->|pg_restore sandbox| S3
    EW -->|download 1 volume| TG
    RW --> MON
    EW --> MON
```

**Repository layout:**

```text
~/Projects/
├── telegram-uploader/     # unchanged onion app; minimal integration hooks
└── backupvault/           # new FastAPI + Celery service
```

**Boundary rule:** BackupVault is an **external inspector**. It must **not** import `telegram-uploader` onion layers. Integration = DSN, SQL validators, optional copy of Telegram HTTP client for drills.

---

## 1.5) Multi-device lab — «real environment» for resume

Use **four machines** on one LAN (home router). This is enough to demonstrate production-like separation: **app host ≠ backup/monitoring host**.

### Hardware map

| Machine | Owner | Role | Runs |
|---------|-------|------|------|
| **Laptop A** | Roman | Dev workstation | IDE, Git, **GUI only** (Tkinter), SSH to weak PC |
| **Weak PC** | Roman | **App host** (`tu-app`) | `docker compose`: postgres, redis, celery workers, `telegram-bot-api` |
| **Server PC** | Friend | **Ops host** (`bv-ops`) | BackupVault stack, MinIO, Grafana, Prometheus, sandbox Postgres |
| **Laptop B** | Friend | Dev workstation | IDE, Terraform, Ansible, SSH to server PC, CI config |

### Is weak PC + laptop enough for telegram-uploader?

**Yes**, with this split:

| Component | Machine | Notes |
|-----------|---------|-------|
| GUI | Laptop A | Lightweight; connects to Postgres on weak PC over LAN |
| Postgres + Redis + workers + bot-api | Weak PC | Minimum **4 GB RAM**, **2 CPU**, **30 GB** free disk |
| Heavy parallel archive | Weak PC | Keep **1** archive worker if RAM tight (stop `celery-worker-archive-2`) |

Weak PC does **not** need a monitor after setup — SSH from laptop is fine.

### Is server PC + laptop enough for BackupVault?

**Yes.** Recommended server PC: **8 GB RAM**, **4 CPU**, **50 GB** disk (MinIO dumps + metrics).

| Service | Approx RAM |
|---------|------------|
| backupvault api + worker + redis + postgres | ~1 GB |
| MinIO | ~512 MB |
| postgres-sandbox | ~256 MB |
| Prometheus + Grafana | ~1–2 GB |
| Headroom | rest |

Friend's laptop is only for editing infra code — **no need** to run stacks locally if server PC is up.

### Network topology (example IPs — replace with yours)

```text
                    [ Home router 192.168.1.1 ]
                              |
        +---------------------+---------------------+
        |                     |                     |
   Laptop A              Weak PC (tu-app)      Server PC (bv-ops)
   192.168.1.10          192.168.1.20          192.168.1.30
   GUI, git              postgres :5433         BackupVault :8000
                         redis :6379              MinIO :9000
                         bot-api :8081            Grafana :3000
                              ^                         |
                              |    backupvault_ro       |
                              +-------- pg_dump --------+
                              |    (TCP 5433 only)      |
                              +---- E2E HTTPS ----------> Telegram Cloud
```

**Hostname tip (optional):** add to `/etc/hosts` on both laptops:

```text
192.168.1.20  tu-app.lan
192.168.1.30  bv-ops.lan
```

### Port matrix

| Port | Host | Service | Exposed to |
|------|------|---------|------------|
| 5433 | tu-app (weak PC) | telegram-uploader Postgres | **bv-ops IP only** (UFW) |
| 6379 | tu-app | Redis | LAN or localhost only — **not** bv-ops |
| 8081 | tu-app | telegram-bot-api | LAN (Roman laptop GUI); bv-ops for E2E |
| 8000 | bv-ops | BackupVault API | LAN |
| 9000 | bv-ops | MinIO API | LAN / bv-ops only |
| 9001 | bv-ops | MinIO console | friend laptop |
| 3000 | bv-ops | Grafana | LAN |
| 9090 | bv-ops | Prometheus | LAN |

### Roman: move telegram-uploader to weak PC (one-time)

On **weak PC** (`tu-app`):

```bash
git clone <telegram-uploader-repo> ~/telegram-uploader
cd ~/telegram-uploader
cp .env.example .env
# edit .env — see below
docker compose up -d
```

On **weak PC** `.env` (container-internal — keep compose defaults):

```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
TELEGRAM_BOT_API_URL=http://telegram-bot-api:8081
```

On **Laptop A** `.env` (GUI + host tools point at weak PC):

```env
POSTGRES_HOST=192.168.1.20
POSTGRES_PORT=5433
TELEGRAM_BOT_API_URL=http://192.168.1.20:8081
```

In `docker-compose.yml` on weak PC, Postgres port mapping stays `"5433:5432"` — already present.

Smoke from laptop:

```bash
psql -h 192.168.1.20 -p 5433 -U telegram_uploader -d telegram_uploader -c "SELECT 1;"
PYTHONPATH=src .venv/bin/python -m application.gui
```

### Resume bullets (after P4 gate)

**Roman (backend):**

- Designed BackupVault control plane (FastAPI, Celery) with automated restore drills and Telegram E2E integrity checks  
- Integrated external backup inspector with PostgreSQL catalog for messenger-based backup application  

**Friend (DevOps):**

- Deployed multi-host observability stack (Prometheus, Grafana, MinIO) across dedicated app and ops servers  
- Hardened cross-host PostgreSQL backup access (read-only role, UFW), lifecycle policies, and DR runbook with measured RTO  

**Together:**

- End-to-end disaster recovery demo: catalog destruction on app host → automated restore from ops host → application operational  

---

## 2) Roles

### Roman (backend / application owner)

| Area | Tasks |
|------|-------|
| `telegram-uploader` | Features, GUI, workers, migrations |
| `backupvault` code | API, Celery tasks, validators, pytest, CI workflow YAML |
| Integration spec | SQL validators, E2E probe contract, handoff doc for DSN |
| Smoke | GUI backup session; confirm catalog rows exist for drills |

### Friend (DevOps / platform owner)

| Area | Tasks |
|------|-------|
| **Platform** | Server PC provisioning, Docker, static IP/hostname |
| **Network & security** | UFW, allow only bv-ops → tu-app:5433; secrets management |
| **Storage ops** | MinIO install, bucket policy, lifecycle, versioning — not «file sharing» |
| **Observability** | Prometheus scrape, Grafana dashboards, alert rules, Telegram/email notifications |
| **Automation** | Ansible playbooks, Terraform modules (staging), GitHub/GitLab deploy pipeline |
| **Reliability** | Sandbox Postgres isolation, job log retention, DR runbook + **solo rehearsal** |
| **Optional** | CI/CD for `telegram-uploader` `.deb` (separate from BackupVault) |

### Both

- Gate/smoke per phase; English UI strings in BackupVault  
- 30 min weekly sync; shared IP/secret checklist (not secrets themselves in chat)  

---

## 2.5) Friend onboarding — software & access (before P0)

Complete on **Laptop B** and **Server PC** before writing infra code.

### Server PC (`bv-ops`) — base OS

Recommended: **Ubuntu 24.04 LTS** or **Debian 12** (matches friend's Linux admin skills).

```bash
# Run on server PC (friend)
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  ca-certificates curl gnupg git jq ufw ansible \
  python3-pip python3-venv
```

### Docker Engine + Compose plugin

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker "$USER"
# re-login, then:
docker compose version
```

### Friend laptop (Laptop B) — tooling

| Tool | Purpose |
|------|---------|
| Git | clone `backupvault`, `telegram-uploader` (read-only understanding) |
| SSH key | passwordless `ssh friend@192.168.1.30` |
| Ansible | run playbooks against bv-ops (and optionally tu-app with Roman's OK) |
| Terraform ≥ 1.5 | optional P0/P4; local state OK for homelab |
| `psql` client | test `backupvault_ro` connectivity to tu-app |
| VS Code / Cursor | edit infra repos |

```bash
# Laptop B
sudo apt install -y postgresql-client ansible terraform git
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_bvops
ssh-copy-id -i ~/.ssh/id_ed25519_bvops friend@192.168.1.30
```

### Access Roman must grant

| Access | How | When |
|--------|-----|------|
| Git repo `backupvault` | collaborator on GitHub/GitLab | P0 |
| Git repo `telegram-uploader` | read access (schema + compose) | P0 |
| SSH to weak PC **optional** | Roman creates `friend` user, limited sudo | P1 (create `backupvault_ro`) |
| LAN reachability tu-app:5433 | Roman configures UFW | P1 |
| Telegram `.env` values | secure channel (not Git) | P3 |
| Grafana URL | `http://192.168.1.30:3000` | P4 |

### Server PC — static IP

Set **192.168.1.30** (example) via router DHCP reservation or netplan:

```yaml
# /etc/netplan/01-static.yaml (example — adjust interface name)
network:
  version: 2
  ethernets:
    enp0s3:
      addresses: [192.168.1.30/24]
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [192.168.1.1, 8.8.8.8]
```

```bash
sudo netplan apply
```

### Repository layout on server PC

```text
/home/friend/
├── backupvault/          # git clone; docker compose up here
├── infra/
│   ├── terraform/        # minio bucket module, optional
│   ├── ansible/
│   │   ├── inventory/hosts.yml
│   │   └── playbooks/
│   │       ├── bv-ops.yml
│   │       └── tu-app-ufw.yml   # run with Roman's approval
│   └── monitoring/
│       ├── prometheus.yml
│       └── grafana/dashboards/
```

---

## 3) Prerequisites

### Roman checklist (Laptop A + weak PC `tu-app`)

- [ ] telegram-uploader cloned and running on **weak PC** (`docker compose up -d`)
- [ ] Laptop A GUI connects to `192.168.1.20:5433` (see §1.5)
- [ ] At least **one completed backup session** ([PROJECT.md](PROJECT.md) happy path)
- [ ] `.env` on weak PC filled per [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)
- [ ] Catalog query works **from server PC** (friend will need this):

```bash
# Run from bv-ops (friend tests in P1)
psql -h 192.168.1.20 -p 5433 -U telegram_uploader -d telegram_uploader -c \
  "SELECT status, count(*) FROM upload_sessions GROUP BY status;"
```

- [ ] Weak PC has **static LAN IP** (e.g. `192.168.1.20`) — DHCP reservation on router
- [ ] Share with friend: `tu-app` IP, telegram-uploader Git URL, planned `backupvault` Git URL

### Friend checklist (Laptop B + server PC `bv-ops`)

- [ ] §2.5 onboarding done (Docker, SSH, static IP on bv-ops)
- [ ] Can `ping 192.168.1.20` from bv-ops
- [ ] `backupvault` repo cloned on bv-ops (after Roman creates P0 skeleton)
- [ ] Inventory file written:

```yaml
# infra/ansible/inventory/hosts.yml
all:
  children:
    ops:
      hosts:
        bv-ops:
          ansible_host: 192.168.1.30
    app:
      hosts:
        tu-app:
          ansible_host: 192.168.1.20
          ansible_user: roman   # or dedicated user
```

### Shared decisions (30 min kickoff meeting)

| Decision | Recommendation |
|----------|----------------|
| Object storage | MinIO in compose for dev; S3/GCS for staging |
| BackupVault repo | `backupvault` on GitHub/GitLab, Python 3.12, same quality bar (ruff, mypy, pytest) |
| Schedules | Backup daily 03:00; restore drill weekly Sun 04:00 |
| Alert channel | Telegram bot → private group (reuse existing bot or separate) |

---

## 4) Phase map

| Phase | Goal | Gate |
|-------|------|------|
| **P0** | Repo + compose skeleton | `docker compose up` for backupvault stack |
| **P1** | Register target + manual backup to S3 | dump file in bucket + checksum in API |
| **P2** | Restore drill (DB only) | sandbox restore + validators green |
| **P3** | E2E drill (Telegram download) | drill detects real 404 or success |
| **P4** | Ops hardening | Grafana dashboard + friend runbook tested |

**Do not start P(n+1) until P(n) gate is closed** ([PROJECT.md](PROJECT.md) §10).

---

## 5) P0 — BackupVault skeleton (week 1)

### 5.1 Roman: create `backupvault` repo

```text
backupvault/
├── src/
│   ├── domain/              # Target, BackupRun, DrillRun, statuses
│   ├── use_cases/           # RegisterTarget, RunBackup, RunRestoreDrill, RunE2eDrill
│   ├── infrastructure/    # SQLAlchemy, Celery, S3 client, pg_dump runner
│   └── application/       # FastAPI app, CLI
├── tests/
├── docker-compose.yml
├── pyproject.toml
└── docs/
```

Mirror onion discipline from telegram-uploader: `application` → `infrastructure` → `use_cases` → `domain`.

### 5.2 Roman: minimal `docker-compose.yml`

Services:

| Service | Image / build | Purpose |
|---------|---------------|---------|
| `backupvault-api` | Dockerfile | FastAPI on `:8000` |
| `backupvault-worker` | same image | Celery worker |
| `backupvault-postgres` | `postgres:16-alpine` | BackupVault metadata |
| `backupvault-redis` | `redis:7-alpine` | Celery broker |
| `minio` | `minio/minio` | S3-compatible storage |
| `postgres-sandbox` | `postgres:16-alpine` | **Isolated** restore-drill target (empty on start) |

`postgres-sandbox` must **not** share volumes with telegram-uploader `postgres-data`.

### 5.3 Friend: step-by-step (P0 — ops host ready)

**Goal:** server PC runs empty BackupVault stack; Roman's app untouched on weak PC.

#### Step F0-1 — Prepare bv-ops directories

```bash
ssh bv-ops
mkdir -p ~/backupvault ~/infra/{terraform,ansible/inventory,ansible/playbooks,monitoring}
```

#### Step F0-2 — Clone repo after Roman pushes P0 skeleton

```bash
cd ~/backupvault
git clone <backupvault-repo-url> .
cp .env.example .env
```

Edit `~/backupvault/.env` on **bv-ops**:

```env
APP_ENV=homelab
MINIO_ROOT_USER=backupvault
MINIO_ROOT_PASSWORD=<generate-strong>
MINIO_BUCKET=backupvault-dumps
BACKUPVAULT_POSTGRES_PASSWORD=<generate-strong>
```

#### Step F0-3 — Start stack on bv-ops only

```bash
cd ~/backupvault
docker compose up -d
docker compose ps   # all healthy
curl -s http://localhost:8000/health
```

MinIO console: `http://192.168.1.30:9001` — create bucket `backupvault-dumps` if not auto-created.

#### Step F0-4 — UFW on bv-ops (allow LAN admin, deny WAN)

```bash
sudo ufw default deny incoming
sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp
sudo ufw allow from 192.168.1.0/24 to any port 9001 proto tcp
sudo ufw enable
sudo ufw status
```

#### Step F0-5 — Ansible baseline playbook (friend)

```yaml
# infra/ansible/playbooks/bv-ops.yml
- hosts: ops
  become: true
  tasks:
    - name: Ensure Docker started
      service:
        name: docker
        state: started
        enabled: true
    - name: Create backupvault deploy dir
      file:
        path: /home/friend/backupvault
        state: directory
        owner: friend
        group: friend
```

```bash
# Laptop B
cd infra/ansible
ansible-playbook -i inventory/hosts.yml playbooks/bv-ops.yml
```

#### Step F0-6 — Terraform stub (optional)

```hcl
# infra/terraform/minio_bucket/main.tf — local homelab documents intent
variable "bucket_name" { default = "backupvault-dumps" }
output "endpoint" { value = "http://192.168.1.30:9000" }
```

Friend commits `infra/` to `backupvault` repo under `deploy/` or separate `backupvault-infra` repo.

**P0 friend deliverable:** bv-ops IP written in shared doc; `curl health` works from Laptop B; MinIO bucket exists.

### 5.4 Gate P0

```bash
cd backupvault
docker compose up -d
curl -s http://localhost:8000/health | jq .
# → {"status":"ok"}
```

---

## 6) P1 — Protect telegram-uploader catalog (week 2)

### 6.1 Friend: step-by-step (P1 — cross-host backup)

**Goal:** bv-ops worker dumps tu-app Postgres nightly; Roman never sends files manually.

#### Step F1-1 — UFW on weak PC (`tu-app`) — Roman runs, friend documents

Allow **only** bv-ops to reach Postgres:

```bash
# On tu-app (weak PC) — Roman executes
sudo ufw allow from 192.168.1.30 to any port 5433 proto tcp comment 'backupvault bv-ops'
sudo ufw enable
```

Verify from **bv-ops**:

```bash
nc -zv 192.168.1.20 5433
```

#### Step F1-2 — Create read-only role (Roman or friend over SSH)

On **tu-app**:

```bash
cd ~/telegram-uploader
docker compose exec postgres psql -U telegram_uploader -d telegram_uploader
```

```sql
CREATE ROLE backupvault_ro LOGIN PASSWORD 'change_me_strong';
GRANT CONNECT ON DATABASE telegram_uploader TO backupvault_ro;
GRANT USAGE ON SCHEMA public TO backupvault_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backupvault_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO backupvault_ro;
```

Test from **bv-ops**:

```bash
psql "postgresql://backupvault_ro:change_me_strong@192.168.1.20:5433/telegram_uploader" \
  -c "SELECT count(*) FROM upload_sessions;"
```

Negative test (must fail):

```bash
psql "postgresql://backupvault_ro:...@192.168.1.20:5433/telegram_uploader" \
  -c "DELETE FROM upload_sessions;"
# → permission denied
```

#### Step F1-3 — Store secrets on bv-ops only

```bash
# /home/friend/backupvault/.env (chmod 600) — friend manages
TARGET_TU_DSN=postgresql://backupvault_ro:change_me_strong@192.168.1.20:5433/telegram_uploader
```

For Celery worker in Docker, use LAN IP — **not** `host.docker.internal` (worker runs on Linux bv-ops, target is remote tu-app).

#### Step F1-4 — MinIO lifecycle (friend)

Via MinIO console or `mc`:

```bash
docker run --rm -it --entrypoint /bin/sh minio/mc -c "
  mc alias set bv http://192.168.1.30:9000 backupvault '<password>';
  mc mb -p bv/backupvault-dumps || true;
  mc version enable bv/backupvault-dumps;
"
```

Document retention rule: delete objects older than 30 days (lifecycle JSON in `deploy/minio-lifecycle.json`).

#### Step F1-5 — First manual backup (Roman triggers API, friend watches logs)

```bash
# Laptop A or bv-ops
curl -X POST http://192.168.1.30:8000/api/v1/targets/<id>/backup-runs
ssh bv-ops 'cd ~/backupvault && docker compose logs -f backupvault-worker'
```

Friend verifies object in MinIO: `telegram-uploader-dev/<timestamp>.dump`.

#### Step F1-6 — Prometheus metric stub (friend, optional in P1)

Expose worker metric `backupvault_backup_success` — full dashboard in P4.

**P1 friend deliverable:** cross-host `pg_dump` succeeds; object in MinIO; UFW documented; DSN not in Git.

### 6.2 Roman: register target via API

```http
POST /api/v1/targets
Content-Type: application/json

{
  "slug": "telegram-uploader-dev",
  "display_name": "telegram-uploader (dev)",
  "engine": "postgres",
  "connection_secret_ref": "targets/tu-dev/dsn",
  "schedule_cron": "0 3 * * *",
  "retention_days": 30,
  "labels": {
    "app": "telegram-uploader",
    "env": "development"
  }
}
```

BackupVault stores **connection ref**, not raw password, in its DB.

### 6.3 Roman: `backup_job` Celery task

Pipeline:

1. Resolve DSN from secret store
2. Run `pg_dump -Fc --no-owner --no-acl` (subprocess or `docker run postgres:16` with network to TU postgres)
3. Compute `sha256`
4. Upload to `s3://backupvault-dumps/telegram-uploader-dev/YYYY-MM-DDTHHMMSS.dump`
5. Insert `backup_runs` row: `status=success`, `size_bytes`, `checksum`, `storage_uri`

Tables (BackupVault DB):

```sql
-- illustrative; implement via migrations in backupvault repo
CREATE TABLE targets (
    id UUID PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    engine TEXT NOT NULL,
    connection_secret_ref TEXT NOT NULL,
    schedule_cron TEXT NOT NULL,
    retention_days INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE backup_runs (
    id UUID PRIMARY KEY,
    target_id UUID NOT NULL REFERENCES targets(id),
    status TEXT NOT NULL,
    storage_uri TEXT,
    size_bytes BIGINT,
    checksum_sha256 TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ
);
```

### 6.4 Roman: manual trigger + status endpoint

```http
POST /api/v1/targets/{id}/backup-runs
GET  /api/v1/targets/{id}/backup-runs/latest
```

### 6.5 Friend: MinIO lifecycle

- Expire objects older than `retention_days`
- Enable bucket versioning (protect against accidental overwrite)

### 6.6 Smoke P1 (Roman, manual)

1. Ensure telegram-uploader has ≥1 `completed` session
2. `POST .../backup-runs` → wait for `status=success`
3. Open MinIO console → object exists
4. **Disaster rehearsal (read-only):** note checksum from API

### 6.7 Gate P1

- [ ] Latest backup run `success`
- [ ] `sha256` reproducible on re-download from MinIO
- [ ] `backupvault_ro` cannot `INSERT`/`UPDATE` (verify with `\conninfo` + failed insert test)

---

## 7) P2 — Restore drill: «does the catalog come back?» (week 3)

### 7.1 What we validate

After `pg_restore` into `postgres-sandbox`, run validators against **telegram-uploader schema** ([0001_initial.sql](../src/infrastructure/db/migrations/0001_initial.sql)):

| Validator ID | SQL / rule | Meaning |
|--------------|------------|---------|
| `schema_migrations_applied` | table `schema_migrations` exists | dump is from real app |
| `sessions_exist` | `SELECT count(*) FROM upload_sessions` ≥ 1 | not empty noise |
| `uploaded_volumes_have_refs` | no row with `status='uploaded' AND external_file_id IS NULL` | [INTERNAL_SPEC.md](INTERNAL_SPEC.md) §4 |
| `display_name_present` | no `source_items` with `display_name = ''` | [INTERNAL_SPEC.md](INTERNAL_SPEC.md) §6 |
| `encryption_key_present` | no `upload_sessions` with `encryption_key = ''` | restore needs key |

Implement validators as pluggable checks in `use_cases/validators/telegram_uploader.py` (in **backupvault** repo).

### 7.2 Roman: `restore_drill_job`

1. Pick latest successful `backup_runs.storage_uri`
2. Download dump to temp dir
3. `pg_restore --clean --if-exists -d postgres://sandbox...` (target: `postgres-sandbox` service)
4. Run all validators → store `drill_runs` + per-check results
5. **Always** tear down sandbox DB (`DROP SCHEMA public CASCADE` or recreate container)

```http
POST /api/v1/targets/{id}/restore-drills
GET  /api/v1/targets/{id}/restore-drills/latest
```

Response example:

```json
{
  "status": "success",
  "backup_run_id": "...",
  "checks": [
    {"id": "uploaded_volumes_have_refs", "ok": true},
    {"id": "sessions_exist", "ok": true, "detail": "12 sessions"}
  ],
  "duration_seconds": 18
}
```

### 7.3 Friend: step-by-step (P2 — sandbox restore drill)

**Goal:** restore drill runs on **bv-ops only**; tu-app prod Postgres never touched by `pg_restore`.

#### Step F2-1 — Isolate sandbox network in `backupvault/docker-compose.yml`

Friend adds (conceptual):

```yaml
networks:
  drill-net:
    internal: false   # needs outbound to MinIO only
services:
  postgres-sandbox:
    networks: [drill-net]
  backupvault-worker:
    networks: [default, drill-net]
```

Worker env:

```env
SANDBOX_DSN=postgresql://sandbox:sandbox@postgres-sandbox:5432/sandbox
```

**No route** from `postgres-sandbox` to `192.168.1.20` — do not attach sandbox to host network.

#### Step F2-2 — Ansible playbook `restore_drill_host.yml`

```yaml
- hosts: ops
  tasks:
    - name: Recreate sandbox postgres before drill (optional clean slate)
      community.docker.docker_container:
        name: backupvault-postgres-sandbox-1
        state: started
      # or: docker compose restart postgres-sandbox
    - name: Verify worker can reach MinIO
      uri:
        url: http://localhost:9000/minio/health/live
```

#### Step F2-3 — Run automated drill (friend monitors)

```bash
curl -X POST http://192.168.1.30:8000/api/v1/targets/<id>/restore-drills
curl -s http://192.168.1.30:8000/api/v1/targets/<id>/restore-drills/latest | jq .
```

#### Step F2-4 — Controlled disaster on tu-app (joint smoke)

| Step | Who | Machine |
|------|-----|---------|
| Stop workers + GUI | Roman | Laptop A / tu-app |
| `docker volume rm` postgres-data | Roman | tu-app |
| Recreate empty postgres | Roman | tu-app |
| `pg_restore` from MinIO dump | **Friend** | bv-ops (downloads + restores over network to tu-app) |
| Verify GUI shows old sessions | Roman | Laptop A |

Friend restores **to tu-app** using:

```bash
# bv-ops: download latest dump
mc cp bv/backupvault-dumps/telegram-uploader-dev/<latest>.dump /tmp/latest.dump
pg_restore -h 192.168.1.20 -p 5433 -U telegram_uploader -d telegram_uploader --clean --if-exists /tmp/latest.dump
```

Roman grants temporary restore permission or runs `pg_restore` locally with friend on call — document chosen model in runbook.

**P2 friend deliverable:** automated drill green; solo restore procedure timed (target RTO 45 min documented).

### 7.4 Smoke P2 (Roman + friend, multi-device)

**On tu-app (weak PC)** — Roman:

```bash
cd ~/telegram-uploader
docker compose stop app celery-worker-archive-1 celery-worker-archive-2 \
  celery-worker-upload celery-worker-cleanup celery-worker-restore
docker compose stop postgres
docker volume rm telegram-uploader_postgres-data   # docker volume ls if name differs
docker compose up -d postgres
# wait healthy
```

**On bv-ops (server PC)** — Friend:

```bash
mc cp bv/backupvault-dumps/telegram-uploader-dev/<latest>.dump /tmp/latest.dump
pg_restore -h 192.168.1.20 -p 5433 -U telegram_uploader -d telegram_uploader \
  --clean --if-exists /tmp/latest.dump
```

**On Laptop A** — Roman: start workers + GUI → old sessions visible.

Record wall-clock time in runbook (target RTO ≤ 45 min on homelab).

### 7.5 Gate P2

- [ ] Automated `restore_drill_job` → all validators green
- [ ] Manual disaster rehearsal: catalog back, GUI lists old sessions
- [ ] Sandbox restore **never** touched prod volume

---

## 8) P3 — E2E drill: «can we still download from Telegram?» (week 4)

### 8.1 Why this is separate from P2

P2 proves **metadata** restores. P3 proves **Telegram volumes** referenced by `external_file_id` / `provider_download_ref` are still reachable — the current gap in [PROJECT.md](PROJECT.md) (restore 404).

### 8.2 Roman: `e2e_drill_job`

Algorithm:

1. After successful restore drill, connect to **sandbox** Postgres (read-only)
2. Pick one session:

```sql
SELECT s.id
FROM upload_sessions s
WHERE s.status = 'completed'
ORDER BY s.created_at DESC
LIMIT 1;
```

3. Load its volumes:

```sql
SELECT av.id, av.file_name, av.external_file_id, av.provider_download_ref, av.part_number
FROM archive_volumes av
JOIN source_items si ON si.id = av.source_item_id
WHERE si.session_id = :session_id AND av.status = 'uploaded'
ORDER BY av.part_number
LIMIT 1;
```

4. Download **one** volume using same HTTP contract as `TelegramProviderV1` ([src/infrastructure/providers/telegram_provider.py](../src/infrastructure/providers/telegram_provider.py)):
   - `TELEGRAM_BOT_API_URL`
   - `TELEGRAM_BOT_TOKEN`
   - Bot API file download endpoint
5. Verify:
   - HTTP 200
   - File size > 0
   - First bytes match `7z` archive magic (`37 7A BC AF 27 1C`)
6. Store `e2e_drill_runs` with `telegram_http_status`, `bytes_downloaded`, `magic_ok`

Secrets for drill: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_API_URL` in BackupVault env (same values as telegram-uploader `.env`).

### 8.3 Friend: step-by-step (P3 — E2E Telegram probe + alerts)

**Goal:** bv-ops worker tests Telegram download; alert fires on 404 (expected until Client API migration).

#### Step F3-1 — Copy Telegram secrets to bv-ops `.env`

Roman sends via secure channel (Signal/Bitwarden send — **not** Git):

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_BOT_API_URL=http://192.168.1.20:8081
TELEGRAM_TARGET_CHAT_ID=...
```

E2E worker must reach **tu-app bot-api** on LAN (`192.168.1.20:8081`) and **Telegram Cloud** (outbound HTTPS).

#### Step F3-2 — UFW on tu-app for bot-api (if not open)

```bash
sudo ufw allow from 192.168.1.30 to any port 8081 proto tcp comment 'backupvault e2e'
```

#### Step F3-3 — Alert channel (friend)

Option A — Telegram alert bot:

1. Create bot via @BotFather (or reuse monitoring bot)
2. Add to private group with Roman
3. Store `ALERT_TELEGRAM_BOT_TOKEN` + `ALERT_CHAT_ID` in bv-ops `.env`
4. Wire Grafana contact point or BackupVault worker hook to send:

   `E2E drill FAILED: telegram-uploader-dev — HTTP 404 on volume download`

Option B — email via Grafana — acceptable for homelab.

#### Step F3-4 — Test alert path

```bash
# Force failing E2E (expected today)
curl -X POST http://192.168.1.30:8000/api/v1/targets/<id>/e2e-drills
# Friend confirms message in Telegram group within 2 min
```

**P3 friend deliverable:** alert received on intentional failure; logs in `docker compose logs backupvault-worker`.

### 8.4 Do **not** modify telegram-uploader onion for P3

Copy minimal download HTTP logic into `backupvault/infrastructure/telegram_download_probe.py` (thin adapter). Duplication is intentional — avoids cross-repo imports.

After [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md), add `engine: telegram-client-api` probe variant.

### 8.5 API

```http
POST /api/v1/targets/{id}/e2e-drills
GET  /api/v1/targets/{id}/e2e-drills/latest
```

### 8.6 Smoke P3

| Expected today | Action |
|----------------|--------|
| E2E returns **404** | Drill `status=failed`, alert fires — documents known restore bug |
| E2E returns **200** after Client API migration | Drill `status=success` |

Both outcomes **close gate** if drill correctly reports reality.

### 8.7 Gate P3

- [ ] E2E job runs end-to-end without crashing
- [ ] Result matches manual `curl` download attempt
- [ ] Alert sent on failure (Telegram message or email)

---

## 9) P4 — Ops hardening (week 5–6)

### 9.1 Friend: step-by-step (P4 — observability + runbook + resume demo)

**Goal:** unattended schedules, visible dashboards, friend restores tu-app **without Roman typing commands**.

#### Step F4-1 — Add Prometheus + Grafana to bv-ops compose

Friend extends `backupvault/docker-compose.yml`:

| Service | Port | Role |
|---------|------|------|
| `prometheus` | 9090 | scrape BackupVault `/metrics` |
| `grafana` | 3000 | dashboards + alerts |

`prometheus.yml` scrape target:

```yaml
scrape_configs:
  - job_name: backupvault
    static_configs:
      - targets: ['backupvault-api:8000']
```

#### Step F4-2 — Grafana dashboard panels

| Panel | Query / source |
|-------|----------------|
| Backup success (24h) | `backupvault_backup_runs_success_total` |
| Hours since last backup | `time() - backupvault_last_success_timestamp` |
| Restore drill duration | histogram from worker |
| E2E drill status | 0/1 gauge |
| MinIO bucket size | optional node/minio exporter |

Export JSON to `deploy/monitoring/grafana/dashboards/backupvault.json`.

#### Step F4-3 — Alert rules

| Alert | Condition | Notify |
|-------|-----------|--------|
| `BackupMissing` | no success in 26h | Telegram |
| `RestoreDrillFailed` | last drill `status=failed` | Telegram |
| `E2EDrillFailed` | 2 consecutive failures | Telegram |
| `MinIODown` | health check fail 5m | Telegram |

#### Step F4-4 — Graylog or Loki (pick one for homelab)

Lightweight option — **Grafana Loki** + Promtail on bv-ops:

```bash
# Collect docker compose logs from backupvault-worker
# Filter: target_slug, run_id, phase=backup|restore_drill|e2e
```

Friend documents log query: `{job="backupvault"} |= "restore_drill"`.

#### Step F4-5 — Ansible full deploy playbook

```yaml
# playbooks/deploy-backupvault.yml
- hosts: ops
  tasks:
    - git: repo=... dest=~/backupvault version=main
    - command: docker compose up -d --build
      args:
        chdir: ~/backupvault
    - uri:
        url: http://localhost:8000/health
        status_code: 200
```

CI on push to `main` → SSH to bv-ops → playbook (GitHub Actions with deploy key).

#### Step F4-6 — DR runbook (friend writes)

Create `backupvault/docs/RUNBOOK_RESTORE_TELEGRAM_UPLOADER.md`:

1. Prerequisites checklist (IPs, credentials location)  
2. Stop tu-app workers (commands)  
3. Destroy + recreate postgres volume  
4. Download dump from MinIO (`mc cp` command with real path)  
5. `pg_restore` to `192.168.1.20:5433`  
6. Start tu-app stack  
7. Verify via BackupVault API + Roman GUI  
8. **Recorded RTO:** ___ minutes (homelab measurement)  

#### Step F4-7 — Solo DR rehearsal (friend alone, Roman watches)

Roman only observes. Friend executes runbook start-to-finish on a call.

**P4 friend deliverable:** Grafana URL shared; 7 days metrics; solo DR passed; deploy pipeline green.

### 9.2 Friend deliverables summary

| Item | Description |
|------|-------------|
| **Grafana dashboard** | `backup_success_rate`, `restore_drill_duration`, `e2e_drill_success`, `last_successful_backup_age_hours` |
| **Alerts** | Page if no backup in 26h; if restore drill failed; if E2E failed 2 weeks in a row |
| **Graylog / Loki** | Celery job logs structured JSON (`target_slug`, `run_id`, `phase`) |
| **Terraform** | Homelab module + comment «maps to AWS S3 in production» |
| **Ansible** | `deploy-backupvault.yml`, `bv-ops.yml`, optional `tu-app-ufw.yml` |
| **DR runbook** | `docs/RUNBOOK_RESTORE_TELEGRAM_UPLOADER.md` |
| **CI deploy** | git push → tests → deploy to bv-ops |

### 9.3 Roman deliverables

| Item | Description |
|------|-------------|
| **Retention job** | Delete `backup_runs` older than policy; object storage lifecycle sync |
| **Audit log** | Who triggered manual drill |
| **CI** | GitHub Actions: ruff, mypy, pytest on backupvault |
| **Dashboard UI** | Single HTML or FastAPI template: traffic lights for backup / DB drill / E2E |

### 9.4 Runbook outline (friend writes, Roman reviews)

```markdown
# Restore telegram-uploader after total catalog loss

## Preconditions
- Telegram group still has volumes
- `.env` preserved (encryption keys are IN DB; bot token still needed for download)
- Latest BackupVault backup_run known

## Steps
1. Stop all telegram-uploader workers
2. Recreate postgres volume
3. pg_restore from BackupVault URI
4. Run migrate.py (should no-op if dump is current)
5. Start infra: postgres → redis → telegram-bot-api
6. Run BackupVault restore drill manually
7. Run BackupVault E2E drill
8. Start workers + GUI
9. Attempt restore of one file to /tmp/restore-test

## RTO target (dev): 45 minutes
```

Aligns with upgrade/rollback section in [PROJECT.md](PROJECT.md) § Packaging & CD.

### 9.5 Gate P4

- [ ] Friend restores from runbook on clean VM without Roman typing commands
- [ ] Grafana shows 7 days of metrics
- [ ] Scheduled backup + weekly drill run unattended

---

## 10) Minimal changes inside telegram-uploader repo

Keep onion clean — only **observation / ops** touchpoints:

| Change | Layer | Required when |
|--------|-------|---------------|
| SQL role `backupvault_ro` | Postgres (ops) | P1 |
| Document DSN + port in this file | docs | P1 |
| Optional: `GET /health` on bootstrap app | infrastructure | P4 if friend wants probe |
| Link in [PROJECT.md](PROJECT.md) doc map | docs | after P0 |

**Do not** add BackupVault imports to `use_cases` or `application`.

Optional future: emit webhook on `session.status = completed` → BackupVault `POST /hooks/backup-completed` (post-v1).

---

## 11) Celery schedules (BackupVault)

```python
# illustrative beat schedule in backupvault
beat_schedule = {
    "tu-dev-backup": {
        "task": "infrastructure.worker.tasks.run_backup",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {"target_slug": "telegram-uploader-dev"},
    },
    "tu-dev-restore-drill": {
        "task": "infrastructure.worker.tasks.run_restore_drill",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
        "kwargs": {"target_slug": "telegram-uploader-dev"},
    },
    "tu-dev-e2e-drill": {
        "task": "infrastructure.worker.tasks.run_e2e_drill",
        "schedule": crontab(hour=4, minute=30, day_of_week=0),
        "kwargs": {"target_slug": "telegram-uploader-dev"},
    },
}
```

---

## 12) Verification commands (copy-paste)

### telegram-uploader catalog health

```bash
docker compose exec postgres psql -U telegram_uploader -d telegram_uploader -c "
SELECT s.status, count(*) AS sessions
FROM upload_sessions s GROUP BY s.status;

SELECT count(*) AS uploaded_missing_ref
FROM archive_volumes
WHERE status = 'uploaded' AND external_file_id IS NULL;
"
```

### BackupVault latest status

```bash
curl -s http://localhost:8000/api/v1/targets/telegram-uploader-dev/status | jq .
```

Expected:

```json
{
  "backup": {"status": "success", "at": "2026-06-09T03:02:11Z"},
  "restore_drill": {"status": "success", "at": "2026-06-08T04:05:00Z"},
  "e2e_drill": {"status": "failed", "detail": "telegram download HTTP 404"}
}
```

---

## 13) Backlog entries (add to backupvault repo)

Track in `backupvault/docs/BACKLOG.md`:

- [ ] P0 compose skeleton
- [ ] P1 backup job + MinIO upload
- [ ] P2 restore drill + validators
- [ ] P3 E2E Telegram probe
- [ ] P4 Grafana + runbook
- [ ] Post Client API: swap E2E probe to MTProto session
- [ ] Optional: webhook on session completed

---

## 14) Session checklist (every work session)

Same cycle as [PROJECT.md](PROJECT.md) §10:

1. One phase or sub-phase only
2. `pytest` + `ruff` + `mypy` green in **backupvault**
3. **Manual smoke** for that phase
4. Roman confirms gate → tick item in backlog
5. Demo to friend: show API status or Grafana panel

---

## 15) What to show your friend on first demo (P1 gate)

1. telegram-uploader GUI on Laptop A: completed backup session
2. BackupVault API on bv-ops: last backup green
3. MinIO console on `192.168.1.30:9001`: dump file with date
4. One sentence: «If Postgres on tu-app dies, we restore from bv-ops — P2 proves it next week»

---

## 16) Resume demo script (record screen — 10 min)

Perform after **P4 gate** on real hardware (weak PC + server PC). Suitable for portfolio / interview.

| Min | Who | Action | What to say |
|-----|-----|--------|-------------|
| 0–1 | Roman | Laptop A: open GUI, show completed session | «User backed up files to Telegram» |
| 1–2 | Roman | `psql` on tu-app: show `archive_volumes.external_file_id` | «Catalog lives on app host Postgres» |
| 2–4 | Friend | Grafana: backup green, last drill, E2E status | «Ops host monitors catalog health 24/7» |
| 4–5 | Friend | MinIO: show dated `.dump` files | «Automated pg_dump over LAN, not manual copies» |
| 5–7 | Roman | tu-app: stop postgres, **delete volume** | «Simulating dead disk on app server» |
| 7–9 | Friend | runbook: `mc cp` + `pg_restore` to tu-app | «Cross-host DR without developer intervention» |
| 9–10 | Roman | GUI: sessions reappear | «RTO ___ min — catalog recovered; files still in Telegram» |

Optional punch line if E2E red: «E2E caught Telegram 404 before user lost laptop — metadata OK, provider fix tracked.»

### Screenshots for CV / LinkedIn

1. Network diagram (§1.5) with your real IPs  
2. Grafana dashboard  
3. MinIO object list  
4. GUI with restored sessions after DR  

---

## 17) Master checklist — friend (DevOps)

Print and tick per phase.

### One-time setup

- [ ] Server PC Ubuntu/Debian installed, static IP `192.168.1.30`
- [ ] Docker + Compose installed
- [ ] SSH key from Laptop B → bv-ops
- [ ] UFW on bv-ops configured
- [ ] Ansible inventory with `ops` + `app` groups
- [ ] Git access to `backupvault` (+ read `telegram-uploader`)

### P0

- [ ] `docker compose up` on bv-ops
- [ ] `/health` OK from Laptop B
- [ ] MinIO bucket `backupvault-dumps` exists

### P1

- [ ] `nc -zv 192.168.1.20 5433` from bv-ops
- [ ] UFW on tu-app allows only bv-ops → 5433
- [ ] `backupvault_ro` SELECT works; DELETE fails
- [ ] First backup object in MinIO
- [ ] Secrets only in bv-ops `.env` (chmod 600)

### P2

- [ ] `postgres-sandbox` isolated from tu-app
- [ ] Automated restore drill all validators green
- [ ] Joint DR smoke: catalog back on tu-app

### P3

- [ ] Telegram secrets on bv-ops
- [ ] UFW tu-app: bv-ops → 8081
- [ ] E2E drill runs; alert received on failure

### P4

- [ ] Prometheus + Grafana live 7 days
- [ ] Alert rules firing on test
- [ ] Runbook written
- [ ] **Solo DR rehearsal** without Roman commands
- [ ] CI deploy on git push
- [ ] Resume demo recorded

---

## 18) Master checklist — Roman (backend)

- [ ] telegram-uploader on tu-app (weak PC), GUI on Laptop A
- [ ] ≥1 completed backup session before P1
- [ ] `backupvault` repo P0 skeleton pushed
- [ ] P1: backup job + target API
- [ ] P2: restore drill job + validators
- [ ] P3: e2e drill job
- [ ] P4: retention job + status UI
- [ ] Gate confirmed each phase (manual smoke)

---

## 19) Troubleshooting (homelab)

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| bv-ops cannot reach :5433 | UFW / wrong IP | `sudo ufw status` on tu-app; ping |
| `pg_dump` empty file | wrong DSN | check `backupvault_ro` password |
| Worker cannot reach MinIO | docker network | `docker compose exec worker curl minio:9000/minio/health/live` |
| E2E cannot reach bot-api | UFW 8081 | allow bv-ops on tu-app |
| GUI cannot connect | Laptop `.env` points wrong host | `POSTGRES_HOST=192.168.1.20` |
| Weak PC OOM | too many workers | stop `celery-worker-archive-2` |

---

*Architecture of telegram-uploader → [PROJECT.md](PROJECT.md). Product rules for restore metadata → [INTERNAL_SPEC.md](INTERNAL_SPEC.md).*
