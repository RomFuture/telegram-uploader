# Debugger — backup pipeline (use_cases only)

> Пошаговые breakpoint'ы для PyCharm. Только `src/use_cases/`.  
> Канон слоя: [MANUAL.md](MANUAL.md) · архитектура: [docs/PROJECT.md](../../docs/PROJECT.md).

## Подготовка

```bash
docker compose up -d
```

**Run Config:** module `application.gui`, `PYTHONPATH=src`.

**Два процесса:**

| Процесс | Остановки | Как |
|---------|-----------|-----|
| GUI | 0–28, 87–91 | Run `application.gui` |
| Celery workers | 32–86, 92–97 | Attach к `celery-worker-archive-1`, `celery-worker-upload`, `celery-worker-cleanup` |

На **port** (`task_queue`, `archive_service`, `storage_provider`): **F7** один раз → **Shift+F8**. Не залипай в infra.

**Клавиши:** F8 — следующая строка в UC · F7 — в domain/gates/idempotency · Shift+F8 — вылет из infra.

---

## Фаза 0 — Session (GUI, опционально)

| # | Файл | Стр | GUI | Смотри |
|---|------|-----|-----|--------|
| 0 | `public/gui_entrypoint.py` | 89 | Unlock | `command.profile_name` |
| 1 | `session/unlock_session.py` | 17 | | `find_by_profile_name` |
| 2 | `session/unlock_session.py` | 20 | | `compare_digest` |
| 3 | `session/unlock_session.py` | 22 | | return Session |
| 4 | `public/gui_entrypoint.py` | 93 | New database | вход |
| 5 | `session/create.py` | 58 | | `domain.create_session` (CreateDatabase) |
| 6 | `session/create.py` | 60 | | `folders.add` — All files |

---

## Фаза 1 — Папки (GUI)

| # | Файл | Стр | GUI | Смотри |
|---|------|-----|-----|--------|
| 7 | `public/gui_entrypoint.py` | 104 | Create folder | `command.name` |
| 8 | `session/create.py` | 88 | | `BackupFolderRecord` перед add |
| 9 | `public/gui_entrypoint.py` | 100 | — | list_folders |

---

## Фаза 2 — Add File (GUI)

| # | Файл | Стр | Смотри |
|---|------|-----|--------|
| 10 | `public/gui_entrypoint.py` | 107 | вход enqueue_file |
| 11 | `public/gui_entrypoint.py` | 108 | F7 → enqueue UC |
| 12 | `backup/enqueue_source_item.py` | 19 | execute вход |
| 13 | `backup/enqueue_source_item.py` | 27 | проверка folder_id |
| 14 | `backup/enqueue_source_item.py` | 33 | `domain.create_source_item` |
| 15 | `backup/enqueue_source_item.py` | 34 | `source_items.add` — status **queued** |
| 16 | `backup/enqueue_source_item.py` | 35 | return item |
| 17 | `public/gui_entrypoint.py` | 114 | `QueueItemResult` |

После #17 Celery **не** вызывался.

---

## Фаза 3 — Start Backup (GUI)

| # | Файл | Стр | Смотри |
|---|------|-----|--------|
| 18 | `public/gui_entrypoint.py` | 120 | вход start_backup |
| 19 | `public/gui_entrypoint.py` | 121 | F7 |
| 20 | `backup/start_backup_pipeline.py` | 31 | `sessions.require` |
| 21 | `backup/start_backup_pipeline.py` | 32 | session `created`? |
| 22 | `backup/start_backup_pipeline.py` | 33 | → RUNNING |
| 23 | `backup/start_backup_pipeline.py` | 36 | else → gate |
| 24 | `backup/gates.py` | 9 | `require_session_running` |
| 25 | `backup/start_backup_pipeline.py` | 39 | цикл items |
| 26 | `backup/start_backup_pipeline.py` | 40 | status == queued |
| 27 | `backup/start_backup_pipeline.py` | 42 | **`enqueue_archive`** |
| 28 | `backup/start_backup_pipeline.py` | 47 | return enqueued |

