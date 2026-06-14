# use_cases — мануал слоя

> Краткий путеводитель по orchestration-слою telegram-uploader.  
> Канон архитектуры: [docs/PROJECT.md](../../docs/PROJECT.md).  
> Журнал backend-изменений: [docs/refactor/CHANGES.md](../../docs/refactor/CHANGES.md).

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
                    │  GuiEntrypoint   CeleryEntrypoint   │
                    │  commands · results                  │
                    └──────────────┬──────────────────────┘
                                   │
    ┌──────────────┬───────────────┼───────────────┬──────────────┐
    ▼              ▼               ▼               ▼              ▼
┌─────────┐  ┌──────────┐   ┌───────────┐   ┌──────────┐  ┌──────────┐
│ session/│  │ backup/  │   │ restore/  │   │ telegram/│  │ (нет     │
│ CRUD    │  │ pipeline │   │ session   │   │ test_api │  │  других  │
│ folders │  │ gates    │   │ preflight │   └──────────┘  │  top pkg)│
│ progress│  │ idempotency│ │ scope     │                   └──────────┘
└────┬────┘  └────┬─────┘   └─────┬─────┘
     │            │               │
     └────────────┴───────────────┘
                    ▼
      ┌─────────────────────────────────────┐
      │            use_cases/shared          │
      │  persistence (*Record)               │
      │  mappers (Record ↔ domain)           │
      │  repositories (Protocol)             │
      │  ports (Protocol → infra)            │
      │  folders.py (DEFAULT_FOLDER_NAME)    │
      │  dto · types (internal)              │
      └──────────────┬──────────────────────┘
                     ▼
                domain/
