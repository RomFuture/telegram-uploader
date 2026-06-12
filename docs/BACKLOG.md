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
- [ ] Backup happy path работает *(уже есть)* · Client API / restore — по возможности, не блокер demo если backup стабилен

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

- [ ] **Onion / clean architecture** — порты (`Protocol`), facade, bootstrap wiring (главная цель P0)
- [ ] **Tkinter** — `application/gui/`; доработка UX (P0.3)
- [ ] **7z / p7zip** — `seven_zip_service.py`, encrypt + split volumes
- [ ] **Telegram Bot API** — legacy `TelegramProviderV1`; понять перед заменой на Client API
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
- [ ] Пройти **Tkinter + facade** вместе (P0.3)
- [ ] Настроить **CI** (ruff, mypy, pytest) — P2
- [ ] (Опционально) spike **Prometheus metrics** на worker task duration

---

## P0 — Architecture cleanup & code quality (срочно)

**Главный приоритет.** Текущий код работает, но архитектурно разъехался; чинить **слой за слоем**, начиная с `use_cases`.

Референс: [PROJECT.md §4–5](PROJECT.md#4-архитектура), границы — `tests/test_layer_boundaries.py`.

### P0.1 — `use_cases` (первый проход)

- [ ] Аудит пакета: дубли, лишние зависимости, согласованность портов и `*Record`
- [ ] Выровнять restore/upload ref helpers под будущий Client API (см. [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md))
- [x] Pipeline rules вынесены из `domain`: `backup/gates.py`, `backup/idempotency.py`, `restore/refs.py`
- [x] Idempotency policy в `use_cases/backup/idempotency.py`
- [x] Failed-status wiring в Celery `tasks.py` (UC-4)
- [x] Public API: `BackupApi` / `WorkerApi`; facade удалён (UC-3)
- [x] Restore refs + extract → `dest_path` (UC-5, UC-7)

**Gate:** слой читается как эталон; ты прошёл backup happy path вручную после правок.

### P0.2 — `infrastructure`

- [x] `TelegramClientProvider` + `TELEGRAM_PROVIDER` switch — [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md)
- [ ] Deprecate Bot API после стабильного client restore smoke
- [ ] Structured logging (минимум — единый формат в worker/bootstrap)

**Gate:** `docker compose up` + полный backup smoke; restore download без 404 (после Client API).

### P0.3 — `application` + GUI

- [x] `backend_receiver` → `BackupApi`, тонкие DTO
- [x] R3: autoclave key messagebox + clipboard
- [x] Понятные ошибки, failed/stuck статусы, restore UX, Settings MVP
- [x] PROJECT §12 full GUI (Unlock, explorer, drawer, restore, Client login)

**Gate:** ты сам прошёл полный сценарий в GUI после правок слоя.

---

## P1 — Restore end-to-end (product)

После Client API smoke:

- [x] Скачать volumes + 7z extract в `dest_path` (UC-7)
- [ ] Resume downloads (nice to have)

**Gate:** Restore Session → оригинальный файл в выбранной папке; ручная проверка.

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
- [ ] **Restore Session UX** — отдельная пустая папка по умолчанию; restore всех completed items по одному extract на файл (частично сделано в UC-7).

**Gate:** в группе есть backup без записи в GUI → Import → файл в папке «Restored» с замочком → rename/move работает.

---

## P1.2 — GUI visual polish

KeePassXC-style layout + theme fix — **первая итерация** (2026-06). Визуал ещё сырой: ttk edge cases, spacing, dialogs, toolbar.

### Запланировано

- [ ] **Второй проход по GUI** — контраст и ttk maps (Settings tabs, Combobox popup, TButton states), toolbar/icons, spacing, unlock card, progress drawer, единая типографика; pixel-perfect KeePassXC не цель, но **читаемость и целостность** — да.
- [ ] Проверка на установленном `.deb` (Ubuntu 24.04): все экраны читаемы, нет белого на белом, layout стабилен при resize.

**Gate:** Roman smoke после `.deb` install — Unlock, vault, Settings, context menu; resize окна без артефактов.

---

## P1.3 — Packaged install (.deb)

### Запланировано (следующий релиз после 0.1.3)

- [x] **Test Client API — test file в .deb** — bundled `share/client_api_test.md` в пакете; `_client_api_test_file()` ищет `share/` затем `docs/refactor/README.md`.
- [x] **Проверка зависимостей при установке** — `check-deps.sh`, `telegram-uploader-check-deps`, postinst + launcher; README: `apt install ./deb` не `dpkg -i` alone.
- [ ] **Settings → сохранение в `~/.config/telegram-uploader/.env`** — Save пишет `.env`; Sign in to Telegram… + `telegram-uploader-login` с intro. Gate: Save → login → Test Client API OK.

**Gate:** `.deb` install → Settings → Test Client API → OK (или понятная ошибка auth, не missing file); Save → backup smoke.

---

## P2 — Observation / CI

- [ ] **AI agent skills** — [AI_AGENT_SKILLS.md](AI_AGENT_SKILLS.md): `.cursor/skills/` (onion-layers, gate-and-smoke); wire stop-slop for prose; clone `--recurse-submodules`
- [x] `import-linter` + `.importlinter` (UC-8)
- [x] `.github/workflows/ci.yml` — ruff, mypy, pytest, lint-imports
- [ ] `src/observation/health.py` (optional) — postgres, redis, telegram session
- [ ] `logs/` в `.gitignore` для session logs

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

## P5 — Docs sync

- [x] [PROJECT.md](PROJECT.md) — синхрон с кодом после R2–R8 (R8)

---

## Side projects (future — not v1 backlog)

- **[BACKUPVAULT_IMPLEMENTATION.md](BACKUPVAULT_IMPLEMENTATION.md)** — joint DevOps learning with a partner; separate `backupvault` repo; return after v1 gate. **No code changes in telegram-uploader required until then.**

---

## Explicitly out of scope (v1)

- Telegram topics (`message_thread_id`) — [INTERNAL_SPEC.md](INTERNAL_SPEC.md)
- Auto-moving user source files into service directory
- Max / VK providers (port ready, no adapter)

---

*При закрытии пункта — удаляй из этого файла.*
