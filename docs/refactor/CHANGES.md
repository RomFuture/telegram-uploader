# Рефакторинг `use_cases` — сводка изменений (2026-06)

Краткий changelog по коду. Детали по UC-01 … UC-08 → [README.md](README.md).

**Статус кода:** UC-1 … UC-8 **реализованы**. Post-refactor roadmap Phase A–G **реализован**. GUI fixes roadmap PR-G1 … PR-G6 **реализован** (см. ниже).

---

## Комментарии Roman (review)

| UC | Комментарий | Решение |
|----|-------------|---------|
| smoke | backup + restore | ✅ OK (Client API default + restore preflight) |

---

## UC-1 … UC-8

См. предыдущие секции в git history; кратко:

- **UC-1:** auto-key в [`CreateSessionUseCase`](../../src/use_cases/session/create_session.py), [`GetSessionProgressUseCase`](../../src/use_cases/session/get_session_progress.py)
- **UC-2:** [`use_cases/public/`](../../src/use_cases/public/) — BackupApi, WorkerApi
- **UC-3:** facade удалён; bootstrap [`build_*_api`](../../src/infrastructure/bootstrap.py)
- **UC-4:** failure reporting в WorkerApi + tasks
- **UC-5:** [`restore_ref_for_volume`](../../src/use_cases/restore/refs.py)
- **UC-6:** [`use_cases/shared/`](../../src/use_cases/shared/) layout
- **UC-7:** restore E2E extract → `dest_path`
- **UC-8:** import-linter + CI

---

## Post-refactor roadmap

| Phase | Статус |
|-------|--------|
| A · R3 GUI autoclave key | ✅ |
| B · docs sync (PROJECT, BACKLOG) | ✅ |
| C · Client API provider | ✅ |
| D · MVP GUI polish | ✅ |
| E · P-demo run.sh + CI | ✅ |
| G · PROJECT §12 full GUI | ✅ |

---

## GUI fixes roadmap (PR-G1 … PR-G6)

План: backup только по Start Backup, KeePassXC-style Unlock/Create db, виртуальные папки, Client API по умолчанию, рабочий Restore, RAM slider (placeholder).

### PR-G1 · Backup только по «Start Backup»

**Проблема:** Add File сразу ставил задачу в Celery — workers начинали 7z/upload до нажатия Start Backup.

| Файл | Что изменилось |
|------|----------------|
| [`src/use_cases/backup/enqueue_source_item.py`](../../src/use_cases/backup/enqueue_source_item.py) | Убран вызов `task_queue.enqueue_archive`. UC только создаёт `source_items` со статусом `queued`. Добавлен опциональный `folder_id` (см. G3). Зависимость от `TaskQueuePort` удалена. |
| [`src/use_cases/backup/start_backup_pipeline.py`](../../src/use_cases/backup/start_backup_pipeline.py) | Единственная точка постановки archive-задач в очередь — вызывается из GUI по кнопке Start Backup. |
| [`src/use_cases/MANUAL.md`](../../src/use_cases/MANUAL.md) | Сценарий «Add File не запускает worker»; archive стартует только из Start Backup. |
| [`src/application/gui/app.py`](../../src/application/gui/app.py) | После Add File drawer показывает «File queued — click Start Backup when ready», без «In progress». |
| [`src/application/gui/drawer.py`](../../src/application/gui/drawer.py) | Состояния idle / working / result для очереди и restore. |
| [`tests/test_use_cases_backup.py`](../../tests/test_use_cases_backup.py) | После `enqueue` — `task_queue.archive_ids == []`; archive появляется только после `StartBackupPipelineUseCase`. |
| [`tests/test_public_api.py`](../../tests/test_public_api.py) | `test_enqueue_file_returns_queue_item_result`: проверка, что fake queue пуст после enqueue. |

---

### PR-G2 · Unlock / Create db (личный кабинет)

**Проблема:** Unlock всегда создавал новую сессию через `start_session` → `CreateSessionUseCase`, без lookup по имени базы и проверки ключа.

#### Domain

| Файл | Что изменилось |
|------|----------------|
| [`src/domain/errors.py`](../../src/domain/errors.py) | Новые factory-методы: `session_not_found_by_profile`, `wrong_encryption_key`, `profile_already_exists`, `legacy_volumes` (G5). |

#### Use cases (новые)

