# Onion Architecture — целевая структура проекта

Документ фиксирует **как должны быть устроены слои**, папки и зависимости в `telegram-uploader`.

Это **источник истины по архитектуре**. При расхождении с [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) (в т.ч. §2.1) **приоритет у этого файла**.

Связанные документы:

- [docs/INTERNAL_SPEC.md](INTERNAL_SPEC.md) — обязательные продуктовые правила (язык UI, шифрование, `display_name`, restore metadata).
- [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) — этапы внедрения, Telegram-first roadmap, тестовая стратегия.
- [STEP_BY_STEP_IMPLEMENTATION_GUIDE.md](../STEP_BY_STEP_IMPLEMENTATION_GUIDE.md) — пошаговые чекпоинты сборки проекта.
- [ONION_LAYER_IMPLEMENTATION.md](ONION_LAYER_IMPLEMENTATION.md) — пошаговая имплементация по слоям (implement → test → verify).

---

## 1) Принцип: линейный стек слоёв

Проект строится как **строгий линейный стек**: в центре — `domain` (физически `use_cases/domain/`), снаружи — остальной `use_cases`, затем `infrastructure`, `application`, `observation`. Это не forked-onion (где `application` и `infrastructure` оба смотрят в `use_cases` параллельно), а **цепочка соседей**.

### Правило соседних слоёв (главное)

**Каждый слой импортирует только одного непосредственного соседа внутрь** (ближе к ядру).  
**Ни один слой не импортирует слои выше себя** — все: `domain`, `use_cases`, `infrastructure`, `application`.

Цепочка (от ядра к периферии):

```
domain  →  use_cases  →  infrastructure  →  application  →  observation
```

**Запрос вниз** (к ядру):

```
application  →  infrastructure  →  use_cases  →  domain
```

**Ответ вверх** (к пользователю; `domain` наружу не отвечает — там нет исходящих вызовов):

```
use_cases  →  infrastructure  →  application
```

| Слой | Импортирует (сосед внутрь) | Вызывается из (сосед снаружи) |
|------|---------------------------|--------------------------------|
| `use_cases/domain` (ядро) | только stdlib | остальной `use_cases` |
| `use_cases` (мозг) | `use_cases.domain` | `infrastructure` |
| `infrastructure` | `use_cases` | `application`, Celery worker entrypoints |
| `application` | `infrastructure` | `observation`, пользователь (GUI) |
| `observation` | любой слой | — (снаружи runtime: тесты, CI, health) |

**Критично:** `infrastructure` **не** импортирует `use_cases.domain`. ORM-строки маппятся в **persistence-записи** (`use_cases/persistence.py`), а `use_cases` переводит записи ↔ доменные сущности.

**Критично:** `application` **не** импортирует `use_cases` и `use_cases.domain`. GUI и `backend_receiver` ходят только в **`infrastructure.facade`**.

Слой взаимодействует с соседом через **публичный API** (`BackupFacade`, порты, persistence-записи). Внутреннему слою **плевать**, кто вызывает — GUI, Celery worker или тест: для него любой вызов это просто **вводные данные**.

```mermaid
flowchart TB
  observation[observation]
  application[application]
  infrastructure[infrastructure]
  use_cases[use_cases]
  domainSub["use_cases/domain"]

  observation --> application
  application --> infrastructure
  infrastructure --> use_cases
  use_cases --> domainSub["use_cases/domain"]
```

### Разрешённые зависимости

| Откуда | Куда | Как |
|--------|------|-----|
| `use_cases` | `use_cases.domain` | бизнес-оркестрация; маппинг persistence-запись ↔ домен |
| `infrastructure` | `use_cases` | `BackupFacade`, реализации портов, wiring use cases, ORM ↔ `persistence.*` |
| `application` | `infrastructure` | `backend_receiver` → `BackupFacade`; GUI не знает про use cases |
| `observation` | любой слой | тесты, линтеры, health-check **снаружи** runtime |

### Запрещённые зависимости

