---
name: explain-architecture-two-views
description: >-
  Explains software architecture to Roman using simple analogies plus full layer
  boundaries—never conflates user journey with direct code coupling. Use when
  Roman asks how layers work, Celery/Redis/GUI flow, hexagonal/onion architecture,
  ports and adapters, or says he does not understand the explanation.
---

# Explain Architecture — Two Views + Simple Analogies

Roman prefers **plain analogies** but **not dumbed-down architecture**. Never trade accuracy for brevity. Never use one phrase that implies a layer bypass when code goes through ports.

## Mandatory response shape

For every architecture question, use **both** views in order:

### View 1 — User path (what happened)

Answer: «What occurs after the user action?»  
Chronological steps from click/command to outcome.

**Allowed shorthand:** «Backup **leads to** a task on the queue.»  
**Forbidden shorthand:** «GUI puts task in Redis» without the chain below.

### View 2 — Layer boundaries (who may call whom)

Answer: «Which **code layer** does each step?»  
Map to real modules/classes/files. State what each layer **may** and **may not** import or call.

Always show the full chain when async/infra is involved:

```
GUI → Entrypoint (public) → UseCase → Port (Protocol) → Infrastructure impl → external system
```

Example (telegram-uploader backup start):

```
app.py → BackendReceiver → GuiEntrypoint.start_backup()
  → StartBackupPipelineUseCase → TaskQueuePort.enqueue_archive()
  → CeleryTaskQueue → archive_volume.delay() → Redis
```

**Rule:** View 1 describes outcome; View 2 proves GUI never imports Redis/Celery.

---

## Default analogy (telegram-uploader / hexagonal)

Use **one stable analogy** per answer—do not mix metaphors (no «recipe» + «courier» + «engine» in the same reply).

| Layer / concept | Restaurant analogy |
|-----------------|-------------------|
| GUI | Guest at table |
| GuiEntrypoint / BackendReceiver | Waiter |
| Use case | Chef — decides **what** |
| Port (Protocol) | Order form — **not** the kitchen |
| Infrastructure adapter | Dispatcher + order board |
| Celery worker process | Cook already on shift |
| CeleryEntrypoint | Menu of cook procedures |
| TelegramClientProvider | Delivery phone (Telethon dials) |
| Redis | Order board (tasks waiting) |

**Provider rule:** Provider objects do **nothing** until a use case calls a method (e.g. `upload_file`). Say: «Use case **calls** provider; provider does not run alone.»

**Celery rule:** Celery **calls into** entrypoint/use cases. CeleryEntrypoint is **not** Celery. Workers are **not** created per task—they run since `docker compose up`.

---

## Forbidden phrasing

| Do not say | Say instead |
|------------|-------------|
| GUI → Redis | GUI → use case → port → infra → Redis |
| GUI uploads to Telegram | Worker upload process uploads; GUI only starts pipeline |
| build_worker_api creates workers | wire_celery_entrypoint **wires** use cases; Docker runs workers |
| Provider sends files by itself | ProcessUploadVolumeUseCase calls `storage_provider.upload_file()` |
| WorkerApi is Celery | Celery calls CeleryEntrypoint; entrypoint delegates to use cases |

---

## telegram-uploader quick facts (View 2 anchors)

- **GUI puts in queue (via use case):** only `enqueue_archive` on Start Backup (queued items).
- **Upload tasks in Redis:** set by **archive worker** (`ProcessArchiveVolumeUseCase` → `enqueue_upload`), not GUI on happy path.
- **Bytes to Telegram on backup:** **upload worker** → `ProcessUploadVolumeUseCase` → `TelegramClientProvider`.
- **Restore download:** GUI process (background thread), not upload worker.
- **Import rules:** `application` → only `use_cases.public`; `use_cases` must not import `infrastructure`, `celery`, `redis` (`tests/test_layer_boundaries.py`).

Renamed public API (use these names):

| Old | Current |
|-----|---------|
| BackupApi | GuiEntrypoint |
| WorkerApi | CeleryEntrypoint |
| build_backup_api | wire_gui_entrypoint |
| build_worker_api | wire_celery_entrypoint |
| _worker_api() | get_celery_entrypoint() |

---

## Tone

- Russian if Roman writes in Russian.
- Short paragraphs; tables for comparisons.
- If Roman is frustrated by contradiction, explicitly separate View 1 vs View 2 in one sentence: «По ощущению — X; по слоям кода — Y».
- After analogy, always list **real file/class names** in View 2.
- Do not skip CeleryEntrypoint, ports, or bootstrap wiring when explaining workers.

---

## Mini template

```markdown
## Что произошло (путь)
1. ...
2. ...

## Кто в коде (слои)
| Шаг | Слой | Файл/класс |
|-----|------|------------|
| ... | ... | ... |

**Граница:** GUI останавливается на …; Redis/Celery/Telethon трогает только …
```