| Файл | Что изменилось |
|------|----------------|
| [`src/use_cases/session/list_session_profiles.py`](../../src/use_cases/session/list_session_profiles.py) | **Новый.** Возвращает отсортированный список `profile_name` из БД для combobox на экране Unlock. |
| [`src/use_cases/session/unlock_session.py`](../../src/use_cases/session/unlock_session.py) | **Новый.** `profile_name` + обязательный `encryption_key` → `find_by_profile_name` → `secrets.compare_digest` → `Session` или `WrongKeyError`. |
| [`src/use_cases/session/create_database.py`](../../src/use_cases/session/create_database.py) | **Новый.** Create db: обязательные имя и ключ пользователя, без auto-generate; при создании добавляет папку «All files» (G3). |
| [`src/use_cases/session/create_session.py`](../../src/use_cases/session/create_session.py) | Оставлен для legacy/API (`start_session`); GUI Unlock больше не использует auto-create на каждый вход. |

#### Repository + persistence

| Файл | Что изменилось |
|------|----------------|
| [`src/use_cases/shared/repositories/session.py`](../../src/use_cases/shared/repositories/session.py) | Протокол расширен: `list_profiles()`, `find_by_profile_name(name)`. |
| [`src/infrastructure/db/sqlalchemy_repositories.py`](../../src/infrastructure/db/sqlalchemy_repositories.py) | Реализация `list_profiles` / `find_by_profile_name` для Postgres. |
| [`tests/fakes/repositories.py`](../../tests/fakes/repositories.py) | In-memory реализация тех же методов для unit-тестов. |
| [`src/infrastructure/db/migrations/0003_unique_profile_name.sql`](../../src/infrastructure/db/migrations/0003_unique_profile_name.sql) | `UNIQUE(profile_name)` — одна база на имя (KeePassXC-модель). |

#### Public API + application layer

| Файл | Что изменилось |
|------|----------------|
| [`src/use_cases/public/commands.py`](../../src/use_cases/public/commands.py) | Команды `UnlockSessionCommand`, `CreateDatabaseCommand`. |
| [`src/use_cases/public/backup_api.py`](../../src/use_cases/public/backup_api.py) | Методы `unlock_session`, `create_database`, `list_profiles`. |
| [`src/infrastructure/bootstrap.py`](../../src/infrastructure/bootstrap.py) | Wiring новых UC в `build_backup_api`. |
| [`src/application/backend_receiver.py`](../../src/application/backend_receiver.py) | `unlock_session`, `create_database`, `list_profiles`; убран прямой `start_session` из GUI-пути. |
| [`src/application/gui/unlock.py`](../../src/application/gui/unlock.py) | **Новый.** Экран: Database name (combobox + Refresh), Encryption key, кнопки Unlock / Create db / Settings. |
| [`src/application/gui/app.py`](../../src/application/gui/app.py) | Flow Unlock → main; header `Database: {profile_name}`; обработка wrong key / profile already exists. |

---

### PR-G3 · Виртуальные папки (sidebar)

**Проблема:** sidebar «Locations» / «Backup queue» был заглушкой без организации файлов.

#### Schema

| Файл | Что изменилось |
|------|----------------|
| [`src/infrastructure/db/migrations/0004_backup_folders.sql`](../../src/infrastructure/db/migrations/0004_backup_folders.sql) | Таблица `backup_folders`; колонка `source_items.folder_id`; индексы. |
| [`src/infrastructure/db/orm.py`](../../src/infrastructure/db/orm.py) | ORM-модель `BackupFolderRow`; `folder_id` на `SourceItemRow`. |
| [`src/use_cases/shared/persistence.py`](../../src/use_cases/shared/persistence.py) | DTO `BackupFolderRecord`; `folder_id` в `SourceItemRecord`. |
| [`src/infrastructure/db/mappers.py`](../../src/infrastructure/db/mappers.py) | Маппинг folder_id / backup_folders. |

#### Use cases + repositories

| Файл | Что изменилось |
|------|----------------|
| [`src/use_cases/shared/folders.py`](../../src/use_cases/shared/folders.py) | Константа `DEFAULT_FOLDER_NAME = "All files"`. |
| [`src/use_cases/shared/repositories/folder.py`](../../src/use_cases/shared/repositories/folder.py) | **Новый.** Протокол `FolderRepository`: add, get, list_by_session, find_by_name. |
| [`src/use_cases/shared/repositories/__init__.py`](../../src/use_cases/shared/repositories/__init__.py) | `Repositories` bundle включает `folders`. |
| [`src/use_cases/session/create_folder.py`](../../src/use_cases/session/create_folder.py) | **Новый.** Создание папки в рамках сессии. |
| [`src/use_cases/session/list_folders.py`](../../src/use_cases/session/list_folders.py) | **Новый.** Список папок сессии для sidebar. |
| [`src/use_cases/backup/enqueue_source_item.py`](../../src/use_cases/backup/enqueue_source_item.py) | Параметр `folder_id`; валидация, что папка принадлежит сессии. |
| [`src/use_cases/session/get_session_progress.py`](../../src/use_cases/session/get_session_progress.py) | В progress items добавлены `folder_id` / `folder_name`. |
| [`src/use_cases/shared/mappers.py`](../../src/use_cases/shared/mappers.py) | `folder_id` при записи source item. |
| [`src/infrastructure/db/sqlalchemy_repositories.py`](../../src/infrastructure/db/sqlalchemy_repositories.py) | `SqlAlchemyFolderRepository` + folder_id в source_items. |
| [`tests/fakes/repositories.py`](../../tests/fakes/repositories.py) | `InMemoryFolderRepository`; bind в `InMemoryRepositories`. |

