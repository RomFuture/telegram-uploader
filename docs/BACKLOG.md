# Backlog — not implemented

Единый список **нереализованного**. Реализованное сюда не пишем.

---

## Правила работы (обязательные)

Это не задачи на потом — **режим**, в котором идёт вся доработка проекта.

### Цели обучения

1. **Архитектура** — понять и выровнять onion-слои; каждый слой пройти вместе, осознанно.
2. **Оптимизация кода** — упростить, убрать дубли и костыли, не ломая границы слоёв.
3. **Фичи** — цикл **внедрил → проверил → только потом дальше**; без «написал и забыл».

### Порядок чистки кода

**Снизу вверх по onion** (не наоборот):

```
domain  ✅  →  use_cases  →  infrastructure  →  application
```

**`domain` закрыт (2026-06):** три файла (`models`, `actions`, `errors`), без пайплайна и persistence. Дальше — только если use_cases вскроет дыру в ядре. GUI — на этапе `application`, после стабильного низа.

Каждый слой — **отдельная сессия**: смотрим вместе, правим, прогоняем тесты, **ты сам** гоняешь приложение.

### Ручная проверка (напоминание себе)

> **После каждой заметной правки:** остановись, запусти приложение руками, пройди сценарий в GUI или worker-логах. Автотесты — необходимы, но **не заменяют** твой smoke.

Минимальный smoke:

```bash
docker compose up -d
PYTHONPATH=src .venv/bin/python -m application.gui
# Start Session → Add File → Start Backup → Refresh Progress
docker compose logs -f celery-worker-archive-1
```

**Ассистенту:** в конце каждой сессии с кодом напоминать пользователю сделать этот ручной прогон, если он сам не написал, что проверил.

### Gate и smoke — **обязательный этап** (не опционально)

