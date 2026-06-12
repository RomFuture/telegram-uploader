# Telegram setup (Client API default)

Manual steps to wire **telegram-uploader** to Telegram before the first backup. **Client API** (Telethon user session) is the default provider — required for reliable **Restore**. Bot API remains optional (`TELEGRAM_PROVIDER=bot` + `docker compose --profile bot`).

---

## What you need

| Item | Where it goes |
|------|----------------|
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_TARGET_CHAT_ID` | Private group where volumes are stored |
| `TELEGRAM_SESSION_PATH` | Path to Telethon session file (host + Docker volume) |
| `TELEGRAM_PROVIDER` | `client` (default) or `bot` for legacy Bot API |
| `TELEGRAM_BOT_TOKEN` | Only if `TELEGRAM_PROVIDER=bot` — [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_BOT_API_URL` | `http://localhost:8081` when using Bot API profile |

Copy the template and edit:

```bash
cp .env.example .env
```

---

## 1. API id and hash

1. Open [my.telegram.org](https://my.telegram.org) and sign in with your phone number.
2. Open **API development tools**.
3. Create an app (any title and short name).
4. Copy **api_id** and **api_hash** into `.env`:

```env
TELEGRAM_PROVIDER=client
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_SESSION_PATH=/tmp/telegram_uploader/session.session
```

---

## 2. Backup group and chat id

All archive volumes upload to **one private group**. Your Telegram user (Client API session) must be a member with permission to send files.

1. Create a **private group** (v1 does not use Telegram topics / threads).
2. Join the group with the account you will authenticate in step 3.
3. Send any message in the group.
4. Resolve `TELEGRAM_TARGET_CHAT_ID`:

**Option A — forward to a helper bot**

Forward a message from the group to [@userinfobot](https://t.me/userinfobot) or [@RawDataBot](https://t.me/RawDataBot). Use the numeric **chat id** (supergroups often start with `-100`).

**Option B — `getUpdates` (Bot API profile only)**

If you use the optional bot profile, after posting in the group:

```bash
curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates" | python3 -m json.tool
```

```env
TELEGRAM_TARGET_CHAT_ID=-1001234567890
```

---

## 3. Authenticate Client API (once)

**Подробная инструкция:** [CLIENT_API_SETUP.md](CLIENT_API_SETUP.md)

Run the spike script on the **host** (interactive phone login). No test file needed:

```bash
mkdir -p /tmp/telegram_uploader
PYTHONPATH=src .venv/bin/python scripts/telegram_client_spike.py --login-only
```

Success: `Login OK — session saved to ...`. Full steps: [CLIENT_API_SETUP.md](CLIENT_API_SETUP.md).

---

## 4. Finish `.env`

Minimum keys for Client API:

| Variable | Notes |
|----------|--------|
| `TELEGRAM_PROVIDER` | `client` (default) |
| `TELEGRAM_API_ID` | From my.telegram.org |
| `TELEGRAM_API_HASH` | From my.telegram.org |
| `TELEGRAM_TARGET_CHAT_ID` | Numeric group id |
| `TELEGRAM_SESSION_PATH` | Host path to `.session` file |

Other keys from `.env.example`:

| Variable | Notes |
|----------|--------|
| `POSTGRES_PORT` | `5433` on the host if port 5432 is already taken |
| `HOST_SOURCE_MOUNT` | Default `$HOME`; files to back up must live under this path for Docker workers |
| `ARCHIVE_ENCRYPTION_KEY` | Optional default; Create db / Unlock use per-database keys in the GUI |

Workers use `TELEGRAM_SESSION_PATH=/data/telegram/session.session` inside Docker (see `docker-compose.yml`).

### Optional: Bot API profile

For legacy uploads without user session:

```bash
# .env
TELEGRAM_PROVIDER=bot
TELEGRAM_BOT_TOKEN=...

docker compose --profile bot up -d
```

Bot API backups **cannot be restored** through the app (HTTP 404). Re-backup with Client API after switching.

---

## 5. Verify stack

From the repo root:

```bash
docker compose up -d
docker compose ps
```

`postgres` and `redis` should be healthy. Then:

```bash
./scripts/run.sh
```

Or open only the GUI if containers already run:

```bash
PYTHONPATH=src .venv/bin/python -m application.gui
```

---

## 6. First backup and restore

1. **Unlock** or **Create db** in the GUI (database name + encryption key).
2. **Add File** → pick a file under `$HOME` → choose folder → set **display name**.
3. **Start Backup** → **Refresh Progress**.
4. Open the target group: expect `your-display-name.7z.001` (more parts if the archive is large).
5. **Restore Session** → pick destination folder → files extract with your database encryption key.

Worker logs:

```bash
docker compose logs -f celery-worker-archive-1
docker compose logs -f celery-worker-upload
```

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Restore unavailable / legacy volumes | Old Bot API backups; set `TELEGRAM_PROVIDER=client` and re-backup |
| Client API not ready | Run `scripts/telegram_client_spike.py`; check `TELEGRAM_SESSION_PATH` |
| Upload fails in Docker | Session volume mounted; same chat id in `.env` |
| File not found in worker | Source path must be under `HOST_SOURCE_MOUNT` (default `$HOME`) |
| `telegram-bot-api` fails | Only needed for `--profile bot`; Client API default skips it |
| RAM spikes during archive | Settings shows RAM slider (placeholder); reduce archive workers in compose if needed |

---

## Related docs

| Doc | Topic |
|-----|--------|
| [CLIENT_API_SETUP.md](CLIENT_API_SETUP.md) | Пошаговое подключение Client API (phone login, spike, Docker) |
| [PROJECT.md](PROJECT.md) | Run, verify, packaging |
| [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md) | Bot API → MTProto user session |
| [INTERNAL_SPEC.md](INTERNAL_SPEC.md) | Encryption, `display_name`, no topics |