| Зависимость | Почему ломает стек |
|-------------|-------------------|
| `application → use_cases` | UI перепрыгивает через `infrastructure` |
| `application → domain` | UI перепрыгивает через `infrastructure` и `use_cases` |
| `infrastructure → use_cases.domain` | адаптер перепрыгивает через `use_cases`; infrastructure знает только `persistence` и порты |
| `use_cases → infrastructure` | сосед внутрь — только `use_cases.domain`; wiring делает `infrastructure` при вызове |
| `use_cases → application` | мозг не знает про UI |
| `use_cases.domain → *` (кроме stdlib) | ядро не знает о портах, persistence, infrastructure |
| импорт `use_cases.domain` вне пакета `use_cases` | домен не торчит наружу мозга |
| `infrastructure → application` | руки не знают про UI |
| `use_cases → sqlalchemy`, `urllib`, `celery` | I/O-детали не в мозге |
| Любой слой → слой **выше** себя | нарушение соседства |

**Composition root** — единственное место склейки портов и реализаций: [`src/infrastructure/bootstrap.py`](../src/infrastructure/bootstrap.py) (целевой путь).

> **Техдолг:** сейчас bootstrap ещё в [`src/application/bootstrap.py`](../src/application/bootstrap.py) и `docker-compose` вызывает `python -m application.bootstrap`. Перенос кода — отдельная задача; целевая точка входа — `python -m infrastructure.bootstrap`.

**Публичный API для application:** [`src/infrastructure/facade.py`](../src/infrastructure/facade.py) (`BackupFacade`) — единая точка входа: `enqueue_file`, `start_session`, `get_progress`, …

### Где живёт фоновый конвейер

GUI **не выполняет** тяжёлую работу (7z, upload, download). Цепочка:

1. `gui` → `backend_receiver` → `infrastructure.facade`
2. `facade` создаёт use case, вызывает `.execute()`
3. use case через `TaskQueuePort` ставит задачу в **Celery** / **Redis**
4. **воркер** (`infrastructure/worker/`) — тот же путь: entrypoint → use case, без `application`

Бизнес-решения — в `use_cases`. `infrastructure` — исполнение и wiring.

```mermaid
flowchart LR
  subgraph application_layer [application]
    GUI[gui]
    Receiver[backend_receiver]
  end
  subgraph infra_layer [infrastructure]
    Bootstrap[bootstrap]
    Facade[BackupFacade]
    CeleryApp[celery_app]
    Tasks[tasks]
    Zip[SevenZipService]
    DB[SqlAlchemyRepos]
    TG[TelegramProviderV1]
  end
  subgraph use_cases_layer [use_cases]
    UC[EnqueueSourceItemUseCase]
    subgraph uc_domain [use_cases/domain]
      Models[models.py]
      Mappers[record_to_domain mappers]
    end
    UC --> Mappers
    Mappers --> Models
  end
  subgraph runtime [Runtime docker-compose]
    Redis[(Redis)]
    Postgres[(PostgreSQL)]
    BotAPI[telegram-bot-api]
  end

  GUI --> Receiver
  Receiver --> Facade
  Facade --> UC
  UC -->|"TaskQueuePort"| CeleryApp
  CeleryApp --> Redis
  Redis --> Tasks
  Tasks --> Facade
  Facade --> UC
  UC --> Zip
  UC --> DB
  UC --> TG
  DB --> Postgres
  TG --> BotAPI
  Bootstrap -->|"health + wiring"| Facade
```

---

## 2) Пять слоёв

Описание идёт **от ядра к периферии** (domain → … → observation).

### Слой 1 — `domain` (центр, внутри `use_cases`)

**Логически** — самый внутренний слой («бумажная работа»). **Физически** — подпапка **`use_cases/domain/`**, отдельного пакета `src/domain/` **нет**. В домене нет функций оркестрации — только модели, статусы и (позже) доменные ошибки.

| Сущность | Назначение |
|----------|------------|
| `Session` | сессия бэкапа, ключ шифрования, статус |
| `SourceItem` | файл в очереди (`source_path`, `display_name`, статус) |
| `ArchiveVolume` | том архива + provider metadata для restore |

Статусы: `SessionStatus`, `SourceItemStatus`, `ArchiveVolumeStatus`.

**Пакет (цель):** `use_cases/domain/models.py`, `use_cases/domain/errors.py`

| Можно | Нельзя |
|-------|--------|
| `dataclass`, `Enum`, чистые функции над моделями | SQL, HTTP, SQLAlchemy, Celery, Telegram API |
| импорт только stdlib | импорт `ports`, `persistence`, `backup`, `infrastructure`, `application` |
| | импорт снаружи пакета `use_cases` (кроме тестов) |

**Готовность:** модели есть в [`src/domain/`](../src/domain/) — **техдолг:** перенести в `use_cases/domain/`.

