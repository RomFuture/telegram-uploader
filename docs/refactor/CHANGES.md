# Restore gate + P0.1 — журнал изменений

> **Дата:** 2026-06-12  
> **План:** Restore gate (P-demo / P0.2 / P1) + P0.1 audit `use_cases` (refs/helpers)  
> **Scope вне итерации:** Restore UX (P1.1), progress bar polling (P1.2), Celery restore orchestration, Bot API deprecation

---

## 2026-06-12 — Rename public entrypoints (naming clarity)

| Было | Стало |
|------|--------|
| `BackupApi` | `GuiEntrypoint` |
| `WorkerApi` | `CeleryEntrypoint` |
| `build_backup_api()` | `wire_gui_entrypoint()` |
| `build_worker_api()` | `wire_celery_entrypoint()` |
| `_worker_api()` in `tasks.py` | `get_celery_entrypoint()` |
| `backup_api.py` | `gui_entrypoint.py` |
| `worker_api.py` | `celery_entrypoint.py` |

**Поведение:** без изменений. `wire_*` собирает use cases + ports; не поднимает Celery-процессы. `BackendReceiver.gui` вместо `.api`.

**Gate:** `pytest -m "not integration"`, `ruff`, `mypy`.

---

## Контекст

До этой итерации restore **уже был собран end-to-end в коде**:

```
GUI (app.py) → BackupApi.restore_session → RestoreSessionUseCase
  → restorable_source_item_ids (client: refs)
  → download_volume_to_dir × N (TelegramClientProvider)
  → SevenZipService.extract → dest_path
```

**Блокер gate:** live smoke «Restore Session → файл в `dest_path`» не был закрыт Roman'ом.  
**Техдолг P0.1:** в `refs.py` были мёртвые fallback'и (`message:{chat}:{id}`, bot `file_id`), не совместимые с `TelegramClientProvider`.

---

## PR-1: Restore gate — верификация download

### Цель

Дать раннюю диагностику download **до** полного GUI restore и подготовить opt-in integration test. Gate owner для GUI restore — **Roman** (ручной smoke).

---

### 1.1 `TestClientApiUseCase` — upload + download + verify

**Файл:** [`src/use_cases/telegram/test_client_api.py`](../../src/use_cases/telegram/test_client_api.py)

**Было:** только `healthcheck` → `upload_file` → success (`stage="upload"`).

**Стало:** полный round-trip:

| Шаг | Stage при ошибке | Действие |
|-----|------------------|----------|
| 1 | `test_file` | Проверка bundled test file на диске |
| 2 | `healthcheck` | `provider.healthcheck(target_chat_id)` |
| 3 | `upload` | `upload_file` → `provider_download_ref` |
| 4 | `download` | `get_file_info(ref)` → `download_file` во temp dir |
| 5 | `verify` | Сравнение `read_bytes()` оригинала и скачанного |
| OK | `verify` | Message: «Upload and download OK…» |

**Детали реализации:**

- Download во **временную директорию** (`tempfile.TemporaryDirectory`); bytes читаются **внутри** `with`, до удаления temp (иначе `FileNotFoundError` при последующем чтении path).
- `TestClientApiResult.provider_ref` заполняется на всех стадиях после upload.
- GUI Settings показывает результат через существующий `_handle_test_client_api` (фоновый thread — без блокировки Tk).

**Файл:** [`src/application/gui/settings.py`](../../src/application/gui/settings.py)

- Текст подсказки на вкладке Client API: «uploads **and downloads** a small test file».

---

### 1.2 Unit-тесты Test Client API

**Файл:** [`tests/test_test_client_api.py`](../../tests/test_test_client_api.py)

| Тест | Что проверяет |
|------|---------------|
| `test_test_client_api_upload_download_roundtrip` | OK, `stage=="verify"`, ref starts with `client:`, 1 download |
| `test_test_client_api_reports_missing_test_file` | `stage=="test_file"` |
| `test_test_client_api_reports_healthcheck_failure` | `stage=="healthcheck"` |
| `test_test_client_api_reports_download_mismatch` | `stage=="verify"` при неверных bytes |

