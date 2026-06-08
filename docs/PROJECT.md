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
| Onion layers: `domain` → `use_cases` → `infrastructure` → `application` | ✅ |
| Backup: GUI → workers → Telegram → `completed` | ✅ |
| Restore download (Bot API) | ❌ HTTP 404 |
| Restore extract (7z → original file) | ❌ |
| Client API provider | ❌ planned |
| CI / `import-linter` / observation layer | ❌ |

Unimplemented work: **[BACKLOG.md](BACKLOG.md)** (includes **stack vs CV** matrix from `~/еку.txt`).

**How we work:** architecture cleanup **use_cases → infrastructure → application** (see BACKLOG § rules). After each change — run the app yourself and smoke-test before moving on.

## Documentation map

| Document | Purpose |
|----------|---------|
| **[PROJECT.md](PROJECT.md)** (this file) | Project overview + doc index |
| **[BACKLOG.md](BACKLOG.md)** | Everything not implemented yet |
| **[INTERNAL_SPEC.md](INTERNAL_SPEC.md)** | Product rules (encryption, `display_name`, English UI) |
| **[ONION_ARCHITECTURE.md](ONION_ARCHITECTURE.md)** | Layer structure, imports, folders — **source of truth** |
| **[TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md)** | **Active plan:** Bot API → Client API (MTProto) |

### Feature / migration plans

| Plan | When to read |
|------|----------------|
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
docker compose up -d
PYTHONPATH=src .venv/bin/python -m application.gui
```

Env: `.env` (see `.env.example`). Host GUI uses `localhost:5433`; containers use compose service names.

## Verify

```bash
.venv/bin/pytest -m "not integration" -v
.venv/bin/ruff check src tests && .venv/bin/mypy src
docker compose logs -f celery-worker-archive-1
```

## Repo root

- [README.md](../README.md) — short product blurb (RU)
- [docker-compose.yml](../docker-compose.yml) — runtime services

---

*Architecture questions → [ONION_ARCHITECTURE.md](ONION_ARCHITECTURE.md). What to build next → [BACKLOG.md](BACKLOG.md).*
