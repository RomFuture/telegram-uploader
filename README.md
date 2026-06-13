# telegram-uploader

Linux desktop backup into messenger storage. v1 ships Telegram only. The core speaks `StorageProviderPort`, so you can add Max or VK adapters later.

Docs: [PROJECT.md](docs/PROJECT.md) (architecture + refactor plan) · [BACKLOG.md](docs/BACKLOG.md)

## Backup flow

You pick files in the GUI (English UI; `display_name` lands at enqueue). Workers encrypt and split archives with 7z, upload volumes to a Telegram group via **Client API (MTProto)**, and record state in PostgreSQL. Celery runs archive, upload, cleanup, and restore queues. The GUI calls `GuiEntrypoint` through `BackendReceiver`. Restore download on Client API is still being validated end-to-end.

## Status (June 2026)

| Area | State |
|------|-------|
| Onion layers: `domain` → `use_cases` → `infrastructure` → `application` | Done |
| Phase 1 refactor (R2–R8, public API) | Done |
| Backup: GUI → workers → Telegram → `completed` | Done (Client API default) |
| Client API: sign-in, Test Client API, upload + download | Done |
| Restore download (Client API) | In progress ([migration](docs/TELEGRAM_CLIENT_API_MIGRATION.md)) |
| Restore extract (7z → original file) | Done |
| Packaging `.deb` + upgrade docs | Done (0.1.9) |
| CI: ruff, mypy, pytest, lint-imports | Done ([workflow](.github/workflows/ci.yml)) |
| CD: `.deb` on tag `v*` | Done ([release](.github/workflows/release.yml)) |

**Start here (maintainer):** [docs/PROJECT.md](docs/PROJECT.md) — architecture, gate/smoke rules.

Open features → [BACKLOG.md](docs/BACKLOG.md).

## Setup from scratch

You need Linux, Docker, Docker Compose, Python 3.12+, Tkinter, and Git.

```bash
git clone --recurse-submodules git@github.com:RomFuture/telegram-uploader.git
cd telegram-uploader
# if you already cloned without submodules:
# git submodule update --init --recursive

python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

cp .env.example .env
```

**Telegram (default: Client API):** backup uses your **Telegram user session** (Telethon). Fill `.env` using **[docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md)** before first run.

| Variable | Source |
|----------|--------|
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_TARGET_CHAT_ID` | Numeric id of your private backup group (`-100…`) |
| `TELEGRAM_SESSION_PATH` | Default `~/.config/telegram-uploader/session.session` |

Then run:

```bash
./scripts/run.sh
```

The script starts Postgres, Redis, Celery workers, applies migrations, and opens the Tkinter GUI. Sign in via **Settings → Sign in to Telegram…** or `telegram-uploader-login` (packaged install).

Smoke: Start Session → Add File → Start Backup → Refresh Progress. Volumes should appear in your Telegram group as `display-name.7z.001`. See [TELEGRAM_SETUP.md § First backup](docs/TELEGRAM_SETUP.md#6-first-backup). **Logs:** `tail -f telegram-uploader.log` (GUI + workers; see [TELEGRAM_SETUP.md § Logs](docs/TELEGRAM_SETUP.md#logs-gui--workers)).

## Install from .deb (Ubuntu 24.04 amd64)

Download the latest `.deb` from [GitHub Releases](https://github.com/RomFuture/telegram-uploader/releases) (built automatically on tag `v*`, version synced with `pyproject.toml`).

**Platform:** Ubuntu 24.04 **amd64** only. Needs Docker, Python 3.12+, Tkinter, and 7z (listed as package dependencies).

### Clean install (first time)

**1. System packages and `.deb`**

Prefer `apt install ./…deb` — it pulls dependencies automatically:

```bash
sudo apt update
sudo apt install ./telegram-uploader_<version>_amd64.deb
telegram-uploader-check-deps
```

If `check-deps` warns that Docker is not reachable:

```bash
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
# log out and back in (or reboot), then:
telegram-uploader-check-deps
```

If you used `dpkg -i` alone and dependencies are missing:

```bash
sudo apt -f install
sudo apt install docker.io docker-compose-plugin python3-venv python3-tk p7zip-full
telegram-uploader-check-deps
```

Avoid `sudo dpkg -i` without `apt -f install` — Docker may not be installed on a fresh system.

**2. App config file**

```bash
telegram-uploader --setup
```

Creates `~/.config/telegram-uploader/.env` (one time).

**3. Telegram credentials (before backup works)**

Prepare on [my.telegram.org](https://my.telegram.org) and in Telegram:

| What | Where |
|------|--------|
| API ID + API hash | [my.telegram.org](https://my.telegram.org) → API development tools |
| Backup group | Private group; your account must be a member |
| Target chat ID | Supergroup id, usually `-100…` (not your personal user id) |

Full walkthrough: [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md).

**4. Start the app**

```bash
telegram-uploader
```

This starts Postgres, Redis, Celery workers (Docker), applies DB migrations, and opens the GUI.

**5. GUI onboarding**

1. **Unlock** — enter encryption key if you set one in Settings later.
2. **Settings → Client API** — API ID, API hash; session path can stay default (`~/.config/telegram-uploader/session.session`).
3. **Settings → General** — **Target chat ID** = backup group id (`-100…`).
4. **Save**.
5. **Sign in to Telegram…** (in Settings) **or** run `telegram-uploader-login` in a terminal (phone + code, once).
6. **Test Client API** — uploads and downloads a small test file from your group.
7. **Add file → Backup** — first real backup.

Config and session persist under `~/.config/telegram-uploader/`. Application files: `/opt/telegram-uploader/`.

### Upgrading (`.deb` users)

Releases are published on [GitHub Releases](https://github.com/RomFuture/telegram-uploader/releases) when a maintainer pushes tag `v*` (version matches `pyproject.toml`).

**What is preserved:** `~/.config/telegram-uploader/.env`, Telegram session (`session.session`), Docker volumes `postgres-data` (backup metadata) and `archive-cache` (7z cache).

**What is updated:** `/opt/telegram-uploader/` (code, `docker-compose.yml`, Dockerfile), `/usr/bin/telegram-uploader`, Python venv in `/opt/telegram-uploader/.venv` (recreated by `postinst`).

```bash
# 1. Close the GUI if it is open.

