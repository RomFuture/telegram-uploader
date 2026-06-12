# use_cases — мануал слоя

> Краткий путеводитель по orchestration-слою telegram-uploader.  
> Канон архитектуры: [docs/PROJECT.md](../../docs/PROJECT.md).

---

## Зачем этот слой

`use_cases` — **мозг приложения**: сценарии «создать сессию», «запустить backup», «восстановить файл».  
Он знает **порядок шагов** и **когда** что вызывать, но не знает:

- как рисовать Tkinter (`application`);
- как ходить в Postgres/SQLAlchemy (`infrastructure/db`);
- как дергать Celery напрямую (только через `TaskQueuePort`).

**Ядро правил** (статусы, переходы) — в `domain`.  
**Контракты наружу** — в `use_cases/public`.

---

## Карта связей (одним взглядом)

```
                    ┌─────────────────────────────────────┐
                    │           use_cases/public           │
                    │  BackupApi (GUI)  WorkerApi (Celery) │
                    │  commands · results                  │
                    └──────────────┬──────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
   ┌──────────┐            ┌─────────────┐           ┌───────────┐
   │ session/ │            │   backup/   │           │ restore/  │
   │ create   │            │ enqueue     │           │ session   │
   │ progress │            │ pipeline    │           │ volume    │
   └────┬─────┘            │ archive     │           └─────┬─────┘
        │                  │ upload      │                 │
        │                  │ cleanup     │                 │
        │                  │ report_fail │                 │
        │                  │ gates       │                 │
        │                  │ idempotency │                 │
        │                  └──────┬──────┘                 │
        │                         │                        │
        └─────────────────────────┼────────────────────────┘
                                  ▼
                    ┌─────────────────────────────────────┐
                    │            use_cases/shared          │
                    │  persistence (*Record)               │
                    │  mappers (Record ↔ domain)           │
                    │  repositories (Protocol)             │
                    │  ports (Protocol → infra)            │
                    │  dto · types (internal)              │
                    └──────────────┬──────────────────────┘
                                   ▼
                              domain/
```

**Правило импортов:** код в `session/`, `backup/`, `restore/` может тянуть `shared/` и `domain`.  
Adapters (GUI, workers) — **только** `use_cases.public`.

---

## public/ — единственная «дверь»

| Файл | Роль |
|------|------|
| `commands.py` | Вход: `StartSessionCommand`, `EnqueueFileCommand`, `RestoreSessionCommand` |
| `results.py` | Выход: frozen DTO без domain entity (`SessionResult`, …) |
| `backup_api.py` | Собирает GUI-сценарии, маппит domain → `*Result` |
| `worker_api.py` | Собирает worker-сценарии + `report_*_failure` |

**Зачем отдельный public:** adapters не зависят от внутренней структуры папок. Можно переносить UC между `backup/` и `shared/`, не ломая GUI.

**Кто вызывает:**

| API | Entry (infra) | Use cases внутри |
|-----|---------------|------------------|
| `BackupApi` | `BackendReceiver` ← `build_backup_api()` | session + backup + restore |
| `WorkerApi` | `tasks.py` ← `build_worker_api()` | backup (process_*) + restore (volume) |

---

## session/ — жизнь сессии

| Модуль | Применение | Связи |
|--------|------------|-------|
| `create_session.py` | Новая сессия + ключ шифрования | `domain.create_session` → `SessionRepository.add` → `SessionCreateOutcome` |
| `get_session_progress.py` | Очередь для GUI Refresh | `SourceItemRepository.list_by_session` → `SessionProgress` |

**Зачем два UC, а не один «SessionService»:** create и read progress — разные сценарии с разными зависимостями; проще тестировать по отдельности.

**Важно:** `display_name` в progress берётся из **record**, не из пути на диске ([INTERNAL_SPEC §6](../../docs/INTERNAL_SPEC.md)).

---

## backup/ — pipeline архивации и upload

### Use case-классы (основной поток)

