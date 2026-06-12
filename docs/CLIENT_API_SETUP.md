# Подключение Telegram Client API

> **TODO (backlog):** сделать эту инструкцию «нативной» для пользователей без опыта в терминале — пошагово с картинками, простым языком, минимум команд. См. [BACKLOG.md — Client API setup guide (beginner-friendly)](BACKLOG.md).

Client API (Telethon, пользовательская сессия) нужен для **загрузки архивов** и **Restore**. Без авторизации workers создадут 7z, но upload в Telegram упадёт — файлы «пропадут» из очереди или останутся в статусе failed.

---

## Что понадобится


| Шаг                                    | Где взять                                                                        |
| -------------------------------------- | -------------------------------------------------------------------------------- |
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | [my.telegram.org](https://my.telegram.org) → API development tools               |
| `TELEGRAM_TARGET_CHAT_ID`              | ID private-группы для бэкапов                                                    |
| `TELEGRAM_SESSION_PATH`                | Путь к файлу сессии Telethon (например `/tmp/telegram_uploader/session.session`) |
| Аккаунт Telegram                       | Ваш номер телефона (не бот)                                                      |


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
```

Создайте каталог для сессии:

```bash
mkdir -p "$(dirname /tmp/telegram_uploader/session.session)"
```

---

## 2. Группа для бэкапов

1. Создайте **private group** в Telegram.
2. Войдите в неё **тем же аккаунтом**, который будете авторизовать в шаге 3.
3. Узнайте chat id (forward сообщения из группы в [@userinfobot](https://t.me/userinfobot)).
4. Запишите id в `TELEGRAM_TARGET_CHAT_ID`.

---

## 3. Одноразовая авторизация (phone login)

Из корня репозитория:

```bash

```

Скрипт:

1. Проверит `healthcheck` (доступ к группе).
2. При первом запуске Telethon спросит **номер телефона**, **код из Telegram**, при необходимости **2FA-пароль**.
3. Сохранит сессию в `TELEGRAM_SESSION_PATH`.
4. Загрузит тестовый файл в группу и скачает обратно.

Успех: в конце `round-trip OK`.

---

## 4. Docker workers и общий volume

Workers в Docker используют тот же session file через volume `telegram-session`:


| Где                 | Путь к сессии                     |
| ------------------- | --------------------------------- |
| Host (GUI, spike)   | `TELEGRAM_SESSION_PATH` из `.env` |
| Container (workers) | `/data/telegram/session.session`  |


**Важно:** после spike на хосте скопируйте сессию в volume или авторизуйтесь с путём, который видят workers:

```bash
docker compose up -d
docker compose exec celery-worker-upload ls -la /data/telegram/
```

Если файла нет — скопируйте с хоста:

```bash
docker cp /tmp/telegram_uploader/session.session \
  telegram-uploader-celery-worker-upload-1:/data/telegram/session.session
```

Перезапустите workers:

```bash
docker compose restart celery-worker-upload celery-worker-archive-1 celery-worker-archive-2
```

---

## 5. Проверка из GUI

1. `./scripts/run.sh`
2. **Settings → Client API** — api id, hash, session path совпадают с `.env`
3. **Create db** или **Unlock**
4. **Add File** → **Start Backup**
5. В drawer должно быть `Enqueued 1 item(s)` (не 0)
6. **Refresh** — статус `uploading` → `completed`
7. **Restore Session** — без ошибки preflight

---

## Типичные проблемы


| Симптом                            | Решение                                                                                              |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Restore: «Backup is not complete»  | Upload не прошёл — нет Client API auth; пройдите шаг 3                                               |
| Restore: «Client API is not ready» | Нет session file или нет доступа к группе                                                            |
| Start Backup: «Enqueued 0 item(s)» | Файл уже обработан (failed/completed) или в **другой папке** sidebar — переключите папку или Refresh |
| Файл «пропал» из списка            | Смотрите другую папку в sidebar; failed items помечены красным после Refresh                         |
| Workers не видят `.env`            | Перезапустите `docker compose` после правок `.env`                                                   |


---

## Связанные документы

- [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) — общий setup и compose
- [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md) — архитектура provider

