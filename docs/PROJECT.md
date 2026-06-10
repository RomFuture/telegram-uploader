# telegram-uploader

Linux desktop app for backing up files to messenger storage. **v1** is Telegram-first; core is provider-agnostic (`StorageProviderPort`).

## What it does

1. User picks files in GUI (English UI, `display_name` captured at enqueue).
2. Pipeline archives with **7z** (encrypt + split), uploads volumes to a **target Telegram group**, tracks state in **PostgreSQL**.
3. **Celery workers** (archive / upload / cleanup / restore queues) run heavy work; GUI talks to **`BackupFacade`** only.
4. **Restore** downloads volumes and (target) extracts the original file.

## Current status (2026-06)

| Area | Status |
|------|--------|
| **`domain` layer cleanup** | ✅ **done** (2026-06) — see [BACKLOG § P4](BACKLOG.md) |
| **`use_cases` layer cleanup** | 🟡 **in progress** (P0.1) |
| **`infrastructure` layer cleanup** | ❌ P0.2 — Client API, Celery failure wiring |
| **`application` / GUI** | ❌ P0.3 |
| Backup: GUI → workers → Telegram → `completed` | ✅ |
| Restore download (Bot API) | ❌ HTTP 404 |
| Restore extract (7z → original file) | ❌ |
| Client API provider | ❌ planned |
| CI (GitHub Actions: ruff, mypy, pytest) | 🟡 `.github/workflows/ci.yml` |
| CD (`.deb` package + safe upgrades) | ❌ planned — see § Packaging & CD |
| AI agent skills (`.cursor/skills/`, vendor submodules) | 🟡 `docs/stop-slop` submodule — [AI_AGENT_SKILLS.md](AI_AGENT_SKILLS.md) |
| `import-linter` / observation layer | ❌ |

Unimplemented work: **[BACKLOG.md](BACKLOG.md)** (includes **stack vs CV** matrix from `~/еку.txt`).

**How we work:** `domain` is closed; architecture cleanup continues **use_cases → infrastructure → application** (see [BACKLOG](BACKLOG.md) § rules). After each change — run the app yourself and smoke-test before moving on.

### AI agents (Cursor)

All **agent outputs must be in English** — chat replies, explanations, doc edits, commit/PR text, code comments added by the agent, and session summaries. This matches the product language policy ([INTERNAL_SPEC.md](INTERNAL_SPEC.md)) and keeps repo prose consistent (README, `docs/`, skills).

The human maintainer may write in any language; agents still respond in English unless explicitly asked otherwise for a one-off message.

Skills and workflow: [AI_AGENT_SKILLS.md](AI_AGENT_SKILLS.md) · gate/smoke: [ONION_LAYER_IMPLEMENTATION.md](ONION_LAYER_IMPLEMENTATION.md).

## Documentation map

| Document | Purpose |
|----------|---------|
| **[PROJECT.md](PROJECT.md)** (this file) | Project overview + doc index |
| **[BACKLOG.md](BACKLOG.md)** | Everything not implemented yet |
| **[INTERNAL_SPEC.md](INTERNAL_SPEC.md)** | Product rules (encryption, `display_name`, English UI) |
| **[ONION_ARCHITECTURE.md](ONION_ARCHITECTURE.md)** | Layer structure, imports, folders — **source of truth** |
| **[ONION_LAYER_IMPLEMENTATION.md](ONION_LAYER_IMPLEMENTATION.md)** | Gate, smoke, implementation cycle per layer — **mandatory**; §7 target GUI mockup |
| **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)** | Bot, API keys, backup group, `.env`, first backup |
| **[TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md)** | **Active plan:** Bot API → Client API (MTProto) |
| **[BACKUPVAULT_IMPLEMENTATION.md](BACKUPVAULT_IMPLEMENTATION.md)** | **Side project (future):** separate `backupvault` repo + DevOps partner — not v1 scope |
| **[AI_AGENT_SKILLS.md](AI_AGENT_SKILLS.md)** | Cursor skills layout, vendor submodules, `.cursor/skills/` TODO |

