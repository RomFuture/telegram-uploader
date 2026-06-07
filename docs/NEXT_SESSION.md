# Next session — ship the vertical slice (MVP first)

> **Intent:** stop polishing the core; wire everything so backup → upload → cleanup → restore **works** end-to-end. Architecture can stay “из говна и палок” — refactor later using [TODO.md](TODO.md).

**Domain / use-case core:** considered **done for now** (Phase 4.1, repo `require()`, `scenarios.py`). Do not block pipeline work on domain cleanup.

---

## Mindset

| Do now | Defer |
|--------|--------|
| Stubs → real calls | Perfect facade API |
| One happy path + basic errors | Full retry taxonomy |
| Manual smoke + a few tests | GUI polish |
| Copy-paste wiring if faster | DRY bootstrap |

**Definition of “done” for this sprint:** `docker compose up`, enqueue a file, worker runs archive → upload → cleanup, DB statuses reach `COMPLETED`; restore downloads volumes and extracts (mock provider OK in tests).

---

## Already in place (do not redo)

- [x] Domain in `src/domain/` (models, errors, actions, guards, scenarios) — top-level layer 1
- [x] Use cases: `CreateSession`, `EnqueueSourceItem`, `StartBackupPipeline`, `ProcessArchiveVolume`, `ProcessUploadVolume`, `CleanupVolume`, `RestoreSession` (download step only)
- [x] Ports + SQLAlchemy repos + Telegram provider + 7z adapter (adapters exist)
- [x] Repo `require()` / `list_domain_*` — use cases free of mapper-on-read
- [x] Unit tests with fakes (`pytest -m "not integration"`)

---

## Phase 5 — Worker pipeline (priority 1)

**Goal:** replace Celery stubs with real use case execution.

| Step | Action |
|------|--------|
| 5.1 | Add `infrastructure/bootstrap.py` with `build_facade()` / factory helpers (minimal version OK) |
| 5.2 | `archive_volume` task → `ProcessArchiveVolumeUseCase.execute(UUID(...))` |
| 5.3 | `upload_volume` task → `ProcessUploadVolumeUseCase.execute(...)` |
| 5.4 | `cleanup_volume` task → `CleanupVolumeUseCase.execute(...)` |
| 5.5 | `restore_volume` task → restore step (even if partial) |
| 5.6 | Basic Celery retries (`autoretry_for`, `max_retries`) — good enough, not perfect |
| 5.7 | Idempotency: skip if already `UPLOADED` / `COMPLETED` where obvious |

**Files:** `src/infrastructure/worker/tasks.py`, new `src/infrastructure/bootstrap.py`

**Verify:**

```bash
docker compose up -d
# trigger archive_volume.delay(...) — logs must NOT say "stub"
pytest tests/test_celery_workers.py -v
```

Detail: [ONION_LAYER_IMPLEMENTATION.md](ONION_LAYER_IMPLEMENTATION.md) § Phase 5.

---

## Phase 6 — Bootstrap + facade (priority 2)

**Goal:** single composition root; workers and app share wiring.

| Step | Action |
|------|--------|
| 6.1 | `infrastructure/bootstrap.py` — logging, config, migrations, Redis ping, `build_facade()` |
| 6.2 | `infrastructure/facade.py` — `BackupFacade`: `enqueue_file`, `start_session`, worker delegates |
| 6.3 | Wire repos, `TelegramProviderV1`, `CeleryTaskQueue`, `SevenZipService`, use case instances |
| 6.4 | Move logic from `application/bootstrap.py` → `infrastructure/bootstrap.py` |
| 6.5 | Update `docker-compose.yml` entrypoint → `python -m infrastructure.bootstrap` |
| 6.6 | Delete `application/bootstrap.py` when redundant |

**Acceptable MVP:** facade methods are thin one-liners; DTOs can be dicts or minimal dataclasses.

**Verify:**

```bash
pytest tests/test_bootstrap_wiring.py tests/test_facade.py -v   # create if missing
python -m infrastructure.bootstrap
```

Detail: § Phase 6.

---

## Phase 7 — Application shell (priority 3)

**Goal:** something a human can click — minimal GUI or CLI wrapper.

| Step | Action |
|------|--------|
| 7.1 | `application/backend_receiver.py` — talks **only** to `BackupFacade` |
| 7.2 | Minimal GUI (`application/gui/`) OR CLI script — session + enqueue + progress |
| 7.3 | English UI strings; show `display_name` from DB |
| 7.4 | Delete `src/presentation/` |

**Acceptable MVP:** Tkinter or a single “enqueue path + start pipeline” script; no ETA charts required.

Detail: § Phase 7.

---

## Phase 8 — Restore end-to-end (priority 4)

**Goal:** finish what `RestoreSessionUseCase` started (download only today).

| Step | Action |
|------|--------|
| 8.1 | Order volumes by `part_number` |
| 8.2 | Download all parts (already partially there) |
| 8.3 | Reassemble split archive |
| 8.4 | Decrypt/extract via 7z + session `encryption_key` |
| 8.5 | Status updates on success/failure |
| 8.6 | Wire `request_restore` in facade + backend/GUI |
| 8.7 | Resume downloads — **nice to have**, skip if tight |

**Verify:**

```bash
pytest tests/test_restore_integration.py -v   # mock provider OK
```

Detail: § Phase 8.

---

## Phase 9 — Observation (priority 5, optional for MVP)

- Layer boundary checks in CI (extend `test_layer_boundaries.py` if needed)
- Health probes / structured logs

Can land after first manual backup smoke.

Detail: § Phase 9.

---

## Suggested session order

1. **Phase 5 + 6 together** — bootstrap + wire tasks (unblocks everything).
2. **Manual smoke** — one file through full pipeline in Docker.
3. **Phase 8** — restore happy path with mocks.
4. **Phase 7** — thinnest possible UI on top of facade.
5. **Phase 9** — CI hardening when stable.

---

## After the slice works

1. Run through [TODO.md](TODO.md) — domain compression / API cleanup.
2. Re-read [ONION_ARCHITECTURE.md](ONION_ARCHITECTURE.md) and align docs with reality.
3. Replace MVP shortcuts (dict DTOs, duplicated wiring, weak retry policy).

---

*Created when domain core work was paused. Update this file as phases complete.*
