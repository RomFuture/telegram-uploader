# Подключение Telegram Client API

> **TODO (backlog):** сделать эту инструкцию «нативной» для пользователей без опыта в терминале — пошагово с картинками, простым языком, минимум команд. См. [BACKLOG.md — Client API setup guide (beginner-friendly)](BACKLOG.md).

Client API (Telethon, пользовательская сессия) нужен для **загрузки архивов** и **Restore**. Без авторизации workers создадут 7z, но upload в Telegram упадёт — файлы «пропадут» из очереди или останутся в статусе failed.

---

## Что понадобится

| Шаг | Где взять |
|-----|-----------|
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | [my.telegram.org](https://my.telegram.org) → API development tools |
| `TELEGRAM_TARGET_CHAT_ID` | ID private-группы для бэкапов |
| `TELEGRAM_SESSION_PATH` | Путь к файлу сессии Telethon (например `/tmp/telegram_uploader/session.session`) |
| Аккаунт Telegram | Ваш номер телефона (не бот) |

---

## 1. Заполните `.env`

```bash
cp .env.example .env
```

Минимум для Client API:

```env
TELEGRAM_PROVIDER=client
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_TARGET_CHAT_ID=-1001234567890
TELEGRAM_SESSION_PATH=/tmp/telegram_uploader/session.session
TELEGRAM_SESSION_DIR=/tmp/telegram_uploader
```

`TELEGRAM_SESSION_DIR` — каталог на хосте, который Docker workers монтируют как `/data/telegram` (файл сессии = `$DIR/session.session`).

Создайте каталог для сессии:

```bash
mkdir -p /tmp/telegram_uploader
```

---

## 2. Группа для бэкапов

1. Создайте **private group** в Telegram.
2. Войдите в неё **тем же аккаунтом**, который будете авторизовать в шаге 3.
3. Узнайте chat id (forward сообщения из группы в [@userinfobot](https://t.me/userinfobot)).
4. Запишите id в `TELEGRAM_TARGET_CHAT_ID`.

---

## 3. Одноразовая авторизация (phone login)

Из **корня репозитория** (папка `telegram-uploader`, где лежит `scripts/`):

```bash
mkdir -p /tmp/telegram_uploader
PYTHONPATH=src .venv/bin/python scripts/telegram_client_spike.py --login-only
```

Скрипт:

1. При первом запуске Telethon спросит **номер телефона**, **код из Telegram**, при необходимости **2FA-пароль**.
2. Сохранит сессию в `TELEGRAM_SESSION_PATH` из `.env`.
3. Проверит доступ к группе (`TELEGRAM_TARGET_CHAT_ID`).

Успех: в конце строка `Login OK — session saved to ...`.

**Не копируйте** пути вида `/path/to/file` из примеров — это не настоящие файлы.

Опционально — полный тест upload+download (создаём **реальный** файл):

```bash
echo 'telegram-uploader test' > /tmp/telegram_uploader/spike-test.bin
PYTHONPATH=src .venv/bin/python scripts/telegram_client_spike.py /tmp/telegram_uploader/spike-test.bin
```

Успех: `round-trip OK`.

---

## 4. Docker workers и общая сессия (bind mount)

Workers читают **тот же файл сессии**, что spike и GUI — через bind mount каталога `TELEGRAM_SESSION_DIR`:

| Где | Путь к сессии |
|-----|----------------|
| Host (GUI, spike) | `TELEGRAM_SESSION_PATH` из `.env` (например `/tmp/telegram_uploader/session.session`) |
| Container (workers) | `/data/telegram/session.session` (= `$TELEGRAM_SESSION_DIR/session.session` на хосте) |

После `--login-only` на хосте workers сразу видят сессию — **docker cp не нужен**.

Проверка:

```bash
docker compose up -d
ls -la /tmp/telegram_uploader/session.session
docker compose exec celery-worker-upload ls -la /data/telegram/
```

**Fallback** (если bind mount недоступен, например remote Docker):

```bash
docker cp /tmp/telegram_uploader/session.session \
  telegram-uploader-celery-worker-upload-1:/data/telegram/session.session
docker compose restart celery-worker-upload celery-worker-archive-1 celery-worker-archive-2
```

---

## 5. Проверка из GUI

1. `./scripts/run.sh`
2. **Settings → Client API** — api id, hash, session path совпадают с `.env`
3. **Test Client API** — загружает `docs/refactor/README.md` в backup-группу (проверка auth + chat id)
4. **Create db** или **Unlock**
5. **Add File** → **Start Backup**
6. В drawer должно быть `Enqueued 1 item(s)` (не 0); файл **остаётся в списке** папки (Refresh)
7. **Refresh** — статус `uploading` → `completed`
8. **Restore Session** — без ошибки preflight

---

## Типичные проблемы

| Симптом | Решение |
|---------|---------|
| Restore: «Telegram upload did not finish» | Upload worker не записал ref — проверьте `TELEGRAM_SESSION_DIR`, chat id, **Test Client API**, логи `docker compose logs celery-worker-upload` |
| Restore: «Telegram Client API is not ready» | Нет session file или нет доступа к группе — `--login-only`, затем Test Client API |
| Start Backup: «Enqueued 0 item(s)» | Файл уже обработан (failed/completed) или в **другой папке** sidebar — переключите папку или Refresh |
| Файл «пропал» из списка | Исправлено в коде (folder_id); Refresh — unassigned items видны с подсказкой в статусной строке |
| Workers не видят `.env` | Перезапустите `docker compose` после правок `.env` |
| `file not found: /path/to/...` | Скопирован placeholder из docs — используйте `--login-only` (шаг 3) |

---

## Связанные документы

- [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) — общий setup и compose
- [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md) — архитектура provider