### Feature / migration plans

| Plan | When to read |
|------|----------------|
| [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) | First-time Telegram + `.env` wiring |
| [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md) | Replacing Telegram Bot API; restore download |

Add new plans here as `docs/<NAME>_MIGRATION.md` or `docs/plans/<name>.md`.

## Stack

| Piece | Role |
|-------|------|
| `src/domain/` | Entities, statuses, invariants |
| `src/use_cases/` | Use cases + `StorageProviderPort` Protocol |
| `src/infrastructure/` | DB, 7z, Celery, `TelegramProviderV1`, `BackupFacade`, `bootstrap` |
| `src/application/` | `backend_receiver` + Tkinter GUI |
| Docker | postgres, redis, celery workers, `telegram-bot-api` (legacy) |

## Run (dev)

```bash
./scripts/run.sh
```

Or manually:

```bash
docker compose up -d
PYTHONPATH=src .venv/bin/python -m application.gui
```

Env: `.env` (see `.env.example`). Host GUI uses `localhost:5433`; containers use compose service names.

## Packaging & CD (P0.05 — planned)

**Goal:** ship a **`.deb`** for Linux desktop install; CD pipeline builds and publishes it on release.

### CD pipeline (to implement)

| Step | What |
|------|------|
| Trigger | Git tag `v*` (or release branch) after green CI |
| Build | `dpkg-deb` / `nfpm` / `fpm` — bundle app (`src/`), `scripts/run.sh`, systemd user units (optional), `docker-compose.yml` + pinned image tag |
| Publish | GitHub Release artifact `.deb` (+ checksums) |
| Smoke | Install `.deb` on clean Ubuntu/Debian VM; run backup happy path |

### Safe upgrade order (must not break running installs)

Upgrades are **forward-only**; downgrading the package is unsupported.

1. **Stop consumers** — quit GUI; `docker compose stop` celery workers (archive/upload/cleanup/restore) and `app`.
2. **Backup state** — document paths users must keep: PostgreSQL volume (`postgres-data`), `archive-cache`, user config (`.env` or `/etc/telegram-uploader/env`), session logs.
3. **Install new `.deb`** — `apt upgrade` / `dpkg -i`; `postinst` must **not** wipe data dirs or volumes.
4. **DB migrations** — run `migrate.py` **before** starting workers (same rule as dev bootstrap); migration version stored in DB; package ships only forward migrations.
5. **Refresh runtime image** — `docker compose pull` (when CD publishes image) or use compose `build` pin matching package version.
6. **Start infra** — `postgres` → `redis` → `telegram-bot-api` (healthchecks green).
7. **Start workers** — celery queues, then `app` bootstrap if used.
8. **Start GUI** — host `python -m application.gui` (or desktop entry from `.deb`).

**Version coupling:** package `Version` = `pyproject.toml` version = Docker image tag = migration set for that release. Mismatch → refuse start with clear error.

**Config on upgrade:** preserve env file and `HOST_SOURCE_MOUNT`; new keys from `.env.example` merged in `postinst` (append missing defaults, never overwrite secrets).

**Rollback policy:** re-install previous `.deb` only if DB was not migrated forward; if migrations ran, rollback requires restore from backup (document in release notes).

## Verify

```bash
.venv/bin/pytest -m "not integration" -v
.venv/bin/ruff check src tests && .venv/bin/mypy src
docker compose logs -f celery-worker-archive-1
```

## Repo root

- [README.md](../README.md) — product overview, quick start, roadmap (EN)
- [scripts/run.sh](../scripts/run.sh) — dev launcher: `docker compose up -d` + GUI
- [docker-compose.yml](../docker-compose.yml) — runtime services

---

*Architecture questions → [ONION_ARCHITECTURE.md](ONION_ARCHITECTURE.md). What to build next → [BACKLOG.md](BACKLOG.md).*