| UC | Когда | Порты / repos | Следующий шаг |
|----|-------|---------------|---------------|
| `EnqueueSourceItemUseCase` | GUI Add File | `SourceItemRepository` | только запись в БД (`queued`); worker — после Start Backup |
| `StartBackupPipelineUseCase` | GUI Start Backup | `Repositories`, `TaskQueuePort` | session→running; archive для всех `queued` |
| `ProcessArchiveVolumeUseCase` | worker archive | sessions, items, volumes, `ArchiveServicePort`, `TaskQueuePort` | 7z → volumes в БД → `enqueue_upload` |
| `ProcessUploadVolumeUseCase` | worker upload | items, volumes, `StorageProviderPort`, `TaskQueuePort` | Telegram → refs в БД → `enqueue_cleanup` |
| `CleanupVolumeUseCase` | worker cleanup | items, volumes | удалить temp; item→`completed` |
| `Report*FailureUseCase` | worker после retries | items, volumes | статус→`failed` |

### Вспомогательные модули (не UC, но критичны)

| Модуль | Зачем | Кто зовёт |
|--------|-------|-----------|
| `gates.py` | Preconditions: «только если статус X» | `start_backup_pipeline`, process_* |
| `idempotency.py` | Celery retry: skip / redo / fail | `process_archive`, `process_upload`, `process_cleanup` |
| `report_failure.py` | Идempotent mark failed | `WorkerApi.report_*` ← `tasks.py` |

### Путь в archive

**Batch only:** `StartBackupPipeline` → archive только для `queued`. Add File **не** ставит задачу в Celery.

---

## restore/ — скачивание и распаковка

| Модуль | Применение | Связи |
|--------|------------|-------|
| `restore_session.py` | GUI Restore Session | sessions (ключ) + volumes + provider + **extract** → `dest_path` |
| `process_restore_volume.py` | worker restore (один том) | download в staging |
| `download_volume.py` | общий шаг download | `restore_ref_for_volume` → provider |
| `refs.py` | выбор ref для provider | client ref → message:chat:id → bot file_id |

**Restore session (полный):** staging = encrypted `.7z.*`; **результат пользователю** — после `ArchiveServicePort.extract` в выбранной папке.

---

## shared/ — общее для всех веток

### persistence.py — `*Record`

Plain dataclass для БД-слоя use_cases: `id`, строковые `status`, `Path` как `str`.  
**Не** domain entity — чтобы repos не тащили enum/domain наружу.

### mappers.py

Симметричные пары `*_record_to_domain` / `domain_to_*_record`.  
Единственное место перевода Record ↔ domain внутри UC.

### repositories/

| Protocol | Методы (идея) |
|----------|----------------|
| `SessionRepository` | add, get, require, update |
| `SourceItemRepository` | add, list_by_session, require, update |
| `ArchiveVolumeRepository` | add, list/require for session, require, update |

`loading.py` — `require_*_record` + `DomainError` если None.

Реализация: `infrastructure/db/sqlalchemy_repositories.py`.

### ports/

| Protocol | Infra-реализация | Назначение |
|----------|------------------|------------|
| `TaskQueuePort` | `CeleryTaskQueue` | enqueue archive/upload/cleanup/restore **без** import celery в UC |
| `ArchiveServicePort` | `ArchiveServiceAdapter` → `SevenZipService` | archive + extract |
| `StorageProviderPort` | `TelegramProviderV1` | upload/download Telegram |

`dto.py` — типы ответов провайдера (`UploadResult`, …).

### types.py

Re-export `Session`, `SourceItem`, `ArchiveVolume` **только для внутреннего** кода UC (gates, mappers).  
В `use_cases/__init__.py` domain entity **не** экспортируются наружу.

---

## Цепочка данных (запомнить один раз)

```
PostgreSQL
  → ORM Row
  → infrastructure/db/mappers
  → *Record                    ← shared/persistence
  → use_cases/shared/mappers
  → domain entity              ← правила в actions.py
  → use case orchestration
  → ports (7z, Telegram, Celery)
```