---

### Слой 2 — `use_cases` (мозг, пакет целиком)

**Роль:** принимает намерение пользователя («забэкапить файл», «восстановить сессию»), валидирует, режет на подзадачи, оркестрирует модули **через порты**. Не выполняет I/O сам.

Примеры будущих классов:

- `EnqueueSourceItemUseCase` — пользователь добавил файл в очередь
- `StartBackupPipelineUseCase` — запуск конвейера archive → upload → cleanup
- `RestoreSessionUseCase` — скачать тома и распаковать

**Пакет:** [`src/use_cases/`](../src/use_cases/)

Пакет `use_cases` **включает** ядро `use_cases/domain/` (слой 1) и оркестрацию вокруг него (слой 2). Сосед снизу для `backup/`, `ports/`, `repositories/` — всегда `use_cases.domain`.

| Можно | Нельзя |
|-------|--------|
| `from use_cases.domain.models import Session` в use case-классах | `from domain import ...` (старый top-level пакет) |
| `use_cases/domain/mappers.py` — record ↔ доменные модели | `import use_cases.domain` из `infrastructure` / `application` |
| `use_cases/domain/transitions.py` — (optional) чистые хелперы смены статусов | |
| `persistence.py` — записи для контракта с infrastructure | `infrastructure.*`, `application.*` |
| `Protocol` (порты репозиториев и сервисов) | SQLAlchemy, `psycopg`, `urllib`, `7z` subprocess |
| DTO (`UploadResult`, `ProviderFileInfo`, …) | конкретные реализации `TelegramProviderV1` |
| `@dataclass` use case с инжектом портов | прямой SQL |

**Готовность:** не готов — нет use case-классов; `repositories.py` и `ports.py` содержат реализации (см. §4).

---

### Слой 3 — `infrastructure` (руки + composition root)

**Роль:** единственная точка входа для `application`; фактическая работа — БД, архивация, провайдер, Celery. Создаёт use cases, инжектит реализации портов, вызывает `.execute()`, возвращает UI-DTO наверх.

| Модуль | Назначение |
|--------|------------|
| `infrastructure/bootstrap.py` | composition root: config, миграции, health, `build_facade()` |
| `infrastructure/facade.py` | `BackupFacade` — публичный API для `application` и worker entrypoints |
| `infrastructure/db/` | SQLAlchemy ORM, мапперы, миграции, реализации `*Repository` |
| `infrastructure/archive/` | `SevenZipService` — шифрование и нарезка томов |
| `infrastructure/providers/` | `TelegramProviderV1` и будущие `Max`/`VK` |
| `infrastructure/worker/` | **Celery** — `celery_app.py`, `tasks.py`; маршрутизация очередей, воркеры |
| `infrastructure/config.py` | env: `POSTGRES_*`, `REDIS_*`, `TELEGRAM_*`, `ARCHIVE_*` |

**Фоновый конвейер:** `use_cases` решает *что* сделать; `infrastructure/worker/tasks.py` — тонкий entrypoint: поднять `BackupFacade` / executor, вызвать use case (целевое состояние; сейчас `tasks.py` — заглушки).

**Пакет:** [`src/infrastructure/`](../src/infrastructure/)

| Можно | Нельзя |
|-------|--------|
| `use_cases.*` (порты, persistence, use case-классы) | `use_cases.domain` (модели домена) |
| создавать use cases, инжектить реализации портов | `application.*` |
| SQLAlchemy, Celery, HTTP, subprocess | бизнес-правила backup (статусы, политика ретраев) |
| ORM ↔ persistence-запись в `infrastructure/db/mappers.py` | |

**Готовность:** частично — адаптеры есть; `facade.py` и `bootstrap.py` (целевые) — нет; границы с `use_cases` нарушены (см. §4).

---

### Слой 4 — `application` (лицо для пользователя)

**Роль:** GUI (English-only) и **прослойка** между пользователем и `infrastructure`. Переводит клики в вызовы `BackupFacade`, показывает UI-DTO наверх. Не знает про use cases, domain, SQL, Celery.

| Компонент | Назначение |
|-----------|------------|
| `application/gui/` | экраны: сессия, очередь, прогресс, restore, настройки |
| `application/backend_receiver.py` | прослойка: событие GUI → `infrastructure.facade` → UI-DTO |

**Пакет:** [`src/application/`](../src/application/)