### Resume (только retry; первый backup пропускает)

| # | Файл | Стр | Когда |
|---|------|-----|-------|
| 29 | `backup/start_backup_pipeline.py` | 56 | resume stuck archiving |
| 30 | `backup/start_backup_pipeline.py` | 87 | resume upload |
| 31 | `backup/idempotency.py` | 85 | `decide_upload_on_retry` |

---

## Фаза 4 — Archive worker

Attach к **celery-worker-archive-1**. Backup уже нажат (или задача в Redis).

| # | Файл | Стр | Смотри |
|---|------|-----|--------|
| 32 | `public/celery_entrypoint.py` | 28 | process_archive |
| 33 | `public/celery_entrypoint.py` | 29 | F7 |
| 34 | `backup/process_archive_volume.py` | 31 | execute вход |
| 35 | `backup/process_archive_volume.py` | 32 | `source_items.require` |
| 36 | `backup/process_archive_volume.py` | 33 | `decide_archive_on_retry` |
| 37 | `backup/idempotency.py` | 40 | → RUN (queued) |
| 38 | `backup/idempotency.py` | 42 | → RESUME (retry) |
| 39 | `backup/process_archive_volume.py` | 35 | SKIP branch |
| 40 | `backup/process_archive_volume.py` | 46 | `require_item_archivable` |
| 41 | `backup/gates.py` | 19 | queued OK |
| 42 | `backup/gates.py` | 21 | archiving без volumes |
| 43 | `backup/process_archive_volume.py` | 50 | файл виден worker |
| 44 | `backup/process_archive_volume.py` | 56 | session + encryption_key |
| 45 | `backup/process_archive_volume.py` | 58 | → ARCHIVING |
| 46 | `backup/process_archive_volume.py` | 61 | `archive_service.archive` |
| 47 | `backup/process_archive_volume.py` | 69 | цикл volumes |
| 48 | `backup/process_archive_volume.py` | 70 | `create_archive_volume` |
| 49 | `backup/process_archive_volume.py` | 76 | `archive_volumes.add` |
| 50 | `backup/process_archive_volume.py` | 77 | **`enqueue_upload`** |
| 51 | `backup/process_archive_volume.py` | 79 | → UPLOADING |
| 52 | `backup/process_archive_volume.py` | 82 | `_update_source_item` |

### Archive resume path

| # | Файл | Стр |
|---|------|-----|
| 53 | `backup/process_archive_volume.py` | 39 |
| 54 | `backup/process_archive_volume.py` | 42 |
| 55 | `backup/process_archive_volume.py` | 96 |
| 56 | `backup/process_archive_volume.py` | 101 |

---

## Фаза 5 — Upload worker

Attach к **celery-worker-upload**. Точки **57–74** — на **каждый** том.

| # | Файл | Стр | Смотри |
|---|------|-----|--------|
| 57 | `public/celery_entrypoint.py` | 31 | process_upload |
| 58 | `public/celery_entrypoint.py` | 32 | F7 |
| 59 | `backup/process_upload_volume.py` | 25 | execute |
| 60 | `backup/process_upload_volume.py` | 26 | require volume |
| 61 | `backup/process_upload_volume.py` | 27 | `decide_upload_on_retry` |
| 62 | `backup/idempotency.py` | 55 | SKIP uploaded |
| 63 | `backup/idempotency.py` | 57 | RUN created |
| 64 | `backup/idempotency.py` | 59 | CONTINUE uploading |
| 65 | `backup/process_upload_volume.py` | 29 | SKIP → cleanup |
| 66 | `backup/process_upload_volume.py` | 36 | `require_volume_created` |
| 67 | `backup/gates.py` | 28 | volume CREATED |
| 68 | `backup/process_upload_volume.py` | 37 | → UPLOADING |
| 69 | `backup/process_upload_volume.py` | 44 | **`storage_provider.upload_file`** |
| 70 | `backup/process_upload_volume.py` | 52 | mark uploaded |
| 71 | `backup/process_upload_volume.py` | 58 | ref **client:** |
| 72 | `backup/process_upload_volume.py` | 59 | **`enqueue_cleanup`** |
| 73 | `backup/process_upload_volume.py` | 61 | require item |
| 74 | `backup/process_upload_volume.py` | 63 | item → CLEANUP |