Use case **внутри** думает domain; наружу (public) отдаёт только `*Result`.

---

## Типовые зависимости UC (шаблон)

Каждый UC — `@dataclass(frozen=True)` с полями-зависимостями:

```python
@dataclass(frozen=True, slots=True)
class SomeUseCase:
    repos_or_ports: SomeProtocol

    def execute(self, ...) -> ...:
        entity = self.repo.require(id)      # domain
        ... domain.mark_* / gates ...
        self.repo.update(record)            # persistence
        self.task_queue.enqueue_*(...)      # async next step
```

Сборка зависимостей — **только** в `infrastructure/bootstrap.py`, не в UC.

---

# Три сценария отладки (PyCharm / debugger)

**Общая настройка:**

```bash
docker compose up -d
# Run configuration:
#   Module: application.gui   (сценарии 1 и 3)
#   PYTHONPATH=src
# Breakpoints: Step Over (F8), Step Into (F7)
```

Workers для сценария 2: либо `docker compose logs -f celery-worker-archive-1`, либо attach к worker-процессу в контейнере.

---

## Сценарий 1 · Session + Progress (ветка `session/` + public GUI)

**Цель:** пройти create session, enqueue, progress — без worker.

**Покрывает:** `CreateSessionUseCase`, `GetSessionProgressUseCase`, `EnqueueSourceItemUseCase`, `BackupApi`, `shared/mappers`, `shared/repositories`, `TaskQueuePort.enqueue_archive` (stub до Redis).

### Шаги

1. Breakpoint: `CreateSessionUseCase.execute` — последняя строка перед `return`.
2. GUI → **Start Session** (пустой ключ).
3. **F7** в `domain.create_session` → **F8** через `domain_to_session_record` → `sessions.add`.
4. Смотри `SessionCreateOutcome.generated_encryption_key` — не None.
5. Breakpoint: `EnqueueSourceItemUseCase.execute` — после `create_source_item`.
6. GUI → **Add File** (любой файл, display name свой).
7. **F7** в `domain.create_source_item`; проверь `display_name` ≠ `source_path.name`.
8. Breakpoint: `GetSessionProgressUseCase.execute`.
9. GUI → **Refresh Progress**.
10. **F8** по `list_by_session` → items[0].display_name из record.

### Что должно сложиться в голове

```
BackupApi.start_session → CreateSessionUseCase → domain + SessionRepository
BackupApi.enqueue_file  → EnqueueSourceItemUseCase → domain + repo + TaskQueuePort
BackupApi.get_progress  → GetSessionProgressUseCase → repo (records only)
```

---

## Сценарий 2 · Backup worker pipeline (ветка `backup/` + ports)

**Цель:** один файл от archive до cleanup; idempotency + gates + порты.

**Покрывает:** `ProcessArchiveVolumeUseCase`, `ProcessUploadVolumeUseCase`, `CleanupVolumeUseCase`, `gates`, `idempotency`, `ArchiveServicePort`, `StorageProviderPort`, `WorkerApi`.

### Подготовка

1. Сценарий 1: session + Add File.
2. GUI → **Start Backup** (если archive ещё не ушёл eager — не страшно).
3. Breakpoint: `ProcessArchiveVolumeUseCase.execute` (entry).
4. Дождись task в worker **или** unit-тест `tests/test_public_api.py::test_worker_api_process_archive_delegates` под Debug.

### Шаги (archive task)

1. **F7** в `decide_archive_on_retry` (`idempotency.py`) — SKIP vs RUN.
2. **F7** в `require_item_queued` или gate внутри archive UC.
3. **F7** в `archive_service.archive` (адаптер → `SevenZipService`) — единственный выход в infra из UC.
4. **F8** через persist volumes → `task_queue.enqueue_upload`.
5. Breakpoint: `ProcessUploadVolumeUseCase.execute`.
6. После archive: **F7** в `storage_provider.upload_file`; смотри запись `external_*`, `provider_download_ref`.
7. Breakpoint: `CleanupVolumeUseCase.execute` — item→`completed`.