Папку [`src/presentation/`](../src/presentation/) **слить в** `application/gui/` — дублирует роль слоя 4.

`application/bootstrap.py` — **удалить** (цель); bootstrap переезжает в `infrastructure/`.

| Можно | Нельзя |
|-------|--------|
| `infrastructure.facade` (через `backend_receiver`) | `use_cases.*`, `use_cases.domain.*` |
| UI-строки на английском ([INTERNAL_SPEC](INTERNAL_SPEC.md)) | прямой SQL, Celery, Telegram API |
| | бизнес-логика ретраев и lifecycle |
| | `observation.*` в runtime-коде |

**Готовность:** ~0% GUI; `bootstrap.py` — техдолг (должен быть в `infrastructure`).

---

### Слой 5 — `observation` (кибернетика)

**Роль:** наблюдение за системой — качество кода, логи, health, метрики. Не участвует в backup-логике, оборачивает runtime снаружи.

**Готовность:** 0% как выделенный слой; базовый tooling уже в репозитории.

Подробнее — §5.

---

## 3) Структура каталогов

Слои — **параллельные пакеты** в `src/`, кроме ядра: **`domain` живёт только как `use_cases/domain/`** (подпапка мозга). Логическая глубина задаётся **правилами импортов**, не физической вложенностью всего стека в одну директорию.

При чтении документации порядок слоёв: **domain → use_cases → infrastructure → application → observation**.

### Целевое дерево

```
src/
  use_cases/
    domain/                   # слой 1 (ядро) — целиком внутри use_cases, без отдельного src/domain/
      models.py               # Session, SourceItem, ArchiveVolume + enums
      errors.py               # (future) доменные исключения
      mappers.py              # persistence.SessionRecord ↔ use_cases.domain.Session / SourceItem / ArchiveVolume
      transitions.py          # (optional) чистые хелперы смены статусов
    persistence.py            # SessionRecord, SourceItemRecord, ArchiveVolumeRecord — контракт для infrastructure
    ports/
      storage_provider.py     # StorageProviderPort (Protocol)
      archive_service.py      # (future) ArchiveServicePort
    repositories/
      session.py              # SessionRepository (Protocol) — работает с SessionRecord, не с domain
      source_item.py          # SourceItemRepository (Protocol)
      archive_volume.py       # ArchiveVolumeRepository (Protocol)
    dto.py                    # UploadResult, ProviderFileInfo, ...
    backup/                   # (future) EnqueueSourceItemUseCase, ...
    restore/                  # (future) RestoreSessionUseCase
    session/                  # (future) CreateSessionUseCase, PauseSessionUseCase

  infrastructure/
    bootstrap.py              # composition root: config, миграции, health, build_facade()
    facade.py                 # BackupFacade — публичный API для application
    db/
      orm.py                  # UploadSessionRow, SourceItemRow, ArchiveVolumeRow
      mappers.py              # ORM row ↔ use_cases.persistence.*Record (без use_cases.domain)
      engine.py               # build_db_session_factory, db_session_scope
      sqlalchemy_repositories.py  # реализации Protocol; отдаёт/принимает SessionRecord и т.д.
      migrate.py
      migrations/
    archive/
      seven_zip_service.py
    providers/
      telegram_provider.py    # TelegramProviderV1 — единственное место HTTP к Bot API
    worker/
      celery_app.py
      tasks.py
    config.py

  application/
    backend_receiver.py       # GUI → infrastructure.facade
    gui/                      # Linux UI, English-only

tests/                        # observation: unit / integration / contract
.github/                      # observation: CI
pyproject.toml                # observation: ruff, mypy, pytest
docs/

  (future) src/observation/
    logging.py                # structured logs, session_id correlation
    health.py                 # readiness probes
    metrics.py                # pipeline counters
```

### Текущее vs целевое (кратко)

| Сейчас | Цель |
|--------|------|
| `src/use_cases/repositories.py` — SQLAlchemy внутри | Protocol в `use_cases/repositories/`; реализация в `infrastructure/db/sqlalchemy_repositories.py` |
| `src/use_cases/ports.py` — Protocol + `TelegramProviderV1` | Protocol в `use_cases/ports/`; реализация в `infrastructure/providers/telegram_provider.py` |
| `src/presentation/` — пустой дубль | удалить; GUI в `application/gui/` |
| `src/application/bootstrap.py` — composition root не на месте | перенести в `infrastructure/bootstrap.py` + `facade.py` |
| нет `infrastructure/facade.py` | `BackupFacade` — единая точка входа для application |
| [`src/domain/`](../src/domain/) — отдельный top-level пакет | перенести в `use_cases/domain/`; удалить `src/domain/` |
| нет `use_cases/domain/mappers.py` | мапперы record ↔ domain в `use_cases/domain/mappers.py` |
| нет use case-классов | `use_cases/backup/`, `restore/`, `session/` |