#### Public API + GUI

| Файл | Что изменилось |
|------|----------------|
| [`src/use_cases/public/commands.py`](../../src/use_cases/public/commands.py) | `CreateFolderCommand`; `folder_id` в `EnqueueFileCommand`. |
| [`src/use_cases/public/results.py`](../../src/use_cases/public/results.py) | `FolderResult`; `folder_id` / `folder_name` в progress. |
| [`src/use_cases/public/backup_api.py`](../../src/use_cases/public/backup_api.py) | `list_folders`, `create_folder`; enqueue с folder_id. |
| [`src/application/backend_receiver.py`](../../src/application/backend_receiver.py) | DTO `FolderViewDTO`; методы folders CRUD/list. |
| [`src/application/gui/explorer.py`](../../src/application/gui/explorer.py) | Sidebar «Folders» (Listbox), фильтрация таблицы по папке, «New folder», Add File с выбранной папкой. Убрана заглушка Locations. |
| [`src/application/gui/app.py`](../../src/application/gui/app.py) | `_load_folders`, `_on_create_folder`; передача folders в ExplorerView. |

---

### PR-G4 · Client API as default

**Проблема:** default `TELEGRAM_PROVIDER=bot`; Bot API restore даёт 404; refs несовместимы с Client restore.

| Файл | Что изменилось |
|------|----------------|
| [`src/infrastructure/config.py`](../../src/infrastructure/config.py) | Default `TELEGRAM_PROVIDER=client`. |
| [`.env.example`](../../.env.example) | `TELEGRAM_PROVIDER=client`; комментарий про restore. |
| [`docker-compose.yml`](../../docker-compose.yml) | Volume `telegram-session`; workers получают `TELEGRAM_SESSION_PATH=/data/telegram/session.session`; `TELEGRAM_PROVIDER` в runtime env; `telegram-bot-api` перенесён в `profiles: [bot]` (optional). |
| [`scripts/run.sh`](../../scripts/run.sh) | Default provider `client`; валидация api_id/api_hash; подсказка `telegram_client_spike.py`; сообщение при старте GUI. |
| [`docs/TELEGRAM_SETUP.md`](../TELEGRAM_SETUP.md) | Переписан под client-first flow: auth spike, session volume, optional bot profile. |
| [`src/infrastructure/bootstrap.py`](../../src/infrastructure/bootstrap.py) | `build_storage_provider` → `TelegramClientProvider` при `provider=client`. |
| [`src/infrastructure/providers/telegram_client_provider.py`](../../src/infrastructure/providers/telegram_client_provider.py) | Upload пишет refs `client:{chat}:{msg}:{doc}` (без изменений логики, используется как default). |

---

### PR-G5 · Restore UX + Client API tests

**Проблема:** restore без preflight; legacy bot volumes падали с непонятной ошибкой; не хватало тестов на client download path.

#### Use cases

| Файл | Что изменилось |
|------|----------------|
| [`src/use_cases/restore/check_restore_ready.py`](../../src/use_cases/restore/check_restore_ready.py) | **Новый.** Pre-flight: volumes есть → все refs `client:*` → `storage_provider.healthcheck`. |
| [`src/use_cases/restore/restore_session.py`](../../src/use_cases/restore/restore_session.py) | Перед download: reject volumes без `client:` ref → `DomainError.legacy_volumes()`. |
| [`src/use_cases/restore/refs.py`](../../src/use_cases/restore/refs.py) | Без изменений API; используется в preflight и restore для выбора download ref. |
| [`src/use_cases/public/backup_api.py`](../../src/use_cases/public/backup_api.py) | Метод `check_restore_ready(session_id)`. |
| [`src/infrastructure/bootstrap.py`](../../src/infrastructure/bootstrap.py) | Wiring `CheckRestoreReadyUseCase` в BackupApi. |