---

## Фаза 6 — Cleanup worker

| # | Файл | Стр | Смотри |
|---|------|-----|--------|
| 75 | `public/celery_entrypoint.py` | 34 | process_cleanup |
| 76 | `public/celery_entrypoint.py` | 35 | F7 |
| 77 | `backup/cleanup_volume.py` | 16 | execute |
| 78 | `backup/cleanup_volume.py` | 17 | require volume |
| 79 | `backup/cleanup_volume.py` | 18 | require item |
| 80 | `backup/cleanup_volume.py` | 20 | `decide_cleanup_on_retry` |
| 81 | `backup/idempotency.py` | 72 | SKIP if completed |
| 82 | `backup/cleanup_volume.py` | 23 | unlink temp |
| 83 | `backup/cleanup_volume.py` | 26 | all cleaned? |
| 84 | `backup/cleanup_volume.py` | 28 | item CLEANUP? |
| 85 | `backup/cleanup_volume.py` | 29 | → **COMPLETED** |
| 86 | `backup/cleanup_volume.py` | 31 | update item |

---

## Фаза 7 — Refresh Progress (GUI)

| # | Файл | Стр | Смотри |
|---|------|-----|--------|
| 87 | `public/gui_entrypoint.py` | 123 | get_queue_snapshot |
| 88 | `public/gui_entrypoint.py` | 124 | F7 |
| 89 | `session/get_session_queue_snapshot.py` | 61 | execute |
| 90 | `session/get_session_queue_snapshot.py` | 71 | **display_name** |
| 91 | `session/get_session_queue_snapshot.py` | 72 | status |

---

## Фаза 8 — Failure (worker, после exhausted retries)

| # | Файл | Стр |
|---|------|-----|
| 92 | `public/celery_entrypoint.py` | 40 |
| 93 | `backup/report_failure.py` | 32 |
| 94 | `public/celery_entrypoint.py` | 43 |
| 95 | `backup/report_failure.py` | 47 |
| 96 | `backup/report_failure.py` | 54 |
| 97 | `public/celery_entrypoint.py` | 46 |

---

## Фаза 9 — loading (F7 из `.require()`)

| # | Файл | Стр |
|---|------|-----|
| 98 | `shared/repositories/loading.py` | 21 |
| 99 | `shared/repositories/loading.py` | 30 |
| 100 | `shared/repositories/loading.py` | 39 |

---

## Быстрый первый проход (8 точек)

| # | Файл | Стр | Зачем |
|---|------|-----|-------|
| 15 | `backup/enqueue_source_item.py` | 34 | queued, без worker |
| 27 | `backup/start_backup_pipeline.py` | 42 | только enqueue_archive |
| 50 | `backup/process_archive_volume.py` | 77 | upload ставит archive |
| 69 | `backup/process_upload_volume.py` | 44 | отправка в Telegram |
| 71 | `backup/process_upload_volume.py` | 58 | client: ref |
| 85 | `backup/cleanup_volume.py` | 29 | completed |
| 90 | `session/get_session_queue_snapshot.py` | 71 | display_name в UI |

---

## Порядок прохода

```
0–9    Session / folder (опционально)
10–17  Add File
18–28  Backup
       [attach archive worker]
32–52  Archive
57–74  Upload × N томов
       [attach cleanup worker]
75–86  Cleanup
87–91  Refresh Progress
```

---

*Пути относительно `src/use_cases/`.*