---

## 4) Порты и реализации

**Порт** — контракт в `use_cases` (`Protocol` + `@dataclass` frozen use case с инжектом). **Реализация** — класс в `infrastructure`, который этот Protocol выполняет.

### Граница persistence (почему infrastructure не трогает domain)

Репозитории в `use_cases` оперируют **persistence-записями** (`SessionRecord`, …), а не доменными `Session`. Use case внутри себя:

1. читает `SessionRecord` из репозитория;
2. маппит в `Session` через **`use_cases/domain/mappers.py`** (`from use_cases.domain.models import Session`);
3. применяет бизнес-правила;
4. маппит обратно в `SessionRecord` и сохраняет.

`infrastructure/db/sqlalchemy_repositories.py` знает только `use_cases.persistence` и ORM-строки. **Импорт `use_cases.domain` в `infrastructure` запрещён.**

```mermaid
flowchart LR
  ORM[ORM Row] -->|"infra mappers"| Record[use_cases.persistence.Record]
  Record -->|"use_cases/domain/mappers"| Entity[use_cases.domain.Session]
  Entity -->|"use_cases/domain/mappers"| Record
  Record -->|"infra mappers"| ORM
```

### Текущие нарушения (технический долг)

| Сейчас (нарушение) | Целевое размещение |
|--------------------|-------------------|
| [`src/use_cases/repositories.py`](../src/use_cases/repositories.py) импортирует `infrastructure.db.*`, `sqlalchemy` | Protocol → `use_cases/repositories/`; SQLAlchemy → `infrastructure/db/sqlalchemy_repositories.py` |
| [`src/use_cases/ports.py`](../src/use_cases/ports.py) содержит `TelegramProviderV1` с HTTP | Protocol → `use_cases/ports/storage_provider.py`; HTTP → `infrastructure/providers/telegram_provider.py` |
| [`src/infrastructure/db/repositories.py`](../src/infrastructure/db/repositories.py) re-export из `use_cases` | Удалить инверсию: infrastructure **реализует**, не импортирует реализацию из мозга |
| [`src/infrastructure/providers/telegram_provider.py`](../src/infrastructure/providers/telegram_provider.py) re-export из `use_cases` | Полная реализация только в infrastructure |

### Целевой поток: «забэкапить файл»

```mermaid
sequenceDiagram
  participant GUI as application_gui
  participant Receiver as backend_receiver
  participant Facade as infrastructure_BackupFacade
  participant UC as use_cases_EnqueueUseCase
  participant Q as Celery_Redis
  participant W as infrastructure_worker
  participant DB as infrastructure_SqlAlchemyRepos
  participant Zip as infrastructure_SevenZip
  participant TG as infrastructure_TelegramProvider

  GUI->>Receiver: user clicked Add file
  Receiver->>Facade: enqueue_file(session_id, path, display_name)
  Facade->>UC: EnqueueSourceItemUseCase.execute()
  UC->>DB: source_items.add(record)
  UC->>Q: enqueue_archive via TaskQueuePort
  Q->>W: archive queue
  W->>Facade: process_archive(source_item_id)
  Facade->>UC: ProcessArchiveVolumeUseCase.execute()
  UC->>Zip: archive via ArchiveServicePort
  UC->>DB: archive_volumes.add(records)
  UC->>Q: enqueue_upload via TaskQueuePort
  Q->>W: upload queue
  W->>Facade: process_upload(volume_id)
  Facade->>UC: ProcessUploadVolumeUseCase.execute()
  UC->>TG: upload_file via StorageProviderPort
  UC->>DB: archive_volumes.update(metadata)
  UC->>Q: enqueue_cleanup via TaskQueuePort
  Facade-->>Receiver: EnqueueResultDTO
  Receiver-->>GUI: update queue view
```