# 2. Stop the stack (recommended)
docker compose -f /opt/telegram-uploader/docker-compose.yml down

# 3. Install the new package
sudo apt install ./telegram-uploader_<version>_amd64.deb

# 4. Start as usual — migrations, image rebuild, and worker restart run automatically
telegram-uploader
```

You do **not** need to run `--setup` or sign in to Telegram again unless you changed accounts or deleted the session file.

| | First install | Upgrade |
|--|---------------|---------|
| `sudo apt install ./…deb` | yes | yes |
| `telegram-uploader --setup` | once | no |
| Sign in / `telegram-uploader-login` | once | usually no |
| `telegram-uploader-check-deps` | recommended | optional |

**Optional — backup Postgres before a major upgrade** (if release notes mention schema migrations):

```bash
docker compose -f /opt/telegram-uploader/docker-compose.yml down
docker run --rm \
  -v telegram-uploader_postgres-data:/data \
  -v "$HOME:/backup" \
  alpine tar czf "/backup/telegram-uploader-postgres-$(date +%Y%m%d).tar.gz" -C /data .
```

There is no auto-update channel yet — download each new `.deb` manually from Releases.

### Building a `.deb` locally

Local build (requires [nfpm](https://nfpm.goreleaser.com/)):

```bash
./scripts/build_deb.sh
```

### `telegram-bot-api` fails to start

If `docker compose up` reports `dependency telegram-bot-api failed to start` (container exit 1), `.env` still has empty or placeholder values — usually `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` left as `change_me` after `cp .env.example .env`.

```bash
docker compose logs telegram-bot-api
# → "You must provide valid api-id and api-hash obtained at https://my.telegram.org"
```

Fix: set real `api_id` (numeric) and `api_hash` from [my.telegram.org](https://my.telegram.org), plus bot token and group id — see [TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md). `./scripts/run.sh` should catch this early and point to the same guide.

### Telegram provider: Client API default, Bot API legacy

**Default:** `TELEGRAM_PROVIDER=client` — `TelegramClientProvider` (Telethon user session). Sign in once via GUI or `telegram-uploader-login`. No `telegram-bot-api` container required.

**Legacy:** `TELEGRAM_PROVIDER=bot` + `docker compose --profile bot` — old Bot API path; restore download unreliable (HTTP 404). See [TELEGRAM_CLIENT_API_MIGRATION.md](docs/TELEGRAM_CLIENT_API_MIGRATION.md).

## Architecture

```mermaid
flowchart TB
  ui[LinuxGUI] --> backend[AppBackendReceiver]
  backend --> api[BackupApi]
  api --> useCases[UseCases]
  useCases --> queue[CeleryQueue]
  useCases --> db[(PostgreSQL)]
  queue --> worker[CeleryWorker]
  worker --> workerApi[WorkerApi]
  workerApi --> useCases
  worker --> redis[(Redis)]
  worker --> archive[SevenZipService]
  worker --> providerPort[StorageProviderPort]
  providerPort --> tgClient[TelegramClientProvider]
  tgClient --> messenger[TelegramGroup]
