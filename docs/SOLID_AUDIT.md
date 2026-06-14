# SOLID-аудит telegram-uploader

> **Дата:** 2026-06-13  
> **Область:** весь `src/` (~103 Python-модуля): `domain`, `use_cases`, `infrastructure`, `application`, `observation`  
> **Контекст:** [PROJECT.md §4](PROJECT.md#4-архитектура) (hexagonal / ports & adapters), `.importlinter`, рефактор R2–R8 (2026-06)

**Содержание:** [Резюме](#резюме) · [Методология](#методология) · [Паттерны](#паттерны-в-проекте) · [S](#s--single-responsibility) · [O](#o--openclosed) · [L](#l--liskov-substitution) · [I](#i--interface-segregation) · [D](#d--dependency-inversion) · [Границы слоёв](#границы-слоёв) · [По слоям](#аудит-по-слоям) · [Приоритеты](#приоритеты-улучшений) · [Связанные docs](#связанные-docs)

---

## Резюме

Проект **осознанно следует hexagonal architecture** и после рефакторинга UC-1…UC-8 **в целом соответствует SOLID**. Сильнейшие стороны — **Dependency Inversion** (порты, composition root, изоляция `use_cases`) и **Open/Closed** для смены Telegram-провайдера. Основной технический долг — **вес адаптеров** (GUI, entrypoints), **bundle `Repositories`**, **runtime re-wiring в Celery tasks** и **смешение presentation-логики в use cases**.

| Принцип | Оценка | Одной строкой |
|---------|--------|---------------|
| **S** Single Responsibility | **72%** | Мелкие UC и чистый `domain`; толстые `app.py`, preflight-сообщения в UC |
| **O** Open/Closed | **68%** | Порты для storage/archive; новая фича = правки entrypoint + bootstrap |
| **L** Liskov Substitution | **75%** | Protocol-реализации работают; асимметрия bot/client и legacy refs |
| **I** Interface Segregation | **70%** | Репозитории по сущностям; bundle + fat entrypoints |
| **D** Dependency Inversion | **78%** | UC → абстракции; утечки `application`/`observation` → `infrastructure` |
| **Итого** | **~73%** | Зрелый pet-проект с enforced import boundaries, не bigtech-монолит |

```mermaid
quadrantChart
    title SOLID по принципам (%)
    x-axis "Слабее" --> "Сильнее"
    y-axis ""
    quadrant-1 ""
    quadrant-2 ""
    quadrant-3 ""
    quadrant-4 ""
    D Dependency Inversion: [0.78, 0.5]
    L Liskov Substitution: [0.75, 0.5]
    S Single Responsibility: [0.72, 0.5]
    I Interface Segregation: [0.70, 0.5]
    O Open Closed: [0.68, 0.5]
```

Оценки субъективны: «сколько типичных нарушений принципа компенсируется архитектурными решениями». Не блокер для релиза; ориентир для следующих PR.

---

## Методология

1. **Обход всех слоёв** — чтение ключевых модулей и grep по импортам.
2. **Сверка с каноном** — [PROJECT.md §4.3](PROJECT.md#43-правила-зависимостей-целевые) (правила зависимостей).
3. **Проверка контрактов** — `.importlinter` (5 contracts: `domain-isolated`, `use-cases-isolated`, `infrastructure-no-domain`, `application-public-api`, + ignores для `gui/__main__.py`).
4. **Критерии оценки** — не «идеальный учебник», а **практичность для desktop app + Celery workers + один разработчик**.

---

## Паттерны в проекте

| Паттерн | Где | Зачем (SOLID) |
|---------|-----|---------------|
| `Protocol` ports | `use_cases/shared/ports/`, `repositories/` | **D**, **I** — UC зависит от контракта |
| Frozen dataclass UC | `use_cases/**/**.py` | **S** — один сценарий, deps через поля |
| Entrypoints | `use_cases/public/gui_entrypoint.py`, `celery_entrypoint.py` | Facade для адаптеров; **O** через делегирование |
| Commands / Results | `use_cases/public/commands.py`, `results.py` | Граница API; GUI не видит domain |
| Persistence Records | `use_cases/shared/persistence.py` | Разделение ORM и domain (**S** persistence vs domain) |
| Composition root | `infrastructure/bootstrap.py` | **D** — единственное место wiring |
| Adapter | `infrastructure/archive/archive_service_adapter.py` | **O** — 7z за портом `ArchiveServicePort` |
| Null object | `unconfigured_storage_provider.py` | Graceful degrade без падения bootstrap |
| Application DTO | `application/backend_receiver.py` | **S** — перевод Result → ViewDTO для Tkinter |

---

## S — Single Responsibility

**Оценка: 72%**

### ✅ Хорошо

| Модуль | Ответственность |
|--------|-----------------|
| `domain/models.py`, `actions.py`, `errors.py` | Сущности, переходы статусов, фабрики ошибок — без I/O |
| `use_cases/backup/gates.py` | Guards «шаг только при статусе X» |
| `use_cases/backup/idempotency.py` | Политика retry отдельно от pipeline |
| `use_cases/restore/refs.py`, `scope.py` | Выбор restorable refs и folder scope |
| `use_cases/backup/report_failure.py` | Три маленьких UC на failure reporting |
| `use_cases/telegram/verify_storage_provider.py` | Round-trip test провайдера |
| `use_cases/session/unlock_session.py` | Только unlock по profile + key |

Пример узкого UC:

```12:22:src/use_cases/session/unlock_session.py
@dataclass(frozen=True, slots=True)
class UnlockSessionUseCase:
    sessions: SessionRepository

    def execute(self, profile_name: str, encryption_key: str) -> Session:
        record = self.sessions.find_by_profile_name(profile_name.strip())
        if record is None:
            raise domain.DomainError.session_not_found_by_profile(profile_name.strip())
        ...
```

### ⚠️ Нарушения и размытие

| Модуль | ~строк | Проблема |
|--------|--------|----------|
| `application/gui/app.py` | 470 | **God object**: unlock, explorer, backup, restore (threading + UI ticks), settings, queue refresh |
| `application/gui/telegram_login.py` | 331 | UI + Telethon sign-in + env + subprocess fallback |
| `application/backend_receiver.py` | ~246 | Mapper UC↔DTO **и** Client API pre-validation (`test_client_api`) |
| `use_cases/restore/check_restore_ready.py` | 146 | Preflight-логика **+** GUI copy (`docker compose logs`, пути Settings) |
| `use_cases/session/get_session_queue_snapshot.py` | 85 | Snapshot UC **+** `Path.stat()`, форматирование размера/даты |
| `infrastructure/providers/telegram_*.py` | ~220 each | HTTP/Telethon + multipart + classify + limits в одном классе |
| `infrastructure/worker/tasks.py` | 133 | Celery task **+** retry routing по строке `stage` |
| `use_cases/session/create.py` | — | Три create-UC в одном файле (мелкий nit) |

GUI-текст в use case (нарушение границы presentation):

```19:34:src/use_cases/restore/check_restore_ready.py
_STALE_BACKUP_MESSAGE = (
    "No restorable backups yet.\n\n"
    ...
    "Worker logs: docker compose logs celery-worker-upload"
)
```

Filesystem I/O в UC «для таблицы GUI»:

```34:38:src/use_cases/session/get_session_queue_snapshot.py
def read_item_size_label(source_path: str) -> str:
    path = Path(source_path)
    if not path.is_file():
        return _MISSING_LABEL
    return format_bytes_as_size_label(path.stat().st_size)
```

**Вывод:** на уровне **модулей pipeline UC** S соблюдён хорошо; основной долг — **application layer** и **UX-текст / filesystem в use_cases**.

---

## O — Open/Closed

**Оценка: 68%**

### ✅ Расширение без правки UC

| Точка расширения | Как добавить |
|------------------|--------------|
| **Storage provider** | Новый класс с 6 методами `StorageProviderPort`; регистрация в `build_storage_provider()` |
| **Archive backend** | Новый adapter за `ArchiveServicePort` (как `ArchiveServiceAdapter`) |
| **DB backend** | Новый bundle репозиториев, реализующий Protocol |
| **Misconfigured env** | `UnconfiguredStorageProvider` — без падения wiring |

```53:67:src/infrastructure/bootstrap.py
def build_storage_provider(cfg: AppConfig) -> StorageProviderPort:
    if cfg.telegram_provider == "client":
        ...
        return TelegramClientProvider(...)
    ...
    return TelegramProviderV1(...)
```

Use cases (`ProcessUploadVolumeUseCase`, `CheckRestoreReadyUseCase`, …) **не знают** bot vs client — классический OCP.

### ⚠️ Закрыто для расширения «из коробки»

| Сценарий | Что править |
|----------|-------------|
| Новый stage pipeline | `TaskQueuePort`, `CeleryTaskQueue`, `tasks.py`, `CeleryEntrypoint`, `wire_celery_entrypoint()` |
| Новая GUI-операция | `GuiEntrypoint`, `commands.py`, `BackendReceiver`, `bootstrap`, часто `app.py` |
| Новый режим provider | if/elif в `build_storage_provider()` (нет registry) |
| Failure routing | `tasks._run_with_failure_report()` — switch по `stage: str` |
| Restore UX-сообщения | константы в `check_restore_ready.py` |

**Вывод:** **OCP силён для провайдеров и persistence**; **слаб для product features** (entrypoints растут линейно).

---

## L — Liskov Substitution

**Оценка: 75%**

### ✅ Подстановка работает

| Protocol | Реализации |
|----------|------------|
| `StorageProviderPort` | `TelegramProviderV1`, `TelegramClientProvider`, `UnconfiguredStorageProvider` |
| `ArchiveServicePort` | `ArchiveServiceAdapter` → `SevenZipService` |
| `*Repository` | `SqlAlchemy*Repository` (structural typing) |
| `TaskQueuePort` | `CeleryTaskQueue` |

UC вызывают методы порта, не проверяя конкретный класс.

### ⚠️ Оговорки

| Место | Риск |
|-------|------|
| `UnconfiguredStorageProvider` | `healthcheck` → `False`; upload/download **raise** — разные контракты «мягкий» vs «жёсткий» fail |
| `TelegramClientProvider` | `download_file(resume=True)` raises; `supports_resume_download=False` — честно, но не симметрично bot |
| `restore/refs.py` | Legacy bot refs не restorable — **провайдеры не взаимозаменяемы для restore**, только для upload |
| `CeleryEntrypoint.report_cleanup_failure_for_volume` | Доступ к `process_cleanup_uc.archive_volumes` — entrypoint знает внутренности UC |

```49:51:src/use_cases/public/celery_entrypoint.py
    def report_cleanup_failure_for_volume(self, archive_volume_id: UUID) -> None:
        volume = self.process_cleanup_uc.archive_volumes.require(archive_volume_id)
        self.report_cleanup_failure(volume.source_item_id)
```

**Вывод:** для **happy path** LSP OK; для **edge cases и legacy migration** — документированная асимметрия, не баг типизации.

---

## I — Interface Segregation

**Оценка: 70%**

### ✅ Узкие интерфейсы

- Репозитории по сущности: `SessionRepository` (6 методов), `FolderRepository` (4), …
- `VerifyStorageProviderUseCase` использует подмножество `StorageProviderPort` (healthcheck, upload, download)
- `TaskQueuePort` — 4 метода, только enqueue

### ⚠️ «Толстые» поверхности

| Интерфейс | Проблема |
|-----------|----------|
| `Repositories` bundle | 4 репозитория одним объектом — UC получает больше, чем нужно |
| `StartBackupPipelineUseCase` | `repos: Repositories` — использует 3 из 4 |
| `ArchiveVolumeRepository` | Record-методы **и** domain-методы (`list_domain_by_*`, `require_for_session`) |
| `SourceItemRepository` | `list_by_session` vs `list_domain_by_session` — два API для одной сущности |
| `StorageProviderPort` | 6 методов; `classify_error` / `provider_limits` не у всех UC |
| `GuiEntrypoint` | 14 injected UC — широкая зависимость GUI-адаптера |
| `BackendReceiver` | 1:1 pass-through ко всем методам entrypoint |

```17:23:src/use_cases/shared/repositories/__init__.py
class Repositories(Protocol):
    sessions: SessionRepository
    folders: FolderRepository
    source_items: SourceItemRepository
    archive_volumes: ArchiveVolumeRepository
```

**Вывод:** **ISP на уровне репозиториев хороший**; bundle и entrypoints — **осознанный компромисс** для wiring, но не ideal ISP.

---

## D — Dependency Inversion

**Оценка: 78%** — **лучшая сторона проекта**

### ✅ Инверсия соблюдена

```
GUI → BackendReceiver → GuiEntrypoint → UseCase → Protocol ← Infrastructure impl
                                                      ↑
                                            bootstrap.py (composition root)
```

| Факт | Доказательство |
|------|----------------|
| `use_cases` без `infrastructure` | grep: 0 импортов |
| UC зависят от Protocol | `StorageProviderPort`, `*Repository`, `TaskQueuePort` |
| Domain изолирован | `.importlinter` contract `domain-isolated` |
| GUI без domain | `application` не импортирует `domain` |
| Infra без domain (direct) | ORM → Record → mapper → domain |

Пример:

```22:29:src/use_cases/backup/process_upload_volume.py
@dataclass(frozen=True, slots=True)
class ProcessUploadVolumeUseCase:
    source_items: SourceItemRepository
    archive_volumes: ArchiveVolumeRepository
    storage_provider: StorageProviderPort
    task_queue: TaskQueuePort
    remote_target: str
```

### ⚠️ Утечки и запахи

| Файл | Проблема |
|------|----------|
| `infrastructure/worker/tasks.py:20-21` | `wire_celery_entrypoint(load_config())` **на каждый task run** — composition в runtime, не inject |
| `observation/health.py` | Прямые импорты `bootstrap`, `load_config`, `apply_migrations` — слой не в `.importlinter` |
| `application/env_store.py:9` | `from infrastructure.paths import session_path_for_use` — нарушает PROJECT §4.3 |
| `application/gui/telegram_login.py:24` | То же |
| `application/telegram_login_cli.py:10` | `from infrastructure.config import load_config` |
| `application/gui/__main__.py` | Импорты infra — **явно разрешены** в `.importlinter` ignore |
| `BackendReceiver.build_client_provider` | `Callable[..., object]` — слабая типизация factory |

**Вывод:** **ядро (domain + use_cases) — эталон DIP**; долг на **краях** (observation, env paths, Celery bootstrap per call).

---

## Границы слоёв

Сверка с [PROJECT.md §4.3](PROJECT.md#43-правила-зависимостей-целевые):

| Правило | Статус | Комментарий |
|---------|--------|-------------|
| `use_cases` → no Tkinter/SQLAlchemy/Celery | ✅ Pass | Enforced + grep |
| `application` → no `domain` | ✅ Pass | DTO через `BackendReceiver` |
| `application` → no `infrastructure` | ⚠️ Partial | `env_store`, `telegram_login`, `telegram_login_cli`; `__main__` — ignore |
| `infrastructure` → no `domain` (direct) | ✅ Pass | Через `use_cases.shared` |
| UC без filesystem для UI | ⚠️ Blur | `get_session_queue_snapshot.py` читает `Path.stat()` |
| UC без GUI strings | ⚠️ Blur | `check_restore_ready.py` |
| `observation/` | ⚠️ Uncontracted | Нет в `.importlinter` |

---

## Аудит по слоям

### `domain/` — ✅ exemplary (S, D)

- ~300 строк: models, actions, errors.
- Только stdlib; единая точка входа `import domain as domain`.
- **SOLID:** каждый файл — одна зона ответственности; нулевые внешние зависимости.

### `use_cases/` — ✅ strong (S, D, частично O)

| Пакет | SOLID |
|-------|-------|
| `backup/` | gates + idempotency отделены; pipeline UC сфокусированы |
| `restore/` | `RestoreSessionUseCase` — чистая оркестрация; `check_restore_ready` — S blur |
| `session/` | Мелкие UC; `create.py` — 3 класса в файле |
| `shared/` | ports, records, mappers — чёткая persistence boundary |
| `public/` | Facade; CeleryEntrypoint leak (L/I) |
| `telegram/` | `verify_storage_provider` — хороший S |

### `infrastructure/` — ✅ adapters (D, O для ports)

| Модуль | SOLID |
|--------|-------|
| `bootstrap.py` | Composition root — D; много обязанностей — допустимо для root |
| `db/` | Repo impl; indirect domain через types |
| `providers/` | OCP для storage; классы толстые (S) |
| `worker/` | tasks re-wire — главный DIP smell |
| `archive/` | Thin adapter over 7z |

### `application/` — ⚠️ adapter weight (S, D)

| Модуль | SOLID |
|--------|-------|
| `backend_receiver.py` | Хороший translator; растёт с фичами |
| `gui/app.py` | Главное S-нарушение репозитория |
| `gui/__main__.py` | Composition — by design |

### `observation/` — ⚠️ thin, leaky (D)

- `logging_setup.py` — OK.
- `health.py` — тянет infra напрямую.

---

## Приоритеты улучшений

Ранжировано по impact на SOLID и согласованности с [PROJECT.md §8](PROJECT.md#8-план-рефакторинга). Не блокеры — кандидаты в [BACKLOG.md](BACKLOG.md).

| # | Действие | Принципы | Сложность |
|---|----------|----------|-----------|
| 1 | Разбить `BackupApp` на screen controllers (unlock / explorer / restore) | **S** | M |
| 2 | Вынести preflight-сообщения из `check_restore_ready` в `application` или port `RestorePreflightMessages` | **S**, границы слоёв | S |
| 3 | Форматирование size/modified — из UC в application или `FileMetadataPort` | **S**, **D** | S |
| 4 | Узкие repo-protocols вместо `Repositories` bundle где возможно | **I**, **D** | M |
| 5 | Inject `CeleryEntrypoint` once (worker init) вместо `wire_*` per task | **D** | M |
| 6 | `session_path_for_use` — inject из `__main__`, убрать infra из `env_store` / `telegram_login` | **D**, PROJECT §4.3 | S |
| 7 | `report_cleanup_failure_for_volume` — порт или метод UC, не `.archive_volumes` снаружи | **L**, **I** | S |
| 8 | Provider registry вместо if/elif в `build_storage_provider` | **O** | S |
| 9 | Добавить `observation` в `.importlinter` или health через injected callables | **D** | S |

---

## Связанные docs

| Файл | Связь |
|------|-------|
| [PROJECT.md](PROJECT.md) | Канон архитектуры, правила импортов, план рефакторинга |
| [refactor/CHANGES.md](refactor/CHANGES.md) | Журнал backend PR |
| [refactor/mind.md](refactor/mind.md) | Открытые вопросы по слоям (DTO, list_*, backup/) |
| [BACKLOG.md](BACKLOG.md) | Продуктовый бэклог (не SOLID, но пересекается с GUI polish) |

---

*Аудит выполнен статическим анализом кода и import graph. Для регрессии границ слоёв: `lint-imports` / CI contract UC-8.*