`application` знает только `BackupFacade` и UI-DTO.  
`infrastructure/facade.py` — wiring + вызов use cases.  
`use_cases` знает `use_cases.domain` + persistence-записи + Protocol.  
Worker (`tasks.py`) — тот же `BackupFacade`, без участия `application`.

### Пример wiring (composition root)

```python
# infrastructure/bootstrap.py — единственное место склейки
def build_facade(cfg: AppConfig) -> BackupFacade:
    repos = SqlAlchemyRepositories.from_dsn(cfg.postgres_dsn)
    provider = TelegramProviderV1(bot_token=..., base_url=...)
    task_queue = CeleryTaskQueue()
    return BackupFacade(
        enqueue_source_item=EnqueueSourceItemUseCase(
            source_items=repos.source_items,
            task_queue=task_queue,
        ),
        process_archive=ProcessArchiveVolumeUseCase(...),
        # ...
    )
```

---

## 5) Слой `observation` — идеи

Observation не заменяет бизнес-логику: он **следит**, что система жива, предсказуема и проверяема.

### A. Базовый уровень (уже в репозитории)

| Инструмент | Назначение |
|------------|------------|
| `pytest` | unit (`use_cases.domain`, `use_cases` с фейками портов), integration (БД, Celery), contract (`StorageProviderPort`) |
| `ruff` | стиль, очевидные ошибки |
| `mypy` | типы на границах слоёв |
| `import-linter` (roadmap) | автозапрет: `application → use_cases`, `infrastructure → use_cases.domain`, `use_cases → infrastructure/application` в CI |

### B. Операционное наблюдение (v1 roadmap)

- Структурированные логи с `session_id` / `task_id` — см. [IMPLEMENTATION_GUIDE §9](../IMPLEMENTATION_GUIDE.md): `logs/sessions/<session_id>/`
- Health/readiness: PostgreSQL, Redis, `telegram-bot-api`, Celery workers (`archive`, `upload`, `cleanup`, `restore`)
- Счётчики пайплайна: `queued` / `archiving` / `uploading` / `failed` — для GUI (ETA, прогресс)
- Correlation ID через цепочку Celery-задач (один backup traceable end-to-end)

### C. Кибернетика / контроль (post-v1)

- Dead-letter и dashboard упавших Celery-задач
- Метрики rate-limit и retry по провайдеру
- Алерты на рост очереди `upload` или заполнение `ARCHIVE_CACHE_DIR`
- Audit log в БД: кто/когда enqueue, restore, смена статуса
- Периодический smoke провайдера (см. [IMPLEMENTATION_GUIDE §10](../IMPLEMENTATION_GUIDE.md) — live Telegram verification)

### Физическое размещение

| Сейчас | Позже |
|--------|-------|
| `tests/`, `pyproject.toml`, `.github/` | `src/observation/logging.py`, `health.py`, `metrics.py` |

Модули в `observation/` **без бизнес-правил** — только формат логов, пробы, счётчики.

---

## 6) Технологический стек и runtime

Слои onion — **логическая** организация кода. Ниже — **физические** сервисы и библиотеки, без которых приложение не работает. Всё перечисленное относится к **infrastructure** и **observation**, кроме вызова постановки задач из `use_cases` через порт.

### Карта: технология → слой → где в репозитории

| Технология | Роль | Слой | Файлы / сервисы |
|------------|------|------|-----------------|
| **Python 3.12+** | язык приложения | все | `pyproject.toml` |
| **PostgreSQL 16** | сессии, очередь `source_item`, тома, restore metadata | infrastructure | `infrastructure/db/`, `docker-compose.yml` → `postgres` |
| **SQLAlchemy 2** + **psycopg** | ORM-доступ к PostgreSQL | infrastructure | `orm.py`, `engine.py`, `sqlalchemy_repositories.py` (цель) |
| **Redis 7** | Celery **broker** и **result backend** | infrastructure (runtime) | `config.redis_url`, `docker-compose.yml` → `redis` |
| **Celery 5** | асинхронный конвейер: archive → upload → cleanup → restore | infrastructure | `infrastructure/worker/celery_app.py`, `tasks.py` |
| **7z** (`p7zip-full`) | шифрование и нарезка томов (`-t7z -mhe=on -v1999m`) | infrastructure | `infrastructure/archive/seven_zip_service.py`, `Dockerfile` |
| **telegram-bot-api** (local) | Bot API для больших файлов (не `api.telegram.org` напрямую) | infrastructure (runtime) | `docker-compose.yml` → `telegram-bot-api`, `TELEGRAM_BOT_API_URL` |
| **HTTP** (`urllib`) | upload/download через `TelegramProviderV1` | infrastructure | `infrastructure/providers/telegram_provider.py` (цель) |
| **Docker Compose** | подъём всего контура локально | observation / ops | `docker-compose.yml`, `Dockerfile` |
| **pytest / ruff / mypy** | качество и регрессии | observation | `tests/`, `pyproject.toml` |