```

Layers: `application` → `infrastructure` → `use_cases` → `domain`. The GUI must not import infrastructure.

## Stack

| Path | Role |
|------|------|
| `src/domain/` | Entities, statuses, invariants |
| `src/use_cases/` | Use cases, `StorageProviderPort` |
| `src/infrastructure/` | DB, 7z, Celery, Telegram providers, bootstrap |
| `src/application/` | `backend_receiver`, Tkinter GUI |
| Docker | Postgres, Redis, workers (`telegram-bot-api` optional, `--profile bot`) |

## Checks

```bash
.venv/bin/pytest -m "not integration" -v
.venv/bin/ruff check src tests && .venv/bin/mypy src
docker compose logs -f celery-worker-archive-1
```

## More docs

| File | Contents |
|------|----------|
| [docs/PROJECT.md](docs/PROJECT.md) | **Architecture, refactor plan, gate/smoke, stack** |
| [docs/BACKLOG.md](docs/BACKLOG.md) | Open work |
| [docs/INTERNAL_SPEC.md](docs/INTERNAL_SPEC.md) | Encryption, `display_name`, UI language |
| [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md) | API keys, group, `.env`, first backup |
| [docs/CLIENT_API_SETUP.md](docs/CLIENT_API_SETUP.md) | Client API sign-in and session |
| [docs/releases/](docs/releases/) | GitHub Release notes per version |
| [docs/TELEGRAM_CLIENT_API_MIGRATION.md](docs/TELEGRAM_CLIENT_API_MIGRATION.md) | Bot API → Client API |

---

## Roadmap

### Onboarding automation

| Task | State |
|------|-------|
| Settings → Save → `~/.config/telegram-uploader/.env` | Done |
| GUI / CLI sign-in (`telegram-uploader-login`) | Done |
| Test Client API in Settings (upload + download) | Done |
| Beginner-friendly setup guide (screenshots, no terminal) | Open ([BACKLOG](docs/BACKLOG.md)) |

### P-demo

| Task | State |
|------|-------|
| `scripts/run.sh`: Docker + GUI | Done |
| `.github/workflows/ci.yml` | Done |
| README + [TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md) | Done |
| Backup happy path (Client API) | Done |
| Restore smoke on Client API | Open |

### P0.05 Packaging & CD

| Task | State |
|------|-------|
| CD pipeline: `.deb` on release tag | Done ([`.github/workflows/release.yml`](.github/workflows/release.yml)) |
| `packaging/` + `telegram-uploader` launcher | Done |
| Clean install + upgrade docs | Done ([README](#clean-install-first-time), [releases](docs/releases/)) |
| Safe upgrade order (stop workers → migrate → image → start) | Documented ([PROJECT.md](docs/PROJECT.md#packaging)) |
| Version lock: deb = `pyproject.toml` = tag `v*` | Done (`scripts/check_release_version.sh`) |

### P0 Architecture cleanup

Work order: `use_cases` → `infrastructure` → `application`.

| Stage | Work | State |
|-------|------|-------|
| P0.1 | Ports/records audit, restore refs for Client API, failed-status in use cases, dedupe backup/restore | Open |
| P0.2 | Client API provider, structured logging, rollback on failure | Partial (provider done) |
| P0.3 | Thin `backend_receiver`, GUI errors, failed/stuck UI, settings, restore UX | Partial (settings + sign-in done) |

### P1 Restore end-to-end

| Task | State |
|------|-------|
| Download volumes by `part_number` (Client API) | Open |
| 7z decrypt/extract with session key | Done |
| Write to user `dest_path` | Done |
| Restore success / `failed` statuses | Partial |
| Resume downloads | Open (low priority) |

### P2 Observation & CI

| Task | State |
|------|-------|
| `import-linter` layer contracts | Done |
| CI `lint-imports` step | Done |
| `src/observation/health.py` | Open |
| `logs/` in `.gitignore` | Open |

### P3 Integration tests

| Task | State |
|------|-------|
| `tests/test_worker_pipeline_integration.py` in Docker | Open |
| `tests/test_repositories_integration.py` on live Postgres | Open |
| Live Telegram smoke after Client API | Open |

### P4 Domain (deferred)

| Task | State |
|------|-------|
| Generic `verify` / `mark` with `@overload` | Open |
| Scenario-first public API | Open |
| Merge `guards.py` + `scenarios.py` if it pays off | Open |
| Audit `domain/__init__.py` exports | Open |

### P5 Docs

| Task | State |
|------|-------|
| [PROJECT.md](docs/PROJECT.md): sync with code | Done (2026-06-12) |

### After v1

| Task | State |
|------|-------|
| Max / VK adapters | Open |
| Provider compatibility matrix | Open |
| Contract tests per provider | Open |
| Session logs under `logs/sessions/<session_id>/` | Open |
| Prometheus / Grafana | Open |
| Kubernetes for workers + Postgres | Open |

### Out of scope for v1

- Telegram topics (`message_thread_id`)
- Moving user files into a service directory
- Max / VK adapters (port only today)