> Полные определения и цикл → **[PROJECT.md §10](PROJECT.md#10-режим-работы)**

| Термин | Суть |
|--------|------|
| **Gate** | Критерий «можно идти дальше» (не «поработал час»). Пример: restore download без 404. |
| **Smoke** | 5–15 мин **руками**: GUI или round-trip файла. `pytest` alone **не считается**. |

**Без закрытого gate следующий слой / пункт бэклога не начинаем.**

**Roman vs ИИ:** smoke и закрытие gate — **только Roman руками**; ИИ пишет код и тесты, но не засчитывает «готово». Таблица → [PROJECT.md §10](PROJECT.md#10-режим-работы).

### Как закрывать пункты бэклога

1. Правка в одном слое *(ИИ может помочь с кодом · Roman читает diff)*  
2. **Roman** гоняет `pytest` + `ruff` + `mypy` у себя  
3. **Roman** делает **ручной smoke** (обязательно · ИИ не заменяет)  
4. **Roman** подтверждает gate → пункт **удаляется** отсюда *(не ИИ)*  

Большие планы — отдельные `docs/*_MIGRATION.md`; в бэклоге только ссылка + gate.

---

## P-demo — v1 «показать другу» (Roman 09.06)

**Цель:** на встрече с другом показать, что **первая версия уже есть** — не финал, но клонируется и запускается. Приоритет **над** косметикой GUI и P4 domain.

- [x] **`scripts/run.sh`** — one-command demo: compose + GUI
- [x] **`.github/workflows/ci.yml`** — ruff, mypy, pytest, lint-imports on push/PR
- [x] **README** + **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)** — setup from scratch (bot, API keys, group, `./scripts/run.sh`, smoke backup)
- [ ] **Onboarding automation** — GUI wizard: API id/hash, bot, group id, `.env`; позже Client API login ([README](../README.md#onboarding-automation-planned))
- [ ] **Client API setup guide (beginner-friendly)** — переписать [CLIENT_API_SETUP.md](CLIENT_API_SETUP.md) «нативно»: без CLI-жаргона, пошагово «куда нажать / что скопировать», скриншоты my.telegram.org и Telegram, что такое session file простыми словами, отдельный блок «если ничего не понятно»; целевая аудитория — пользователь без опыта в терминале. **Gate:** человек без dev-навыков проходит auth + первый backup по одному документу (Roman проверяет на «чистом» знакомом).
- [x] Backup happy path (Client API default)
- [x] Test Client API upload + download round-trip (Settings)
- [ ] **GUI Restore Session smoke** — backup completed item → Restore → файл в `dest_path` (Roman)

**Gate P-demo:** друг (или ты на чистой машине) повторяет **одну команду** после clone; CI на `main` зелёный; smoke backup пройден.

**Сегодня (09.06):** двигаться к P-demo параллельно с Telegram driver — вечерний блок: CI + run script + продолжение драйвера.

---

## Стек vs CV (`~/еку.txt`)

Сверка **твоих навыков** с тем, что реально есть в репозитории. Цель — не «впихнуть всё подряд», а **осознанно** добавить или углубить технологии по ходу P0–P3.

Легенда: ✅ есть в проекте · 🟡 частично / стоит пройти глубже · ❌ ещё нет · ➖ не нужно в v1 (desktop backup)

### Уже задействовано (закрепить на практике)

| Технология | Где в проекте |
|------------|----------------|
| Python, OOP, design principles | onion: `domain` → `use_cases` → `infrastructure` → `application` |
| SQLAlchemy 2.x | `infrastructure/db/orm.py`, `sqlalchemy_repositories.py` |
| PostgreSQL, SQL, индексы | `docker-compose.yml`, `migrations/*.sql`, FK + `ix_*` |
| Транзакции commit/rollback | `infrastructure/db/engine.py` → `db_session_scope` |
| Celery + Redis (broker/backend) | `celery_app.py`, workers archive/upload/cleanup/restore |
| Docker, Docker Compose | `Dockerfile`, `docker-compose.yml`, p7zip в образе |
| pytest | `tests/` (~60 unit), fakes, `@pytest.mark.integration` |
| mypy (strict) | `pyproject.toml` |
| ruff (вместо Black/Flake8/isort) | `pyproject.toml`, линт в dev |
| Git, Linux/bash | ежедневный workflow, compose, smoke-команды |

### Частично — просмотреть и углубить

- [ ] **SQLAlchemy** — relationships, `select`/`merge`, N+1 при restore (несколько volumes); паттерн repository vs session scope
- [ ] **PostgreSQL** — изоляция, idempotency Celery retries, индексы под реальные запросы (`status`, `session_id`)
- [ ] **Schema migrations** — сейчас raw SQL + `migrate.py`, не Alembic; решить: оставить SQL или ввести Alembic для zero-downtime (из CV)
- [ ] **pytest** — больше fixtures, `@pytest.mark.parametrize`, integration в Docker (P3)
- [ ] **TDD / code review** — писать тест до/вместе с use case при P0.1; границы слоёв уже в `test_layer_boundaries.py`
- [ ] **Микросервисный стиль** — Celery-очереди как отдельные «сервисы»; понять retry/backoff и согласованность БД (P0.2)
- [ ] **Redis** — сейчас только broker; кеширование не используется (для v1, скорее всего, не нужно)

### Добавить в проект (по приоритету)

| Технология | Зачем | Где в бэклоге |
|------------|-------|----------------|
| **Telethon / MTProto (asyncio)** | restore download, стабильный upload | P0.2, [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md) |
| **asyncio в sync Celery** | обёртка `asyncio.run` для client provider | P0.2 (spike в migration doc) |
| **Structured logging** | correlation `session_id`, worker logs | P0.2 |
| **import-linter** | автоматические границы слоёв (сейчас только AST-тест) | P2 |
| **GitHub Actions CI** | ruff, mypy, pytest на каждый PR | P2 |
| **Prometheus / metrics** (optional) | длительность archive/upload, queue depth | P2 observation или после стабильного restore |
| **Grafana** (optional) | дашборды поверх metrics | после Prometheus |
| **Alembic** (optional) | если вырастем из hand-written SQL | при следующей смене схемы после P0 |
| **Kubernetes** (optional, far) | деплой workers + postgres вне compose | не v1; только если понадобится prod-хостинг |

### Есть в проекте, но нет в CV — освоить здесь

- [x] **Onion / clean architecture** — порты (`Protocol`), public API, bootstrap wiring (P0, закрыт 2026-06)
- [ ] **Tkinter** — `application/gui/`; доработка UX (P0.3)
- [ ] **7z / p7zip** — `seven_zip_service.py`, encrypt + split volumes
- [ ] **Telegram Bot API** — legacy `TelegramProviderV1`; решение keep vs remove → **P0.2** (не «понять перед заменой», а осознанный выбор после Client API default)
- [ ] **psycopg3** — прямые SQL в `migrate.py` (параллельно SQLAlchemy)

### Из CV — не планируется в v1

| Технология | Причина |
|------------|---------|
| FastAPI, REST, OpenAPI, Postman | desktop app, не HTTP backend |
| OAuth2, JWT, RBAC | нет multi-user auth в v1 |
| Stripe, PayPal, Booking CM | вне продукта |
| RabbitMQ | Celery уже на Redis |
| GitLab CI/CD | в репо планируется GitHub Actions (P2) |

### Чеклист «пройти технологию»

При закрытии пункта: **прочитал код → поправил/добавил → тест → ручной smoke** (см. правила выше).

- [ ] Пройти **use_cases + SQLAlchemy** вместе (P0.1)
- [ ] Пройти **Celery + Redis + asyncio/Telethon** вместе (P0.2)
- [ ] Пройти **Tkinter + BackupApi** вместе (P0.3)
- [ ] Настроить **CI** (ruff, mypy, pytest) — P2
- [ ] (Опционально) spike **Prometheus metrics** на worker task duration

---

## P0 — Architecture cleanup & code quality (срочно)

**Главный приоритет.** Текущий код работает, но архитектурно разъехался; чинить **слой за слоем**, начиная с `use_cases`.

Референс: [PROJECT.md §4–5](PROJECT.md#4-архитектура), границы — `tests/test_layer_boundaries.py`.

### P0.1 — `use_cases` (первый проход)

- [ ] Аудит пакета: дубли, лишние зависимости, согласованность портов и `*Record`
- [ ] **Hexagonal architecture audit + naming pass** — пройти слои по [PROJECT.md §4](PROJECT.md#4-архитектура) и [SOLID_AUDIT.md](SOLID_AUDIT.md) после курса/ролика по hexagonal; зафиксировать глоссарий «кто что называется» (domain action vs use case vs adapter vs entrypoint). **Переименовать** классы/методы в `use_cases/` и `infrastructure/`, где имена размывают границы или дублируют соседний слой без причины — пример боли: `CheckRestoreReadyUseCase` (UC) ↔ `GuiEntrypoint.check_restore_ready` ↔ `BackendReceiver.check_restore_ready` (три «check_restore_ready» в цепочке, смысл разный). Цель: один канонический термин на сценарий, слой виден из имени (или из пакета), без копипасты суффиксов `UseCase` ради формы. **Не big-bang:** move-only PR + rename PR; gate — `pytest` + `lint-imports` + Roman smoke backup/restore.
- [x] Выровнять restore/upload ref helpers под Client API (`client:` only, `has_legacy_bot_volumes`) — [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md)
- [x] Pipeline rules вынесены из `domain`: `backup/gates.py`, `backup/idempotency.py`, `restore/refs.py`
- [x] Idempotency policy в `use_cases/backup/idempotency.py`
- [x] Failed-status wiring в Celery `tasks.py` (UC-4)
- [x] Public API: `BackupApi` / `WorkerApi`; facade удалён (UC-3)
- [x] Restore refs + extract → `dest_path` (UC-5, UC-7)
- [ ] **Legacy Bot API — разгрести restore-слой** — сейчас legacy размазан по `restore/refs.py` (`is_legacy_volume`, `count_legacy_volumes`, `restore_ref_for_volume` → `DomainError.legacy_volumes()`), `check_restore_ready` + `preflight_types` (`LEGACY_VOLUMES`), `application/restore_preflight_messages`, `domain/errors.py`. **Зависит от** решения **Bot API: keep vs remove** (P0.2 ниже): (A) remove — выкинуть `UNSUPPORTED_LEGACY`, bot provider, legacy preflight/copy; restore = только `client:` refs. (B) keep upload-only — один явный модуль/док «bot backups never restore», минимум веток в refs. (C) migration — re-backup path, потом удалить legacy. **Цель:** перестать таскать «ёбаный legacy» через каждый файл restore при чтении кода. **Gate:** решение P0.2 зафиксировано + diff уменьшает legacy surface в `use_cases/restore/` (или удаляет полностью); `pytest` + Roman smoke restore/preflight для client-only и (если keep) bot-upload сценария.

**Gate:** слой читается как эталон; ты прошёл backup happy path вручную после правок.

### P0.2 — `infrastructure`

- [x] `TelegramClientProvider` + `TELEGRAM_PROVIDER` switch — [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md)
- [ ] **Client API + Bot API — слить или развести осознанно** — вопрос: почему нельзя restore backup, залитый через Bot API, через Client API (MTProto)? **Гипотеза:** файл в той же группе → user-session может `get_messages` + `download_media` по `chat_id` + `message_id`, если ref в БД это позволяет (сейчас bot volumes хранят bot `file_id`, restore policy — только `client:…`, иначе `legacy_volumes`). **Разобрать:** (1) что сохраняем при bot upload (`external_message_id`, `provider_download_ref`); (2) можно ли resolve bot ref → client ref без re-backup; (3) один unified provider vs два adapter + `TELEGRAM_PROVIDER=client|bot`; (4) upload bot + restore client — один продуктовый путь или dead end. **Связано:** **Bot API: keep vs remove** (ниже), **Legacy Bot API — разгрести restore-слой** (P0.1). **Gate:** design note в [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md) («restore bot-era via client: да/нет и почему») + решение merge / client-only / re-backup; smoke если выбран restore старых bot backup без re-upload.
- [ ] **Bot API: keep vs remove** — проработать, стоит ли оставлять legacy Bot API (`TelegramProviderV1`, compose `--profile bot`, вкладка Settings «Bot API»). **Контекст:** Client API — default; restore только для `client:` refs; Bot-backups не restorable (`is_legacy_volume` / `LEGACY_VOLUMES` preflight, предупреждение в Settings). **Связано:** **Legacy Bot API — разгрести restore-слой** (P0.1); **Client API + Bot API — слить или развести** (выше). **Варианты:** (A) удалить полностью; (B) upload-only, «no restore»; (C) re-backup через Client API; (D) client restore по `message_id` для bot-era volumes (если design note подтвердит). **Gate:** решение в [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md) + [PROJECT.md](PROJECT.md); если remove — код/settings/compose вычищены; Roman smoke backup+restore на Client-only path.
- [x] Structured logging (file + unified format) — `telegram-uploader.log`; correlation `session_id` — позже

**Gate:** `docker compose up` + полный backup smoke; restore download без 404 — **Test Client API ✅; GUI Restore Session — Roman**.

### P0.3 — `application` + GUI

- [x] `backend_receiver` → `BackupApi`, тонкие DTO
- [x] R3: autoclave key messagebox + clipboard
- [x] Понятные ошибки, failed/stuck статусы, restore UX, Settings MVP
- [x] PROJECT §12 full GUI (Unlock, explorer, drawer, restore, Client login)

**Gate:** ты сам прошёл полный сценарий в GUI после правок слоя.

---

## P1 — Restore end-to-end (product)

- [x] Скачать volumes + 7z extract в `dest_path` (UC-7)
- [x] Test Client API upload + download round-trip (Settings / opt-in integration test)
- [ ] **GUI Restore Session smoke** (Roman) — полный цикл backup → restore → файл в папке
- [ ] Resume downloads (nice to have)

**Gate:** Restore Session → оригинальный файл в выбранной папке; **Roman ручная проверка** (Test Client API — предварительный gate download).

---

## P1.1 — GUI: файлы и импорт из Telegram

### Сделано (2026-06)

- [x] Контекстное меню файла (double-click / ПКМ): **Rename**, **Move to folder**, **Delete**
- [x] Минималистичная тёмная тема (unlock card + explorer)

### Запланировано

- [ ] **Import from Telegram group** — подтянуть архивы из backup-группы, которых **нет в GUI** (orphan messages / volumes без `source_item`):
  1. Скан группы (`TELEGRAM_TARGET_CHAT_ID`) по `client:` refs, которых нет в БД текущей session.
  2. Скачать + распаковать во **временную** папку restore staging.
  3. Создать виртуальную папку **`Restored`** (или «Восстановленное») и импортировать записи туда.
  4. В таблице такие файлы помечать **жёлтым замочком** (`external` / «imported from Telegram») — не были добавлены через Add File.
  5. Пользователь может переименовать / перенести / удалить / повторно backup как обычный item.
- [ ] **Cross-session import (Client API)** — восстанавливать файлы из **другой** backup-группы или чужой session и добавлять в **свою** session (расширение Import выше). До скачки: `source_item` без локального файла → Size/Modified = «—» в `GetSessionProgressUseCase`. После скачки/импорта: прописать `source_path` на файл на диске **или** сохранить `size_bytes` / mtime в БД → таблица подхватит размер при Refresh. **Сейчас не проработано:** `RestoreSessionUseCase` пишет в `dest_path`, но **не связывает** восстановленный файл с записью в очереди.
- [ ] **Настройка папки для restore (результат extract)** — в Settings задать **папку по умолчанию**, куда кладётся восстановленный файл после 7z extract (`dest_path`). **Сейчас:** hardcode `~/Restored/` в `application/gui/restore_dest.py`; каждый Restore — `filedialog` с `initialdir` оттуда; путь не сохраняется между сессиями. **Сделать:** поле в Settings (+ persist в `.env` / `SettingsValues`, как остальные настройки); optional режим «всегда сюда без диалога» vs «только подставлять в диалог». UC `validate_restore_dest_path` без изменений. **Не путать** со staging (`archive_cache_dir/restore`) — там encrypted `.7z.*`, не user-facing результат. **Gate:** сохранил path в Settings → Restore использует его; Roman smoke: restore в не-default папку, перезапуск GUI — path помнится.
- [ ] **Restore Session UX** — см. **Настройка папки для restore** выше; прочее: restore completed items в scope, empty-folder warnings (частично UC-7).

**Gate:** в группе есть backup без записи в GUI → Import → файл в папке «Restored» с замочком → rename/move работает.

---

## P1.2 — GUI visual polish

KeePassXC-style layout + theme fix — **первая итерация** (2026-06). Визуал ещё сырой: ttk edge cases, spacing, dialogs, toolbar.

### Запланировано

- [ ] **Progress bar (переделать)** — нижний drawer сейчас **не отражает ход backup**:
  - `ProgressDrawer` (`drawer.py`) — только `indeterminate` анимация; после `Start Backup` сразу `show_result` → бар останавливается и скрывается, хотя workers ещё работают.
  - Нет polling `get_session_progress` во время pipeline; пользователь видит «Backup started» / «Enqueued N item(s)», но не прогресс по файлам (`queued` → `archiving` → `uploading` → `completed`).
  - **Цель:** determinate bar или пошаговый статус (N/M файлов, текущий этап); обновление по Refresh или таймеру, пока есть items in progress; idle когда всё `completed` / `failed`.
  - Затронет: `drawer.py`, `app.py` (`_on_start_backup`, `_refresh_queue`), возможно `ProgressDTO` / `GetSessionProgressUseCase`.
- [ ] **Второй проход по GUI** — контраст и ttk maps (Settings tabs, Combobox popup, TButton states), toolbar/icons, spacing, unlock card, progress drawer layout, единая типографика; pixel-perfect KeePassXC не цель, но **читаемость и целостность** — да.
- [ ] Проверка на установленном `.deb` (Ubuntu 24.04): все экраны читаемы, нет белого на белом, layout стабилен при resize.

**Gate (progress bar):** Start Backup с 2+ файлами → бар движется/считает до `completed` без ручного Refresh; smoke на `.deb`.

**Gate (visual polish):** Roman smoke после `.deb` install — Unlock, vault, Settings, context menu; resize окна без артефактов.

---

## ~~P1.3 — Packaged install (.deb)~~ ✅ закрыт (0.1.9)

**Итог:** `.deb` на GitHub Releases; clean install + upgrade в README; release notes в `docs/releases/v0.1.9.md`; sign-in, Test Client API, archive worker fixes (`INSTALL_ROOT` mount, stale 7z cleanup).

**Gate закрыт:** `.deb` install → Settings → Test Client API → backup smoke.

---

## P2 — Observation / CI

- [ ] **AI agent skills** — [AI_AGENT_SKILLS.md](AI_AGENT_SKILLS.md): `.cursor/skills/` (onion-layers, gate-and-smoke); wire stop-slop for prose; clone `--recurse-submodules`
- [x] `import-linter` + `.importlinter` (UC-8)
- [x] `.github/workflows/ci.yml` — ruff, mypy, pytest, lint-imports
- [ ] `src/observation/health.py` (optional) — postgres, redis, telegram session
- [x] `telegram-uploader.log` in `.gitignore` (unified app log)

Уже есть: `pytest`, `ruff`, `mypy`, `tests/test_layer_boundaries.py`, Celery log timestamps.

---

## P3 — Tests & integration

- [ ] `tests/test_worker_pipeline_integration.py` — full chain in Docker
- [ ] `tests/test_repositories_integration.py` — live PostgreSQL
- [ ] Live Telegram smoke (opt-in) после Client API

---

## ~~P4 — `domain` cleanup~~ ✅ закрыт (2026-06)

**Итог:** ядро = `models.py` + `actions.py` + `errors.py`. Вынесено в `use_cases`: not-found (`loading`), backup gates, idempotency, restore refs. `guards.py` / `scenarios.py` удалены.

**Gate закрыт:** границы зафиксированы в [PROJECT.md](PROJECT.md) и `tests/test_layer_boundaries.py`; unit-тесты зелёные.

Опционально позже (не блокер): generic `verify`/`mark` с `@overload` — только если при ревью `use_cases` станет больно без этого.

**Следующие слои:** P0.1 `use_cases` → P0.2 `infrastructure` → P0.3 `application` → P2 observation.

---

## ~~P5 — Docs sync~~ ✅ закрыт (2026-06-12)

**Итог:** [PROJECT.md](PROJECT.md), README, Telegram guides, `docs/releases/`; удалены устаревшие redirect-файлы и `docs/refactor/`.

---

## Side projects (future — not v1 backlog)

- **[BACKUPVAULT_IMPLEMENTATION.md](BACKUPVAULT_IMPLEMENTATION.md)** — joint DevOps learning with a partner; separate `backupvault` repo; return after v1 gate. **No code changes in telegram-uploader required until then.**

---

## Explicitly out of scope (v1)

- Telegram topics (`message_thread_id`) — [INTERNAL_SPEC.md](INTERNAL_SPEC.md)
- Auto-moving user source files into service directory
- Max / VK providers (port ready, no adapter)

---

## Open fixes (smoke 2026-06-12)

Подробности: [refactor/CHANGES.md](refactor/CHANGES.md).

- [ ] **FIX-1** — Progress bar «мёртвый» при backup: нет polling `get_session_progress` (P1.2)
- [ ] **FIX-2** — `database is locked` — **переоценено:** два окна GUI на одном `session.session`; не primary blocker
- [ ] **FIX-3** — Restore в background thread — **partial** (`app.py`); progress animation TBD
- [ ] **FIX-4** — 7z extract `Permission denied` — **fix landed** (dest validation + messages); Roman smoke TBD

**Workaround smoke:** одно окно GUI; restore в **пустую** папку в `$HOME` (не под `/opt/telegram-uploader/`).

---

*При закрытии пункта — удаляй из этого файла.*
