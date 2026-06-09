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
use_cases  →  infrastructure  →  application
```

`domain` трогаем только если use_cases вскрыл проблему в ядре. GUI — на этапе `application`, после того как низ стабилен.

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

> Полные определения и цикл → **[ONION_LAYER_IMPLEMENTATION.md](ONION_LAYER_IMPLEMENTATION.md)**

| Термин | Суть |
|--------|------|
| **Gate** | Критерий «можно идти дальше» (не «поработал час»). Пример: restore download без 404. |
| **Smoke** | 5–15 мин **руками**: GUI или round-trip файла. `pytest` alone **не считается**. |

**Без закрытого gate следующий слой / пункт бэклога не начинаем.**

**Roman vs ИИ:** smoke и закрытие gate — **только Roman руками**; ИИ пишет код и тесты, но не засчитывает «готово». Таблица → [ONION_LAYER_IMPLEMENTATION.md §4](ONION_LAYER_IMPLEMENTATION.md#4-обязательный-цикл-на-каждую-заметную-правку).

### Как закрывать пункты бэклога

1. Правка в одном слое *(ИИ может помочь с кодом · Roman читает diff)*  
2. **Roman** гоняет `pytest` + `ruff` + `mypy` у себя  
3. **Roman** делает **ручной smoke** (обязательно · ИИ не заменяет)  
4. **Roman** подтверждает gate → пункт **удаляется** отсюда *(не ИИ)*  

Большие планы — отдельные `docs/*_MIGRATION.md`; в бэклоге только ссылка + gate.

---

## P-demo — v1 «показать другу» (Roman 09.06)

**Цель:** на встрече с другом показать, что **первая версия уже есть** — не финал, но клонируется и запускается. Приоритет **над** косметикой GUI и P4 domain.

- [ ] **`scripts/run.sh`** (или `make demo`) — **один скрипт**: `docker compose up -d` + миграции + инструкция/GUI
- [ ] **`.github/workflows/ci.yml`** — ruff, mypy, `pytest -m "not integration"` на push/PR
- [x] **README** + **[TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)** — setup from scratch (bot, API keys, group, `./scripts/run.sh`, smoke backup)
- [ ] **Onboarding automation** — GUI wizard: API id/hash, bot, group id, `.env`; позже Client API login ([README](../README.md#onboarding-automation-planned))
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

Референс: [ONION_ARCHITECTURE.md](ONION_ARCHITECTURE.md), границы — `tests/test_layer_boundaries.py`.

### P0.1 — `use_cases` (первый проход)

- [ ] Аудит пакета: дубли, лишние зависимости, согласованность портов и `*Record`
- [ ] Выровнять restore/upload ref helpers под будущий Client API (см. [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md))
- [ ] Failed-status / idempotency policy в use cases (не в `tasks.py`)
- [ ] Убрать tech debt, вскрытый при ревью (мапперы, loading, дубли в backup/restore)
- [ ] Тесты после каждого блока правок: `pytest tests/test_use_cases_*.py -v`

**Gate:** слой читается как эталон; ты прошёл backup happy path вручную после правок.

### P0.2 — `infrastructure`

- [ ] Аудит: bootstrap/facade wiring, провайдеры, workers, db mappers
- [ ] Client API provider (можно встроить в этот проход) — [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md)
- [ ] Убрать/изолировать legacy Bot API после client stable
- [ ] Structured logging (минимум — единый формат в worker/bootstrap)
- [ ] Failed pipeline rollback на уровне use case + корректные статусы в БД

**Gate:** `docker compose up` + полный backup smoke; restore download без 404 (после Client API).

### P0.3 — `application` + GUI

- [ ] Аудит `backend_receiver` — только facade, тонкие DTO
- [ ] **Доработка GUI** (не только MVP):
  - [ ] Понятные ошибки (не сырой traceback)
  - [ ] Отображение failed / stuck статусов
  - [ ] Settings: encryption key, target chat (после Client API — session auth)
  - [ ] Restore UX: прогресс, куда сохранилось, ошибки download/extract
- [ ] (Позже) GUI в контейнере — единая FS с workers

**Gate:** ты сам прошёл полный сценарий в GUI после правок слоя.

---

## P1 — Restore end-to-end (product)

После P0.2 (download) + частично P0.1:

- [ ] Скачать все volumes по `part_number`
- [ ] 7z decrypt/extract с `encryption_key` сессии
- [ ] Результат в **user-selected `dest_path`** (баг: сейчас пишет в staging)
- [ ] Статусы restore: success / `failed`
- [ ] Resume downloads (nice to have)

**Gate:** Restore Session → оригинальный файл в выбранной папке; ручная проверка.

---

## P2 — Observation / CI

- [ ] **AI agent skills** — [AI_AGENT_SKILLS.md](AI_AGENT_SKILLS.md): `.cursor/skills/` (onion-layers, gate-and-smoke); wire stop-slop for prose; clone `--recurse-submodules`
- [ ] `import-linter` + `.importlinter` (adjacent-layer contracts)
- [ ] `.github/workflows/ci.yml` — ruff, mypy, `pytest -m "not integration"`, `lint-imports`
- [ ] `src/observation/health.py` (optional) — postgres, redis, telegram session
- [ ] `logs/` в `.gitignore` для session logs

Уже есть: `pytest`, `ruff`, `mypy`, `tests/test_layer_boundaries.py`, Celery log timestamps.

---

## P3 — Tests & integration

- [ ] `tests/test_worker_pipeline_integration.py` — full chain in Docker
- [ ] `tests/test_repositories_integration.py` — live PostgreSQL
- [ ] Live Telegram smoke (opt-in) после Client API

---

## P4 — `domain` cleanup (deferred)

**Gate:** P0.1 use_cases review не выявил блокеров в domain; restore e2e стабилен.

- [ ] Generic `ensure` / `mark` with `@overload`
- [ ] Scenario-first public API
- [ ] Merge `guards.py` + `scenarios.py` (если оправдано)
- [ ] Audit `domain/__init__.py` exports

---

## P5 — Docs sync

- [ ] [ONION_ARCHITECTURE.md](ONION_ARCHITECTURE.md) — Client API в runtime stack, актуальные диаграммы
- [ ] Root [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) — archive or trim

---

## Explicitly out of scope (v1)

- Telegram topics (`message_thread_id`) — [INTERNAL_SPEC.md](INTERNAL_SPEC.md)
- Auto-moving user source files into service directory
- Max / VK providers (port ready, no adapter)

---

*При закрытии пункта — удаляй из этого файла.*