### Celery + Redis — топология воркеров

**Redis** — единая точка: очередь задач и хранение результатов (`redis_url` в [`AppConfig`](../src/infrastructure/config.py)).

**Четыре очереди** (маршруты в [`celery_app.py`](../src/infrastructure/worker/celery_app.py)):

| Очередь | Назначение | Нагрузка |
|---------|------------|----------|
| `archive` | 7z: шифрование, split, запись в `ARCHIVE_CACHE_DIR` | CPU / disk |
| `upload` | отправка тома провайдеру (Telegram `sendDocument`) | network |
| `cleanup` | удаление temp после подтверждённого upload | fast local I/O |
| `restore` | скачивание томов и сборка архива | network |

**Пять процессов-воркеров** в [`docker-compose.yml`](../docker-compose.yml):

| Сервис | Очередь | Concurrency |
|--------|---------|-------------|
| `celery-worker-archive-1` | `archive` | 1 |
| `celery-worker-archive-2` | `archive` | 1 |
| `celery-worker-upload` | `upload` | 1 |
| `celery-worker-cleanup` | `cleanup` | 1 |
| `celery-worker-restore` | `restore` | 1 |

Два воркера на `archive` — чтобы параллельно архивировать разные `source_item`, не блокируя upload другого объекта.

**Задачи** ([`tasks.py`](../src/infrastructure/worker/tasks.py)) — по одной на стадию:

- `archive_volume(source_item_id)` — stub → цель: вызвать use case / `SevenZipService`, записать тома в БД
- `upload_volume(archive_volume_id)` — stub → цель: `StorageProviderPort.upload_file`, сохранить `external_*` в БД
- `cleanup_volume(archive_volume_id)` — stub → цель: удалить файлы из `ARCHIVE_CACHE_DIR`
- `restore_volume(archive_volume_id)` — stub → цель: download + распаковка

**Параллельный конвейер:** архивация `source_item` B может идти одновременно с upload `source_item` A и cleanup уже отправленных томов. Статусы в PostgreSQL — источник истины для GUI.

### Docker Compose — сервисы runtime

| Сервис | Образ / сборка | Зависимости |
|--------|----------------|-------------|
| `app` | Dockerfile → `python -m infrastructure.bootstrap` (цель; сейчас `application.bootstrap` — техдолг) | postgres, redis, telegram-bot-api |
| `celery-worker-*` (×5) | тот же образ, разные `-Q` | redis |
| `postgres` | `postgres:16-alpine` | — |
| `redis` | `redis:7-alpine` | — |
| `telegram-bot-api` | `aiogram/telegram-bot-api` | — |

`infrastructure/bootstrap` проверяет PostgreSQL (миграции) и Redis (`ping`), собирает `BackupFacade`; воркеры стартуют после healthy Redis.

### Кеш архивации (`ARCHIVE_CACHE_DIR`)

Временные артефакты пайплайна (не в git):

```
/tmp/telegram_uploader/          # default; env ARCHIVE_CACHE_DIR
  <source_item_id>/
    raw/                         # тома от 7z; удаляются после копии в outgoing/
    outgoing/                    # тома с hashed именами для upload
    volume_manifest.json
```

Управляется `SevenZipService` + задачи `cleanup`; см. [IMPLEMENTATION_GUIDE](../IMPLEMENTATION_GUIDE.md) и [INTERNAL_SPEC](INTERNAL_SPEC.md).

### Переменные окружения (ключевые)