---

### 1.3 `FakeStorageProvider` — client refs + round-trip

**Файл:** [`tests/fakes/ports.py`](../../tests/fakes/ports.py)

**Было:**

- Upload возвращал `provider_download_ref=f"ref-{file_id}"` (не `client:`).
- Download всегда писал `b"volume-bytes"`.

**Стало:**

- Upload: `client:{remote_target}:{message_id}:{document_id}` + сохранение bytes в `_uploads`.
- `get_file_info`: если ref starts with `client:` — возвращает его как `provider_download_ref`.
- `download_file`: bytes из `_uploads` по ref, fallback `b"volume-bytes"` для restore-тестов с заранее заданными refs.

Это выравнивает fake provider с контрактом `TelegramClientProvider` и позволяет тестировать Test Client API без Telethon.

---

### 1.4 Opt-in integration test (live Telethon)

**Файл:** [`tests/test_telegram_client_integration.py`](../../tests/test_telegram_client_integration.py)

**Новый тест:** `test_live_client_upload_download_roundtrip`

- Skip unless `TELEGRAM_INTEGRATION=1`.
- Требует: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, session file, `TELEGRAM_TARGET_CHAT_ID`.
- Использует bundled file через `infrastructure.bootstrap._client_api_test_file()`.
- Вызывает тот же `TestClientApiUseCase.execute`, что и Settings → Test Client API.

**Запуск:**

```bash
TELEGRAM_INTEGRATION=1 .venv/bin/pytest tests/test_telegram_client_integration.py::test_live_client_upload_download_roundtrip -v
```

---

### 1.5 Обновления документации (PR-1)

| Файл | Изменение |
|------|-----------|
| [`docs/PROJECT.md`](../PROJECT.md) §2 | Test Client API: upload + download; restore download 🟡 GUI smoke — Roman |
| [`docs/BACKLOG.md`](../BACKLOG.md) P-demo | `[x]` Test Client API round-trip; `[ ]` GUI Restore Session smoke |
| [`docs/BACKLOG.md`](../BACKLOG.md) P1 | Test Client API ✅; gate уточнён |
| [`docs/TELEGRAM_CLIENT_API_MIGRATION.md`](../TELEGRAM_CLIENT_API_MIGRATION.md) | Restore flow Client API; checklist обновлён |
| [`README.md`](../../README.md) | Test Client API = upload + download |

---

### 1.6 Manual smoke checklist (Roman — gate owner)

**Предусловия:**

- `TELEGRAM_PROVIDER=client`
- Signed session (`~/.config/telegram-uploader/session.session` или путь из Settings)
- `TELEGRAM_TARGET_CHAT_ID` — backup-группа
- Backup после переключения на Client API (`provider_download_ref LIKE 'client:%'`)

**Шаги:**

1. `docker compose up -d`
2. Settings → **Test Client API** → «Upload and download OK»
3. GUI: Unlock → Add File → Start Backup → `completed`
4. (опционально) SQL: `SELECT provider_download_ref FROM archive_volumes WHERE …`
5. **Restore Session** → пустая папка → сравнить файл с оригиналом

**Gate закрыт:** оригинал в `dest_path`, без HTTP 404.