#### GUI

| Файл | Что изменилось |
|------|----------------|
| [`src/application/backend_receiver.py`](../../src/application/backend_receiver.py) | `RestorePreflightDTO`; метод `check_restore_ready`. |
| [`src/application/gui/app.py`](../../src/application/gui/app.py) | `_on_restore`: preflight до выбора папки; понятные сообщения для legacy volumes; drawer с путями extracted files. |

#### Tests

| Файл | Что изменилось |
|------|----------------|
| [`tests/test_use_cases_restore.py`](../../tests/test_use_cases_restore.py) | Client refs в happy-path; `test_restore_rejects_legacy_bot_api_refs`; `test_check_restore_ready_*`. |
| [`tests/test_telegram_client_provider.py`](../../tests/test_telegram_client_provider.py) | `test_download_file_delegates_to_async`; healthcheck success path. |
| [`tests/test_provider_contract.py`](../../tests/test_provider_contract.py) | `test_restore_ref_for_volume_accepts_client_provider_ref`. |
| [`tests/test_telegram_client_integration.py`](../../tests/test_telegram_client_integration.py) | **Новый.** `@pytest.mark.integration`, opt-in через `TELEGRAM_INTEGRATION=1`. |
| [`tests/test_public_api.py`](../../tests/test_public_api.py) | Fake BackupApi включает `check_restore_ready_uc`. |

---

### PR-G6 · RAM slider placeholder (Settings)

**Проблема:** 7z без лимита RAM; на первом этапе — только UI, без wiring в workers.

| Файл | Что изменилось |
|------|----------------|
| [`src/application/gui/settings.py`](../../src/application/gui/settings.py) | Поле `archive_ram_limit_mb: int = 1024`; `ttk.Scale` 512–4096 MB; label «Archive RAM limit (not applied yet)»; default provider при Save — `client`. |
| [`src/application/gui/__main__.py`](../../src/application/gui/__main__.py) | `_settings_from_config` инициализирует `archive_ram_limit_mb=1024`. |
| [`src/application/gui/app.py`](../../src/application/gui/app.py) | Settings хранятся in-memory (как остальные поля); значение RAM пока не прокидывается в 7z. |

**Не в scope (отдельный PR):** [`src/infrastructure/archive/seven_zip_service.py`](../../src/infrastructure/archive/seven_zip_service.py), env `ARCHIVE_7Z_MMT`, прокидка через workers.

---

## Зависимости между PR

```
G1 (eager backup) → G2 (unlock) → G3 (folders) → G4 (client default) → G5 (restore) → G6 (RAM UI)
```

---

## Quality gate (GUI fixes)

```bash
pytest -m "not integration"
ruff check src tests
mypy src
lint-imports
```

Roman smoke: Create db → Add File (status `queued`) → Start Backup → Restore Session с `TELEGRAM_PROVIDER=client`.

---

## Client API fixes (folder_id, session mount, Test button)

| Область | Изменение |
|---------|-----------|
| **folder_id** | [`merge_source_item_record`](../../src/use_cases/shared/mappers.py) сохраняет `folder_id` при worker updates; миграция [`0005_repair_null_folder_id.sql`](../../src/infrastructure/db/migrations/0005_repair_null_folder_id.sql); fallback в [`explorer.py`](../../src/application/gui/explorer.py) |
| **Session sync** | Bind mount `TELEGRAM_SESSION_DIR` в [`docker-compose.yml`](../../docker-compose.yml); предупреждение в [`run.sh`](../../scripts/run.sh) |
| **Test Client API** | [`TestClientApiUseCase`](../../src/use_cases/telegram/test_client_api.py) + кнопка в [`settings.py`](../../src/application/gui/settings.py); wiring через [`backend_receiver.py`](../../src/application/backend_receiver.py) |
| **Restore messages** | [`check_restore_ready.py`](../../src/use_cases/restore/check_restore_ready.py) — отдельные тексты для incomplete upload vs healthcheck |
| **Docs** | [`CLIENT_API_SETUP.md`](../../docs/CLIENT_API_SETUP.md) — bind mount, Test button, troubleshooting |

Roman smoke: Add File → Start Backup (файл в списке) → spike без docker cp → Test Client API → Restore preflight OK.

---

## Что дальше

- Live Telegram smoke с Client API provider (Roman)
- Wiring RAM limit → [`SevenZipService`](../../src/infrastructure/archive/seven_zip_service.py)
- Deprecate Bot API в compose после стабильного client restore
- P3 integration tests в Docker

Детальные PR-доки UC: [UC-01 … UC-08](README.md).