```

**Правило импортов:** код в `session/`, `backup/`, `restore/`, `telegram/` может тянуть `shared/` и `domain`.  
Adapters (GUI, workers) — **только** `use_cases.public` (см. `tests/test_layer_boundaries.py`).

---

## public/ — единственная «дверь»

| Файл | Роль |
|------|------|
| `commands.py` | Входные DTO (см. таблицу ниже) |
| `results.py` | Выход: frozen DTO без domain entity |
| `gui_entrypoint.py` | GUI-сценарии → `*Result` |
| `celery_entrypoint.py` | Celery task-сценарии + `report_*_failure` |

### commands.py (полный список)

| Command | Поля (суть) |
|---------|-------------|
| `StartSessionCommand` | `profile_name`, optional `encryption_key` |
| `UnlockSessionCommand` | `profile_name`, `encryption_key` |
| `CreateDatabaseCommand` | `profile_name`, `encryption_key` (обязательный ключ) |
| `EnqueueFileCommand` | `session_id`, `source_path`, `display_name`, optional `folder_id` |
| `CreateFolderCommand` | `session_id`, `name` |
| `RestoreSessionCommand` | `session_id`, `dest_path`, optional `folder_id` (sidebar) |
| `RenameSourceItemCommand` | `source_item_id`, `display_name` |
| `MoveSourceItemCommand` | `source_item_id`, `folder_id` |
| `DeleteSourceItemCommand` | `source_item_id` |

### GuiEntrypoint — методы

| Метод | UC / поведение |
|-------|----------------|
| `start_session` | `CreateSessionUseCase` |
| `unlock_session` | `UnlockSessionUseCase` |
| `create_database` | `CreateDatabaseUseCase` + папка **All files** |
| `list_profiles` | `ListSessionProfilesUseCase` |
| `list_folders` / `create_folder` | `ListFoldersUseCase` / `CreateFolderUseCase` |
| `enqueue_file` | `EnqueueSourceItemUseCase` |
| `start_backup` | `StartBackupPipelineUseCase` |
| `get_queue_snapshot` | `GetSessionQueueSnapshotUseCase` |
| `restore_session` | `RestoreSessionUseCase` |
| `check_restore_ready` | `CheckRestoreReadyUseCase` (+ optional `folder_id`) |
| `verify_storage_provider` | `VerifyStorageProviderUseCase` (provider inject из GUI) |
| `rename` / `move` / `delete` source item | `manage_source_item.py` |

**Зачем отдельный public:** adapters не зависят от внутренней структуры папок.

**Кто вызывает:**

| API | Entry (infra) | Use cases внутри |
|-----|---------------|------------------|
| `GuiEntrypoint` | `BackendReceiver` ← `wire_gui_entrypoint()` | session + backup + restore + telegram |
| `CeleryEntrypoint` | `tasks.py` ← `get_celery_entrypoint()` | backup (process_*) + restore volume only |

> **GUI restore** идёт in-process через `RestoreSessionUseCase` (download + extract).  
> `ProcessRestoreVolumeUseCase` / Celery `restore_volume` — отдельный hook на один том **без** extract; на GUI-путь не влияет.

---

## session/ — жизнь сессии и виртуальные папки

| Модуль | Применение | Связи |
|--------|------------|-------|
| `create.py` | Create session / database / folder | `CreateSessionUseCase`, `CreateDatabaseUseCase`, `CreateFolderUseCase` |
| `unlock_session.py` | Unlock существующей session по profile + key | `SessionRepository` |
| `list.py` | Списки профилей и папок | `ListSessionProfilesUseCase`, `ListFoldersUseCase` |
| `get_session_queue_snapshot.py` | Снимок очереди для GUI Refresh | items + `folder_id` / `folder_name`, size/modified labels |
| `manage_source_item.py` | Rename / Move / Delete | `SourceItemRepository`, move проверяет `FolderRepository` |

### Модель папок (GUI + restore)

- В БД: `backup_folders` + `source_items.folder_id` (см. migration `0004`).
- Default при создании базы: **`All files`** (`shared/folders.DEFAULT_FOLDER_NAME`).
- **All files** в GUI — **агрегирующий вид**: показывает все файлы сессии; restore из All files = **вся** restorable сессия.
- Именованная папка (TEST, …) — фильтр по `folder_id`; restore = только файлы этой папки.
- **Move to folder** — только смена `folder_id` (логическое «положить в папку»), не удаление из All files view.

**Важно:** `display_name` в progress берётся из **record**, не из `source_path.name` ([INTERNAL_SPEC §6](../../docs/INTERNAL_SPEC.md)).

---

## backup/ — pipeline архивации и upload

### Use case-классы (основной поток)

| UC | Когда | Порты / repos | Следующий шаг |
|----|-------|---------------|---------------|
| `EnqueueSourceItemUseCase` | GUI Add File | `SourceItemRepository`, `FolderRepository` | запись `queued`; Celery — после Start Backup |
| `StartBackupPipelineUseCase` | GUI Start Backup | `Repositories`, `TaskQueuePort` | session→running; archive для `queued` |
| `ProcessArchiveVolumeUseCase` | worker archive | sessions, items, volumes, `ArchiveServicePort`, `TaskQueuePort` | 7z → volumes → `enqueue_upload` |
| `ProcessUploadVolumeUseCase` | worker upload | items, volumes, `StorageProviderPort`, `TaskQueuePort` | Telegram → `client:` ref в БД → cleanup |
| `CleanupVolumeUseCase` | worker cleanup | items, volumes | temp удалён; item→`completed` |
| `Report*FailureUseCase` | worker после retries | items, volumes | статус→`failed` |

### Вспомогательные модули (не UC)

| Модуль | Зачем | Кто зовёт |
|--------|-------|-----------|
| `gates.py` | Preconditions: «только если статус X» | `start_backup_pipeline`, process_* |
| `idempotency.py` | Celery retry: skip / redo / fail | process_archive / upload / cleanup |
| `report_failure.py` | Idempotent mark failed | `CeleryEntrypoint.report_*` ← `tasks.py` |

**Batch only:** `StartBackupPipeline` → archive только для `queued`. Add File **не** ставит задачу в Celery.

---

## restore/ — скачивание, scope, распаковка

| Модуль | Применение | Связи |
|--------|------------|-------|
| `restore_session.py` | **GUI Restore Session** | scope filter + writable dest probe + download × N + extract → `dest_path` |
| `check_restore_ready.py` | Preflight перед restore | counts + reason; scope copy в `application/restore_preflight_scope.py` |
| `scope.py` | Фильтр по sidebar folder | `is_session_wide_restore_scope`, `filter_restorable_ids_by_folder` |
| `download_volume.py` | Общий шаг download | `restore_ref_for_volume` → provider (+ optional `on_progress`) |
| `observation/restore_download_progress.py` | Heartbeat / % logging during restore download | callback для Telethon `progress_callback`; не restore policy |
| `refs.py` | Restore ref policy | `assess_restore_ref` через `StorageProviderPort`; legacy → `UNSUPPORTED_LEGACY` |
| `process_restore_volume.py` | worker: один том | download в staging **без** extract |

### Restore session (полный GUI-путь)

1. `source_item_ids_restorable_in_session(volumes, storage_provider)` — IDs items, которые можно restore во всей session.
2. `filter_restorable_ids_by_folder` — сужение до выбранной папки; «All files» = `is_session_wide_restore_scope`.
3. `validate_restore_dest_path(dest_path)`.
4. Для каждого source item: volumes по `part_number` → `download_volume_to_dir` (progress logs).
5. `ArchiveServicePort.extract` → **файлы пользователю в `dest_path`**, staging = encrypted `.7z.*`.

### refs.py — restore policy (provider-agnostic)

| Функция | Поведение |
|---------|-----------|
| `is_volume_restorable(volume, provider)` | UPLOADED + `provider.assess_restore_ref(ref) == RESTORABLE` |
| `restore_ref_for_volume(volume, provider)` | RESTORABLE → `resolve_restore_ref`; legacy → `legacy_volumes` |
| `is_legacy_volume` / `count_legacy_volumes` | UPLOADED + `UNSUPPORTED_LEGACY`; optional filter по item ids |
| `count_incomplete_volumes` | non-restorable в scope, без legacy |
| `source_item_ids_in_restore_scope` | item ids для текущей папки или всей session |
| `source_item_ids_restorable_in_session(volumes, provider)` | item restorable если **все** parts restorable |
| `filter_restorable_ids_by_folder(restorable_ids_in_session=...)` | session IDs → subset для выбранной папки |
| `is_session_wide_restore_scope(folder_id, folder_name)` | True для GUI «All files» (вся session) |

Формат ref (`client:` и т.д.) знает только adapter в `infrastructure/providers/`.

### Логирование restore

Logger `observation.restore.session` — start/complete scope, download/extract milestones.
Logger `observation.restore.download` — 10% progress + 30s heartbeat (см. [CHANGES.md](../../docs/refactor/CHANGES.md)).

---

## telegram/ — opt-in проверка провайдера

| Модуль | Применение |
|--------|------------|
| `verify_storage_provider.py` | Settings → Test Client API: healthcheck → upload test file → download → byte compare |

Не на hot path backup/restore; provider передаётся из GUI (`build_client_provider`).

---

## shared/ — общее для всех веток

### persistence.py — `*Record`

Plain dataclass для repos: `id`, строковые `status`, paths как `str`.  
`SourceItemRecord.folder_id: UUID | None`.  
`BackupFolderRecord` — virtual folders.

### mappers.py

Симметричные пары `*_record_to_domain` / `domain_to_*_record`.  
`folder_id` сохраняется при update status (не затирается).

### repositories/

| Protocol | Методы (идея) |
|----------|----------------|
| `SessionRepository` | add, get, require, update, find_by_profile_name |
| `SourceItemRepository` | add, list_by_session, require, update, delete |
| `ArchiveVolumeRepository` | add, list/require for session, require, update |
| `FolderRepository` | add, get, list_by_session |

`loading.py` — `require_*_record` + `DomainError` если None.

Реализация: `infrastructure/db/sqlalchemy_repositories.py`.

### ports/

| Protocol | Infra-реализация (default) | Назначение |
|----------|----------------------------|------------|
| `TaskQueuePort` | `CeleryTaskQueue` | enqueue archive/upload/cleanup/restore |
| `ArchiveServicePort` | `ArchiveServiceAdapter` → `SevenZipService` | archive + extract |
| `StorageProviderPort` | `TelegramClientProvider` (`TELEGRAM_PROVIDER=client`) | upload/download; `assess_restore_ref` / `resolve_restore_ref`; optional `on_progress` kwarg |

Legacy: `TelegramProviderV1` (Bot API) — только upload path; restore refs v1 не поддерживает.

`dto.py` — `UploadResult`, `ProviderFileInfo`, `ClassifiedProviderError`, …

### folders.py

`DEFAULT_FOLDER_NAME = "All files"`, `is_default_folder_name()`.

### types.py

Re-export `Session`, `SourceItem`, `ArchiveVolume` **только для внутреннего** UC-кода.  
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

> **Полный список breakpoint'ов backup pipeline (101 точка):** [DEBUG_BACKUP.md](DEBUG_BACKUP.md)

**Общая настройка:**

```bash
docker compose up -d
# Run configuration: Module application.gui, PYTHONPATH=src
# Packaged: telegram-uploader
tail -f telegram-uploader.log   # restore progress / workers
```

---

## Сценарий 1 · Session + folders + Progress

**Цель:** create/unlock, folders, enqueue с `folder_id`, progress.

**Покрывает:** `CreateDatabaseUseCase`, `CreateFolderUseCase`, `EnqueueSourceItemUseCase`, `GetSessionQueueSnapshotUseCase`, `GuiEntrypoint`.

### Шаги

1. Breakpoint: `CreateDatabaseUseCase.execute` — после `folders.add(All files)`.
2. GUI → **New database** (имя + ключ).
3. Breakpoint: `EnqueueSourceItemUseCase.execute` — проверь `folder_id` из sidebar.
4. GUI → **Add File** в папке TEST.
5. Breakpoint: `GetSessionQueueSnapshotUseCase.execute` — `folder_name`, `display_name`.
6. GUI → **Refresh Progress**.

---

## Сценарий 2 · Backup worker pipeline

**Цель:** archive → upload (`client:` ref) → cleanup.

**Покрывает:** `ProcessArchiveVolumeUseCase`, `ProcessUploadVolumeUseCase`, `CleanupVolumeUseCase`, `gates`, `idempotency`, ports, `CeleryEntrypoint`.

### Подготовка

Session + Add File + **Start Backup**. Breakpoint в `ProcessArchiveVolumeUseCase.execute` или unit-тест `test_celery_entrypoint_process_archive_delegates`.

### Шаги

1. **F7** `decide_archive_on_retry` → **F7** gates → **F7** `archive_service.archive`.
2. **F8** persist volumes → `enqueue_upload`.
3. **F7** `storage_provider.upload_file` — проверь `provider_download_ref` starts with `client:`.
4. **F7** `CleanupVolumeUseCase` → item `completed`.

---

## Сценарий 3 · Restore (scope + download + extract)

**Цель:** folder-scoped restore, client refs, extract в `dest_path`, progress logs.

**Покрывает:** `CheckRestoreReadyUseCase`, `RestoreSessionUseCase`, `scope.py`, `refs.py`, `observation/restore_download_progress.py`, extract.

### Подготовка

Completed backup (client refs). Unit: `tests/test_use_cases_restore.py`, `tests/test_restore_scope_and_progress.py`.

### Шаги

1. Breakpoint: `CheckRestoreReadyUseCase.execute(..., folder_id=...)` — message с scope.
2. Breakpoint: `RestoreSessionUseCase.execute` — `filter_restorable_ids_by_folder`.
3. **F7** `validate_restore_dest_path`.
4. Breakpoint: `restore_ref_for_volume` — только `client:` (legacy → exception).
5. Breakpoint: `observation.restore_download_progress.make_download_progress_callback` → `download_file(..., on_progress=...)`.
6. **F7** `archive_service.extract` — `dest_dir == user dest_path`.
7. Лог: `observation.restore.session` + `observation.restore.download` в `telegram-uploader.log`.

### Worker-ответвление

`ProcessRestoreVolumeUseCase` — один volume в staging, **без** extract и **без** folder scope (не GUI path).

---

## Шпаргалка: «где искать, если…»

| Симптом | Смотри |
|---------|--------|
| Неверный ключ в БД | `session/create.py`, `unlock_session.py` |
| Таблица показывает имя с диска | `get_session_queue_snapshot.py` — должно быть `display_name` |
| Файл не в нужной папке sidebar | `enqueue` / `manage_source_item.move` → `folder_id` |
| Restore качает «лишние» файлы | `restore/scope.py`, `RestoreSessionCommand.folder_id`, GUI `explorer.selected_folder_id` |
| Restore 404 / legacy bot | `restore/refs.py` — только `client:`; re-backup |
| Permission denied на extract | `restore_session.py` (`validate_restore_dest_path`), GUI preflight в `application/gui/restore_dest.py` |
| Долгая тишина в логах при download | `observation/restore_download_progress.py`, Telethon callback в `TelegramClientProvider` |
| Archive не стартует | `gates.py`, `idempotency.py`, статус item |
| Upload без refs | `process_upload_volume.py` + client provider |
| Stuck после worker fail | `report_failure.py`, `tasks._run_with_failure_report` |
| Test Client API fail | `telegram/verify_storage_provider.py`, Telethon session file, chat membership |

---

## Тесты слоя

| Область | Файлы |
|---------|--------|
| Restore + refs | `tests/test_use_cases_restore.py`, `tests/test_restore_refs.py`, `tests/test_restore_scope_and_progress.py`, `tests/test_restore_dest_path.py` |
| Public API wiring | `tests/test_public_api.py`, `tests/test_backend_receiver.py` |
| Verify storage provider UC | `tests/test_verify_storage_provider.py` |
| Provider contract | `tests/test_provider_contract.py` |
| Layer boundaries | `tests/test_layer_boundaries.py` |

---

## P0.1 audit notes (2026-06-12)

**Согласовано с кодом:**

- Public API = единственная дверь; facade удалён.
- Pipeline rules в `backup/gates.py`, `backup/idempotency.py`, `restore/refs.py` (не domain).
- Restore GUI path = `RestoreSessionUseCase` in-process; worker restore volume — отдельный hook.
- Folders: DB + UC + restore scope + All files aggregate semantics.
- Client API-only restore refs; logging в restore/download.

**Known gaps (не блокируют P0.1 doc sync):**

- `ProcessRestoreVolumeUseCase` не использует folder scope / progress (by design — не GUI path).
- `public/__init__.py` экспортирует подмножество commands (полный список — `commands.py`).
- Correlation `session_id` в логах — backlog P0.2+, не в UC.

---

## Дальше читать

| Тема | Документ |
|------|----------|
| Архитектура и gate/smoke | [docs/PROJECT.md](../../docs/PROJECT.md) |
| Backend change journal | [docs/refactor/CHANGES.md](../../docs/refactor/CHANGES.md) |
| Продуктовые правила | [docs/INTERNAL_SPEC.md](../../docs/INTERNAL_SPEC.md) |
| Client API refs | [docs/TELEGRAM_CLIENT_API_MIGRATION.md](../../docs/TELEGRAM_CLIENT_API_MIGRATION.md) |
| Backlog P0.1 | [docs/BACKLOG.md](../../docs/BACKLOG.md) |

---

*Аудит P0.1 + sync с кодом: 2026-06-12 (logging, folder-scoped restore, client refs, virtual folders).*