> **Статус на 2026-06-12:** Test Client API round-trip — код готов. GUI Restore Session smoke — **не закрыт** (см. [Фиксы](#фиксы--известные-проблемы-smoke-2026-06-12)).

---

## PR-2: P0.1 — restore/upload ref alignment

### Цель

Единая политика refs в `use_cases/restore`: **только `client:`**. Убрать мёртвый код и дублирование legacy-detection.

---

### 2.1 `refs.py` — v1 policy

**Файл:** [`src/use_cases/restore/refs.py`](../../src/use_cases/restore/refs.py)

#### Константа

```python
CLIENT_RESTORE_REF_PREFIX = "client:"
```

#### Новые функции

| Функция | Назначение |
|---------|------------|
| `is_client_restore_ref(ref)` | `ref.startswith("client:")` |
| `has_legacy_bot_volumes(volumes)` | UPLOADED + ref есть, но не `client:` (Bot API backups) |

#### `restore_ref_for_volume(volume, target_chat_id)`

**Было:** цепочка fallback — `provider_download_ref` → `message:{chat}:{id}` → `external_file_id`.

**Стало:**

- Если `provider_download_ref` starts with `client:` → вернуть ref.
- Если ref есть, но не `client:` → `DomainError.legacy_volumes()`.
- Иначе → `DomainError.missing_external_file_id(volume.id)`.

`target_chat_id` сохранён в сигнатуре для совместимости; не используется (v1).

#### `is_volume_restorable`

**Было:** try/except через `restore_ref_for_volume` + check prefix.

**Стало:** `UPLOADED` + `provider_download_ref` is not None + `is_client_restore_ref(ref)`.

#### Удалено (использовались только в тестах)

- `restore_download_ref(volume)`
- `external_file_id_for_restore(volume)`

#### Без изменений по смыслу

- `restorable_source_item_ids` — все parts item'а должны быть restorable.

---

### 2.2 Потребители refs

#### [`restore_session.py`](../../src/use_cases/restore/restore_session.py)

- Legacy detection → `has_legacy_bot_volumes(volumes)` вместо inline `any(...)`.
- **Удалён** redundant loop: проверка каждого volume ref перед download (теперь в `restore_ref_for_volume` / `restorable_source_item_ids`).

#### [`check_restore_ready.py`](../../src/use_cases/restore/check_restore_ready.py)

- `has_legacy_bot_volumes(volumes)` вместо дублированного inline.
- Убран неиспользуемый `import domain`.

#### [`download_volume.py`](../../src/use_cases/restore/download_volume.py)

- Без изменений; по-прежнему единственная точка provider download для restore UC.
- Вызывает `restore_ref_for_volume` → при non-`client:` ref бросит `legacy_volumes`.

---

### 2.3 Upload side — комментарий контракта

**Файл:** [`src/use_cases/backup/process_upload_volume.py`](../../src/use_cases/backup/process_upload_volume.py)

После `upload_file` добавлен комментарий:

```python
# Client API stores provider_download_ref as client:{chat}:{msg}:{doc}.
# Restore accepts only client: refs; legacy Bot API backups require re-upload.
```

Guard/error на non-`client:` ref **не добавлен** — Bot API provider (`TELEGRAM_PROVIDER=bot`) всё ещё допустим для legacy upload.

---

### 2.4 Worker restore hook — docstring

**Файл:** [`src/use_cases/restore/process_restore_volume.py`](../../src/use_cases/restore/process_restore_volume.py)

Docstring класса:

> Download one archive volume to staging (Celery worker hook).  
> GUI restore uses RestoreSessionUseCase in-process; this UC is not on that path.

`enqueue_restore` по-прежнему **не вызывается** из use cases — осознанно вне scope.

---

### 2.5 Тесты (PR-2)

#### [`tests/test_restore_refs.py`](../../tests/test_restore_refs.py) — переписан

| Тест | Покрытие |
|------|----------|
| `test_is_client_restore_ref` | prefix check |
| `test_restore_ref_for_volume_returns_client_ref` | happy path |
| `test_restore_ref_for_volume_raises_for_legacy_bot_ref` | `legacy_volumes` |
| `test_restore_ref_for_volume_raises_when_no_client_ref` | `missing_external_file_id` |
| `test_is_volume_restorable_requires_client_ref` | client / legacy / empty ref |
| `test_has_legacy_bot_volumes` | helper |
| `test_restorable_source_item_ids_requires_all_parts_client` | multi-part: 2 OK parts + 1 legacy → empty set |

**Удалены** тесты fallback `message:` и `bot-file-id` как «рабочих» restore paths.

#### [`tests/test_provider_contract.py`](../../tests/test_provider_contract.py)

- `test_restore_ref_for_volume_accepts_client_provider_ref` — + `is_client_restore_ref`, `is_volume_restorable`.
- **Новый:** `test_client_upload_ref_matches_restore_policy` — `build_client_download_ref` ↔ parse.

---

### 2.6 Документация (PR-2)

| Файл | Изменение |
|------|-----------|
| [`docs/BACKLOG.md`](../BACKLOG.md) P0.1 | `[x]` Выровнять restore/upload ref helpers |
| [`docs/TELEGRAM_CLIENT_API_MIGRATION.md`](../TELEGRAM_CLIENT_API_MIGRATION.md) | v1 policy; нет `message:` fallback |

---

## Сводка изменённых файлов

### Use cases / application

| Файл | PR | Суть |
|------|----|------|
| `src/use_cases/telegram/test_client_api.py` | 1 | upload → download → verify |
| `src/use_cases/restore/refs.py` | 2 | `client:` only, helpers |
| `src/use_cases/restore/restore_session.py` | 2 | `has_legacy_bot_volumes`, убран redundant loop |
| `src/use_cases/restore/check_restore_ready.py` | 2 | `has_legacy_bot_volumes` |
| `src/use_cases/restore/process_restore_volume.py` | 2 | docstring |
| `src/use_cases/backup/process_upload_volume.py` | 2 | comment ref policy |
| `src/application/gui/settings.py` | 1 | copy Test Client API |

### Tests

| Файл | PR |
|------|----|
| `tests/fakes/ports.py` | 1 |
| `tests/test_test_client_api.py` | 1 |
| `tests/test_telegram_client_integration.py` | 1 |
| `tests/test_restore_refs.py` | 2 |
| `tests/test_provider_contract.py` | 2 |

### Docs

| Файл | PR |
|------|----|
| `docs/PROJECT.md` | 1 |
| `docs/BACKLOG.md` | 1, 2 |
| `docs/TELEGRAM_CLIENT_API_MIGRATION.md` | 1, 2 |
| `README.md` | 1 |

---

## Gates — статус после итерации

| Gate | Статус |
|------|--------|
| `pytest -m "not integration"` | ✅ 130 passed |
| `ruff` + `mypy src` | ✅ |
| Test Client API upload + download (Settings) | ✅ код + unit tests |
| `TELEGRAM_INTEGRATION=1` live round-trip | ✅ opt-in test добавлен |
| **GUI Restore Session smoke** | 🟡 fix landed — Roman smoke in `~/Restored/` |
| P0.1 ref helpers | ✅ |
| P0.1 full use_cases audit | ❌ остаётся в BACKLOG |

---

## Фиксы / известные проблемы (smoke 2026-06-12)

Зафиксировано при ручном прогоне Roman после PR-1/PR-2. **Требуют отдельных PR.**

---

### FIX-1 · Progress bar «зависает» при backup

**Симптом (скрин):**

- После **Start Backup** drawer показывает «Enqueued 1 item(s) for processing» / «Backup started».
- Progress bar — `indeterminate`, визуально **не двигается** или кажется мёртвым.
- Workers при этом могут работать в фоне (Celery archive/upload).

**Вероятная причина (не Client API напрямую):**

- [`ProgressDrawer`](../../src/application/gui/drawer.py) — только `mode="indeterminate"`.
- [`app.py` `_on_start_backup`](../../src/application/gui/app.py) сразу вызывает `show_result` после enqueue — **нет polling** `get_session_progress`.
- Известный пункт BACKLOG **P1.2 Progress bar** — не реализован в этой итерации.

**Связь с Client API:**

- Upload идёт в **Celery worker** (`celery-worker-upload`), не в GUI thread.
- «Зависание» loader'а — скорее **UX/отсутствие live progress**, чем блок Telethon в GUI при backup.

**Workaround для smoke:**

- Нажать **Refresh** периодически — таблица обновит status (`archiving` → `uploading` → `completed`).
- Смотреть логи: `docker compose logs -f celery-worker-upload`.

**План fix (P1.2):**

- Timer или polling `get_session_progress` пока есть items in progress.
- Determinate bar или текст «N/M completed, current: uploading …».
- Не скрывать bar сразу после enqueue.

---

### FIX-2 · Restore failed: `database is locked` — **переоценено**

**Статус:** не считаем основным блокером restore gate; гипотеза про Celery worker **не подтверждена**.

**Симptom (первый скрин, 2026-06-12):**

- **Restore Session** → «Restore failed: **database is locked**».
- Операция висела заметное время, затем ошибка.

**Уточнение (Roman):**

- В момент ошибки были открыты **два окна Telegram Uploader** одновременно.
- Оба процесса GUI используют один и тот же Telethon SQLite `session.session` (`~/.config/telegram-uploader/session.session`).
- **Это ожидаемо:** SQLite не допускает concurrent write — второй GUI → `database is locked`. Логично, не баг архитектуры backup/upload.

**Первоначальная гипотеза (снята как primary):**

- Конфликт GUI + `celery-worker-upload` за тот же session file через Docker volume.
- Возможно в отдельных сценариях, но **не воспроизведено** как корневая причина текущего smoke.

**Workaround:**

- Не запускать **два GUI** одновременно.
- Один экземпляр приложения на session file.

**Нужно ли чинить в коде:**

- Nice to have: detect second instance / file lock на session при старте GUI.
- Не блокирует PR restore gate, если restore воспроизводится из **одного** окна.

---

### FIX-3 · Restore blocks GUI (related)

**Симптом:** indeterminate bar при restore не анимируется; окно не отвечает.

**Причина:** `_on_restore` → `request_restore` синхронно в main thread (Telethon + 7z).

**План fix:** background thread (отдельный PR, P1.2 / restore UX). Не блокирует gate, если restore functionally OK.

---

### FIX-4 · Restore failed: 7z extract `Permission denied` (errno=13) — **нужен debug**

**Статус:** **open · primary blocker** для GUI Restore Session smoke. Корневая причина **не установлена** — требуется дебаг.

**Симptom (скрин, 2026-06-12, одно окно GUI):**

```
Restore failed: 7z extract failed: ERROR: Cannot open output file :
errno=13 : Permission denied :
/opt/telegram-uploader/src/testtest/2026-04-05 11-05-50.mkv
```

**Что это значит:**

- Download с Telegram, судя по ошибке, **дошёл до extract** (иначе упали бы раньше на Telethon).
- Падает **7z** при записи файла в `dest_path`, не Client API session DB.

**Кontext из UI:**

- Restore destination: `/opt/telegram-uploader/src/testtest` (папка внутри **deb install tree** / packaged path).
- Файл в таблице перед restore: `IMPLEMENTATION_GUIDE.md` (status `backed up`); extract target в ошибке — **`2026-04-05 11-05-50.mkv`** (другой item / предыдущий backup в session).
- Пользователь ранее видел warning «destination not empty» — в папке уже могли быть файлы.

**Гипотезы для дебага (не проверены):**

| # | Гипотеза | Как проверить |
|---|----------|---------------|
| 1 | `dest_path` под `/opt/telegram-uploader/` — **root-owned** после `.deb` install; GUI user не может писать | `ls -la /opt/telegram-uploader/src/testtest`, restore в `~/Restored/` |
| 2 | Файл **уже существует** в dest с правами root / read-only | `ls -la` конкретного `.mkv`; restore в пустую домашнюю папку |
| 3 | 7z subprocess / `SevenZipService` — cwd или umask | breakpoint / log в `seven_zip_service.extract`, кто spawn'ит 7z |
| 4 | Session restore **всех** restorable items — extract перезаписывает чужой файл | сколько items `completed` в session; один или несколько extract в один dest |
| 5 | Имя файла с пробелами / путь — edge case 7z args | сравнить с extract в `/tmp/restore-test/` |

**Workaround для следующего smoke:**

1. **Одно** окно GUI.
2. Restore destination: **`~/Restored-test/`** (или `/tmp/...`) — **не** под `/opt/telegram-uploader/`.
3. **Пустая** папка.
4. Session с **одним** backed-up файлом (меньше путаницы в логах).

**План fix (после дебага):**

- Понятная ошибка в GUI: «Cannot write to destination — choose a folder you own».
- Default dest вне install root (P1.1).
- Preflight: проверка writability dest (`os.access(W_OK)`) до download.
- Записать root cause в этот файл после Roman debug session.

**Задача:** Roman + debugger — один прогон restore в `~/Restored/` с `pytest`/логами 7z; обновить FIX-4 с findings.

**Fix PR (2026-06-12) — implemented, smoke TBD:**

| Change | File(s) |
|--------|---------|
| Preflight writability: probe file + `os.access` before download | `use_cases/restore/dest_path.py`, `restore_session.py` |
| `DomainError.restore_destination_not_writable` | `domain/errors.py` |
| GUI: default folder picker `~/Restored/`, warn `/opt/telegram-uploader/` | `application/gui/restore_dest.py`, `app.py` |
| GUI: warn read-only existing files in dest | `app.py` |
| Restore in **background thread** (FIX-3 partial) | `app.py` |
| Clearer 7z permission denied message | `seven_zip_service.py` |
| `format_user_error` passes through domain/permission messages | `application/gui/errors.py` |

**Roman smoke after fix:** одно окно GUI → Restore → `~/Restored/` (empty) → file matches original.

---

## Unified logging — file in project root (2026-06-12)

**Scope:** P0.2 structured logging (minimal v1) + PROJECT.md §9 rule for backend CHANGES.md.

### PROJECT.md rule (Part A)

§9 **Документирование backend-изменений:** PR в `domain/`, `use_cases/`, `infrastructure/` → секция в этот файл.

### Implementation (Part B)

| Component | Change |
|-----------|--------|
| [`src/observation/logging_setup.py`](../../src/observation/logging_setup.py) | `setup_logging()` — idempotent FileHandler + StreamHandler |
| [`src/infrastructure/config.py`](../../src/infrastructure/config.py) | `log_file_path`; `APP_LOG_FILE`, `INSTALL_ROOT/telegram-uploader.log` |
| [`src/application/gui/__main__.py`](../../src/application/gui/__main__.py) | setup on GUI start |
| [`src/infrastructure/bootstrap.py`](../../src/infrastructure/bootstrap.py) | replaces inline `basicConfig` |
| [`src/infrastructure/worker/celery_app.py`](../../src/infrastructure/worker/celery_app.py) | `worker_process_init` → setup |
| [`docker-compose.yml`](../../docker-compose.yml) | `APP_LOG_FILE=/data/telegram-uploader.log`; rw bind mount |
| [`scripts/run.sh`](../../scripts/run.sh) | `touch telegram-uploader.log`; echo log path |
| [`.gitignore`](../../.gitignore) | `telegram-uploader.log` |

**Default path:** `{INSTALL_ROOT}/telegram-uploader.log` — dev repo root via `./scripts/run.sh`.

**Env:** `APP_LOG_FILE` (override), `APP_LOG_LEVEL` (existing).

**Concurrency:** multiple processes append one file; lines may interleave (documented, OK for v1).

**Not in v1:** `session_id` correlation, log rotation, `logs/sessions/` tree.

**Gate:** `tail -f telegram-uploader.log` shows GUI + worker lines after backup smoke.

---

## Restore progress logging + folder-scoped restore (2026-06-12)

**Scope:** heartbeat/progress logs during long Telegram downloads; restore respects sidebar folder; **All files** = aggregate view of whole session.

### Problem (before)

| Issue | Symptom |
|-------|---------|
| Silent Telethon download | 5–6 min gap in `telegram-uploader.log` during large file download |
| Restore ignored folder | Restore from **TEST** downloaded every backed-up file in session |
| **All files** sidebar filter | Hid files assigned to other folders instead of showing full session |

### Folder model (after)

- **`All files`** — virtual aggregate: table lists **every** file in the session (move to another folder assigns `folder_id`, file stays visible here).
- **Named folder (e.g. TEST)** — table lists only items with `folder_id == TEST`.
- **Restore** follows sidebar selection: **All files** → whole session; named folder → that folder only.
- **Move to folder** — unchanged in DB: updates `source_items.folder_id` (logical “copy into folder”, not delete from All files view).

### Files changed

| File | Change |
|------|--------|
| [`src/use_cases/restore/download_progress.py`](../../src/use_cases/restore/download_progress.py) | **New.** `make_download_progress_callback()` — 10% milestones + 30s heartbeat (`use_cases.restore.download` logger) |
| [`src/use_cases/restore/scope.py`](../../src/use_cases/restore/scope.py) | **New.** `restorable_source_item_ids_for_folder()` — All files vs folder filter |
| [`src/use_cases/shared/folders.py`](../../src/use_cases/shared/folders.py) | `is_default_folder_name()` |
| [`src/use_cases/restore/restore_session.py`](../../src/use_cases/restore/restore_session.py) | `folder_id` param; scope filter; start/part/extract/complete INFO logs; progress callback per volume |
| [`src/use_cases/restore/download_volume.py`](../../src/use_cases/restore/download_volume.py) | Optional `on_progress` → provider |
| [`src/use_cases/restore/check_restore_ready.py`](../../src/use_cases/restore/check_restore_ready.py) | Preflight scoped to folder; message names scope |
| [`src/use_cases/shared/ports/storage_provider.py`](../../src/use_cases/shared/ports/storage_provider.py) | `download_file(..., on_progress=)` optional kwarg |
| [`src/infrastructure/providers/telegram_client_provider.py`](../../src/infrastructure/providers/telegram_client_provider.py) | Telethon `progress_callback=on_progress` |
| [`src/infrastructure/providers/telegram_provider.py`](../../src/infrastructure/providers/telegram_provider.py) | Bot provider: pass-through `on_progress` at start/end |
| [`src/domain/errors.py`](../../src/domain/errors.py) | `no_restorable_backups_in_folder` |
| [`src/use_cases/public/commands.py`](../../src/use_cases/public/commands.py) | `RestoreSessionCommand.folder_id` |
| [`src/use_cases/public/backup_api.py`](../../src/use_cases/public/backup_api.py) | Pass `folder_id` to restore + preflight |
| [`src/infrastructure/bootstrap.py`](../../src/infrastructure/bootstrap.py) | Wire `source_items` + `folders` into restore use cases |
| [`src/application/backend_receiver.py`](../../src/application/backend_receiver.py) | `folder_id` on restore/preflight |
| [`src/application/gui/app.py`](../../src/application/gui/app.py) | Pass selected sidebar folder to restore |
| [`src/application/gui/explorer.py`](../../src/application/gui/explorer.py) | All files shows all items; named folders filter strictly |
| [`tests/test_restore_scope_and_progress.py`](../../tests/test_restore_scope_and_progress.py) | **New.** scope + progress tests |

### Log examples (during restore)

```
INFO [use_cases.restore] restore started session_id=… dest=… scope=folder 'TEST' items=1 volumes=2
INFO [use_cases.restore] download starting big.mkv.7z.001 item 1/1 part 1/2
INFO [use_cases.restore.download] download progress big.mkv.7z.001 10% (… bytes) elapsed=32s
INFO [use_cases.restore.download] download in progress big.mkv.7z.001 …/… bytes elapsed=62s (heartbeat)
INFO [use_cases.restore] extract complete item 1/1 -> /home/…/Restored/big.mkv
INFO [use_cases.restore] restore complete session_id=… scope=folder 'TEST' extracted=1 path(s)
```

Telethon library lines (`telethon.network…`) still appear; app logs fill the long gaps.

### Gate / smoke

1. **All files** selected → table shows all session files → Restore → all restorable files land in dest.
2. **TEST** selected → only TEST files in table → Restore → only TEST files (not IMPLEMENTATION_GUIDE from other folder).
3. `tail -f telegram-uploader.log` during 1 GB restore → progress/heartbeat lines every ~30s or 10%, not multi-minute silence.

---

## Связанные документы

- [PROJECT.md §11 — известные баги](../PROJECT.md#11-известные-баги-и-долг)
- [BACKLOG.md P1.2 — progress bar](../BACKLOG.md)
- [TELEGRAM_CLIENT_API_MIGRATION.md](../TELEGRAM_CLIENT_API_MIGRATION.md)

---

*При закрытии FIX-* — переносить в PROJECT.md §11 как Resolved и удалять из этого раздела.*