### Опционально: failure-ветка

1. Breakpoint: `WorkerApi.report_archive_failure`.
2. Симулируй exception в archive UC или дождись реального fail после retries.
3. **F7** в `ReportArchiveFailureUseCase` → `domain.mark_source_item(FAILED)`.

### Что должно сложиться

```
WorkerApi.process_archive → ProcessArchiveVolumeUseCase
  → idempotency → gates → ArchiveServicePort → repos → TaskQueuePort
WorkerApi.process_upload  → StorageProviderPort → enqueue_cleanup
WorkerApi.process_cleanup → filesystem cleanup → completed
```

---

## Сценарий 3 · Restore end-to-end (ветка `restore/` + extract)

**Цель:** download refs + extract в `dest_path` — полная restore-ветка.

**Покрывает:** `RestoreSessionUseCase`, `download_volume`, `refs.restore_ref_for_volume`, `ArchiveServicePort.extract`, `SessionRepository` (encryption_key).

### Подготовка

Нужна **завершённая** backup-сессия (volumes в БД со refs). Если Bot API 404 — гоняй под Debug тест:

`tests/test_use_cases_restore.py::test_restore_downloads_volumes_in_part_order_and_extracts_to_dest`

с breakpoints в UC (fake provider + fake archive).

### Шаги (GUI или тест)

1. Breakpoint: `RestoreSessionUseCase.execute` — entry.
2. **F7** `sessions.require` → возьми `session.encryption_key`.
3. **F7** `archive_volumes.require_for_session` — порядок по `part_number`.
4. Breakpoint: `restore_ref_for_volume` в `refs.py`.
5. **F8** по цепочке ref: provider_download_ref → иначе `message:{chat}:{id}` → иначе file_id.
6. Breakpoint: `download_volume_to_dir` → `storage_provider.get_file_info` / `download_file`.
7. Breakpoint: `archive_service.extract` — volumes из staging, **dest_dir = dest_path пользователя**.
8. Return: один `Path` в выбранной папке, не в staging.

### Worker-ответвление (коротко)

Breakpoint: `ProcessRestoreVolumeUseCase.execute` — только download одного volume в staging (без extract).  
Вызывается из `WorkerApi.process_restore_volume` (отдельная Celery task `restore_volume`).

### Что должно сложиться

```
BackupApi.restore_session → RestoreSessionUseCase
  → SessionRepository (key)
  → download_volume × N (refs + StorageProviderPort)
  → ArchiveServicePort.extract → dest_path
```

---

## Шпаргалка: «где искать, если…»

| Симптом | Смотри |
|---------|--------|
| Неверный ключ в БД | `session/create_session.py` |
| Progress показывает имя файла с диска | `get_session_progress.py` — должно быть `display_name` record |
| Archive не стартует | `gates.py`, `idempotency.py`, статус item |
| Upload без refs для restore | `process_upload_volume.py` + provider |
| Stuck после worker fail | `report_failure.py`, `WorkerApi`, `tasks._run_with_failure_report` |
| Restore 404 / wrong ref | `restore/refs.py`, `target_chat_id` в bootstrap |
| Файл не в dest_path | `restore_session.py` — extract vs staging |

---

## Дальше читать

| Тема | Документ |
|------|----------|
| Архитектура и gate/smoke | [docs/PROJECT.md](../../docs/PROJECT.md) |
| Продуктовые правила | [docs/INTERNAL_SPEC.md](../../docs/INTERNAL_SPEC.md) |
| Client API refs | [docs/TELEGRAM_CLIENT_API_MIGRATION.md](../../docs/TELEGRAM_CLIENT_API_MIGRATION.md) |
| Unit-тесты UC | `tests/test_use_cases_*.py`, `tests/test_public_api.py` |

---

*Обновлено после рефакторинга UC-1 … UC-8 (2026-06).*
