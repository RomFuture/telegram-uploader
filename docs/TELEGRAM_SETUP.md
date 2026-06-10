# Telegram setup (v1, Bot API)

Manual steps to wire **telegram-uploader** to Telegram before the first backup. v1 uses a **bot** plus a local **telegram-bot-api** container for large uploads. Restore through the app is unreliable; you may download volumes from the group by hand.

After [Client API migration](TELEGRAM_CLIENT_API_MIGRATION.md), phone login and a user session will replace most of this flow.

---

## What you need

| Item | Where it goes |
|------|----------------|
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | [my.telegram.org](https://my.telegram.org) → powers `telegram-bot-api` in Docker |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_TARGET_CHAT_ID` | Private group where volumes are stored |
| `TELEGRAM_BOT_API_URL` | `http://localhost:8081` (host GUI and default compose) |

Copy the template and edit:

```bash
cp .env.example .env
```

---

## 1. API id and hash

The compose service `telegram-bot-api` needs your Telegram API application credentials.

1. Open [my.telegram.org](https://my.telegram.org) and sign in with your phone number.
2. Open **API development tools**.
3. Create an app (any title and short name).
4. Copy **api_id** and **api_hash** into `.env`:

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
```

These are tied to your Telegram account, not to a specific bot.

---

## 2. Bot token

1. In Telegram, open [@BotFather](https://t.me/BotFather).
2. Send `/newbot`.
3. Choose a **display name** (shown in chats) and a **username** ending in `bot`.
4. Copy the HTTP API token BotFather returns.

```env
TELEGRAM_BOT_TOKEN=123456789:AAH...
```

Keep the token out of git. `.env` is gitignored.

---

## 3. Backup group and chat id

All archive volumes upload to **one group**. The bot must be able to post documents there.

1. Create a **private group** (v1 does not use Telegram topics / threads).
2. Add your bot to the group.
3. Promote the bot to **admin** with permission to send messages and upload files.
4. Send any message in the group so the chat is visible to the Bot API.

### Resolve `TELEGRAM_TARGET_CHAT_ID`

**Option A — forward to a helper bot**

Forward a message from the group to [@userinfobot](https://t.me/userinfobot) or [@RawDataBot](https://t.me/RawDataBot). Use the numeric **chat id** from the reply (supergroups often start with `-100`).

**Option B — `getUpdates`**

After posting in the group, run:

```bash
curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates" | python3 -m json.tool
```

Find `"chat":{"id": ...}` in the JSON. Example:

```env
TELEGRAM_TARGET_CHAT_ID=-1001234567890
```

If the list is empty, message the group again or disable privacy mode for the bot via BotFather (`/setprivacy` → Disable) so group messages appear in updates.

---

## 4. Finish `.env`

Minimum Telegram-related keys:

| Variable | Notes |
|----------|--------|
| `TELEGRAM_BOT_TOKEN` | From BotFather |
| `TELEGRAM_API_ID` | From my.telegram.org |
| `TELEGRAM_API_HASH` | From my.telegram.org |
| `TELEGRAM_TARGET_CHAT_ID` | Numeric group id |
| `TELEGRAM_BOT_API_URL` | `http://localhost:8081` on the host |

Other keys from `.env.example`:

| Variable | Notes |
|----------|--------|
| `POSTGRES_PORT` | `5433` on the host if port 5432 is already taken |
| `ARCHIVE_ENCRYPTION_KEY` | Leave empty to generate per session in the GUI |
| `HOST_SOURCE_MOUNT` | Default `$HOME`; files to back up must live under this path for Docker workers |

Workers inside Docker use `TELEGRAM_BOT_API_URL=http://telegram-bot-api:8081` (set in `docker-compose.yml`). The host GUI uses `localhost:8081`.

---

## 5. Verify stack

From the repo root:

```bash
docker compose up -d
docker compose ps
```

`telegram-bot-api`, `postgres`, and `redis` should be healthy. Then:

```bash
./scripts/run.sh
```

Or open only the GUI if containers already run:

```bash
PYTHONPATH=src .venv/bin/python -m application.gui
```

---

## 6. First backup

1. **Start Session** in the GUI (profile name; encryption key optional).
2. **Add File** → pick a file under `$HOME` → set **display name** (shown on volumes in Telegram).
3. **Start Backup** → **Refresh Progress**.
4. Open the target group: expect `your-display-name.7z.001` (more parts if the archive is large).

Worker logs:

```bash
docker compose logs -f celery-worker-archive-1
docker compose logs -f celery-worker-upload
```

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `telegram-bot-api` exits (1) / dependency failed to start | `.env` still has placeholders or empty `TELEGRAM_API_ID` / `TELEGRAM_API_HASH`; get both from [my.telegram.org](https://my.telegram.org). Run `docker compose logs telegram-bot-api` — expect *"You must provide valid api-id and api-hash"*. `./scripts/run.sh` now checks `.env` before compose. |
| Bot cannot post to group | Bot is admin; group id is correct; bot was added before id lookup |
| `getUpdates` empty | Message the group after adding the bot; try `/setprivacy` → Disable |
| Upload fails / connection refused | `docker compose ps`; `TELEGRAM_BOT_API_URL` on host is `http://localhost:8081` |
| File not found in worker | Source path must be under `HOST_SOURCE_MOUNT` (default `$HOME`) |
| Hashed filenames in chat (`abc123.7z.001`) | Rebuild workers: `./scripts/run.sh` (mounts host `src/` into containers) |
| Restore 404 | Known Bot API limitation; use [Client API plan](TELEGRAM_CLIENT_API_MIGRATION.md) or download from the group manually |

---

## Planned: automated onboarding

Today every step above is manual. Target: GUI wizard that collects API credentials, guides bot/group setup, writes `.env`, and runs `healthcheck`. After Client API migration, replace bot token flow with phone login and session file.

Tracked in [README § Onboarding automation](../README.md#onboarding-automation-planned) and [BACKLOG.md](BACKLOG.md).

---

## Related docs

| Doc | Topic |
|-----|--------|
| [PROJECT.md](PROJECT.md) | Run, verify, packaging |
| [INTERNAL_SPEC.md](INTERNAL_SPEC.md) | Encryption, `display_name`, no topics |
| [TELEGRAM_CLIENT_API_MIGRATION.md](TELEGRAM_CLIENT_API_MIGRATION.md) | Bot API → MTProto user session |
| [ONION_ARCHITECTURE.md](ONION_ARCHITECTURE.md) | `TelegramProviderV1`, compose services |
