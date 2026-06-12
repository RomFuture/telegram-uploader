# Подключение Telegram Client API

> **TODO (backlog):** сделать эту инструкцию «нативной» для пользователей без опыта в терминале — пошагово с картинками, простым языком, минимум команд. См. [BACKLOG.md — Client API setup guide (beginner-friendly)](BACKLOG.md).

Client API (Telethon, пользовательская сессия) нужен для **загрузки архивов** и **Restore**. Без авторизации workers создадут 7z, но upload в Telegram упадёт.

---

## Что понадобится

| Шаг | Где взять |
|-----|-----------|
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | [my.telegram.org](https://my.telegram.org) → API development tools |
| `TELEGRAM_TARGET_CHAT_ID` | ID private-группы для бэкапов (`-100…`) |
| `TELEGRAM_SESSION_PATH` | `~/.config/telegram-uploader/session.session` (рекомендуется) |
| Аккаунт Telegram | Ваш номер телефона (не бот) |

---

## Сценарий A: установка из `.deb`

```bash
sudo apt install ./telegram-uploader_<version>_amd64.deb
telegram-uploader --setup
telegram-uploader
```

В GUI:

1. **Settings → Client API** — API ID, API hash (session path можно оставить по умолчанию)
2. **Settings → General** — Target chat ID = id **группы** (`-100…`, не ваш user id)
3. **Save**
4. **Sign in to Telegram…** (диалог в Settings) **или** в терминале:

   ```bash
   telegram-uploader-login
   ```

5. **Test Client API** — тестовый файл должен появиться в группе
6. **Add file → Backup**

Конфиг: `~/.config/telegram-uploader/.env` · Сессия: `~/.config/telegram-uploader/session.session`

Полная инструкция: [README § Clean install](../README.md#clean-install-first-time).

---

## Сценарий B: разработка из git

### 1. Заполните `.env`

```bash
cp .env.example .env
```

Минимум для Client API:

```env
TELEGRAM_PROVIDER=client
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_TARGET_CHAT_ID=-1001234567890
TELEGRAM_SESSION_PATH=~/.config/telegram-uploader/session.session
```

```bash
mkdir -p ~/.config/telegram-uploader
```

### 2. Группа для бэкапов

1. Создайте **private group** в Telegram.
2. Войдите в неё **тем же аккаунтом**, который авторизуете ниже.
3. Узнайте chat id (forward сообщения из группы в [@userinfobot](https://t.me/userinfobot)).

### 3. Авторизация (один раз)

```bash
./scripts/run.sh
```

В GUI: **Settings → Save → Sign in to Telegram…**

Или из терминала:

```bash
PYTHONPATH=src .venv/bin/python -m application.telegram_login_cli
```

Сессия сохраняется в `TELEGRAM_SESSION_PATH`.

### 4. Docker workers и session volume

Workers монтируют каталог сессии с хоста:

| Где | Путь |
|-----|------|
| Host (GUI, login) | `TELEGRAM_SESSION_PATH` из `.env` |
| Container (workers) | `/data/telegram/session.session` |

По умолчанию `docker-compose.yml` монтирует `~/.config/telegram-uploader` → `/data/telegram`. После sign-in на хосте перезапустите workers:

```bash
docker compose restart celery-worker-upload celery-worker-archive-1 celery-worker-archive-2
```

### 5. Проверка

1. **Settings → Test Client API**
2. **Add File** → **Start Backup** → **Refresh**
3. Статус `uploading` → `completed`; файл в Telegram-группе

---

## Типичные проблемы

| Симптом | Решение |
|---------|---------|
| Restore: «Client API is not ready» | Нет session file — пройдите sign-in |
| `phone_code_hash` error | Нажмите Send code снова, введите свежий код |
| Target chat id = user id | Нужен id **группы** (`-100…`), не личный user id |
| Upload fails in worker | Проверьте session volume и `TELEGRAM_TARGET_CHAT_ID` |
| Archive stuck on `archiving` | `docker compose logs celery-worker-archive-1`; обновите до 0.1.9+ |
| Файл не найден в worker | Путь файла должен быть под `HOST_SOURCE_MOUNT` (default `$HOME`) |

---

## Связанные документы

- [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) — общий setup и compose
- [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md) — статус миграции Bot API → Client API
- [releases/v0.1.9.md](releases/v0.1.9.md) — install/upgrade из `.deb`