| Группа | Переменные | Назначение |
|--------|------------|------------|
| PostgreSQL | `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | DSN для SQLAlchemy и миграций |
| Redis | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` | Celery broker/backend |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_API_URL`, `TELEGRAM_TARGET_CHAT_ID`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | провайдер и local Bot API |
| Archive | `ARCHIVE_ENCRYPTION_KEY`, `ARCHIVE_CACHE_DIR` | шифрование 7z и путь кеша |

### Граница onion для Celery

| Правильно | Неправильно |
|-----------|-------------|
| `use_cases` вызывает `TaskQueuePort.enqueue_archive(source_item_id)` | `use_cases` импортирует `celery_app` и `.delay()` |
| `infrastructure/worker/tasks.py` — тонкий entrypoint: поднять DI, вызвать use case | бизнес-правила ретраев и смены статусов прямо в `tasks.py` |
| `application` читает статусы через `BackupFacade.get_progress()` | GUI опрашивает Redis или `use_cases` напрямую |

**Целевой порт (roadmap):** `TaskQueuePort` в `use_cases/ports/`; реализация `CeleryTaskQueue` в `infrastructure/worker/`.

**Готовность:** Celery + Redis + compose + маршрутизация очередей — **есть**; задачи — **заглушки**; wiring use cases ↔ worker — **нет**.

---

## 7) Чеклист миграции кода (будущий рефакторинг)

Документ описывает цель; перенос кода — отдельные задачи.

- [ ] Перенести [`src/domain/models.py`](../src/domain/models.py) → `use_cases/domain/models.py`; удалить пакет `src/domain/`
- [ ] Ввести `use_cases/persistence.py` + `use_cases/domain/mappers.py` (record ↔ domain); доменные модели только в `use_cases/domain/`
- [ ] Разрезать [`src/use_cases/repositories.py`](../src/use_cases/repositories.py) → Protocol в `use_cases/repositories/` + реализация в `infrastructure/db/sqlalchemy_repositories.py`
- [ ] Перенести `infrastructure/db/mappers.py` на ORM ↔ persistence-запись; убрать любой `import domain` из `infrastructure`
- [ ] Разрезать [`src/use_cases/ports.py`](../src/use_cases/ports.py) → Protocol в `use_cases/ports/` + `TelegramProviderV1` в `infrastructure/providers/telegram_provider.py`
- [ ] Ввести use case-классы (`EnqueueSourceItemUseCase`, `RestoreSessionUseCase`, …) с DI через `@dataclass`
- [ ] Создать [`src/infrastructure/bootstrap.py`](../src/infrastructure/bootstrap.py) + [`src/infrastructure/facade.py`](../src/infrastructure/facade.py) — composition root и `BackupFacade`
- [ ] Перенести код из [`src/application/bootstrap.py`](../src/application/bootstrap.py) → `infrastructure/bootstrap.py`; удалить `application/bootstrap.py`
- [ ] Обновить `docker-compose`: `python -m infrastructure.bootstrap`
- [ ] `backend_receiver` вызывает только `infrastructure.facade` (не `use_cases`)
- [ ] Удалить [`src/presentation/`](../src/presentation/), перенести GUI в `application/gui/`
- [ ] Добавить `import-linter` (контракт слоёв в CI)
- [ ] Синхронизировать [IMPLEMENTATION_GUIDE.md §2.1](../IMPLEMENTATION_GUIDE.md) после рефакторинга
- [ ] Ввести `TaskQueuePort` в `use_cases`; реализация `CeleryTaskQueue` в `infrastructure/worker/`
- [ ] Подключить `tasks.py` к use cases и репозиториям (убрать stub-ответы)
- [ ] Настроить retry/backoff и idempotency в worker (без переноса правил в `tasks` — политика в `use_cases`)

---

## 8) Иерархия документов

| Документ | Вопрос, на который отвечает |
|----------|----------------------------|
| [docs/INTERNAL_SPEC.md](INTERNAL_SPEC.md) | **Что** обязано делать продукт (шифрование, `display_name`, English UI) |
| **docs/ONION_ARCHITECTURE.md** (этот файл) | **Как** устроены слои, папки, зависимости |
| [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) | **В каком порядке** внедрять и что в roadmap |
| [STEP_BY_STEP_IMPLEMENTATION_GUIDE.md](../STEP_BY_STEP_IMPLEMENTATION_GUIDE.md) | **Пошаговые чекпоинты** сборки с нуля |
| [ONION_LAYER_IMPLEMENTATION.md](ONION_LAYER_IMPLEMENTATION.md) | **Пошаговая имплементация по слоям** onion (фаза → тесты → verify) |

---

**При расхождении между IMPLEMENTATION_GUIDE и этим документом по слоям, папкам и импортам — приоритет у `docs/ONION_ARCHITECTURE.md`.**
