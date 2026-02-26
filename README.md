# Telegram Group Manager Bot

Moderation bot built with `python-telegram-bot` and SQLite.

## Features

- Inline settings panel in group: `/settings`
- Anti-links:
  - Detects `http(s)://`, `t.me/`, `telegram.me/`, `joinchat/`
  - Deletes link messages
  - Warn system with configurable threshold
  - Mute for configurable duration when threshold is reached
- Anti-bots: auto-ban bot accounts that join (if enabled)
- Message audit logging for group/private text and captions
- Test mode to force anti-link rules on everyone (admin, bot, user)

## Requirements

- Python 3.10+
- Bot token from BotFather

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create `.env` (or copy from `.env.example`) and set:

```env
BOT_TOKEN=YOUR_TOKEN_HERE
DB_PATH=bot.db
MAX_WARNS=3
MUTE_SECONDS=3600
LOG_LEVEL=INFO
LOG_DIR=logs
TEST_MODE=0
ODOO_API_BASE_URL=
ODOO_API_TOKEN=
ODOO_API_TIMEOUT_SECONDS=10
ODOO_CACHE_TTL_SECONDS=30
```

Notes:
- `MUTE_SECONDS` is the exact mute duration.
- `TEST_MODE=1` enables strict test behavior globally.
- Set `ODOO_API_BASE_URL` and `ODOO_API_TOKEN` to enable external Odoo API integration (scaffolded client).
- `ODOO_CACHE_TTL_SECONDS` controls settings/rules/routes/gates cache duration for Odoo API reads.

## Run

Normal mode:

```bash
python bot.py
```

Test mode (override at runtime):

```bash
python bot.py --test
```

`--test` forces anti-link checks for everyone, including admins and bot senders.

## Bot Commands

- `/start` - Basic bot status/help
- `/settings` - Open moderation settings panel (group)
- `/resetwarns` - Reply to a user message and reset warnings
- `/addrule <regex>` - Add dynamic remove rule (admin)
- `/delrule <id>` - Delete dynamic remove rule
- `/listrules` - List dynamic remove rules
- `/addroute <keyword> <url> [gate_group_id]` - Add keyword route
- `/delroute <keyword>` - Delete keyword route
- `/listroutes` - List keyword routes

These commands are also registered to Telegram command menu at startup.

## Permissions Needed

Give the bot admin rights in your group:

- Delete messages
- Ban/Restrict users

Without these, anti-link deletion or mute actions will fail.

## Anti-link Behavior

- If warnings are below threshold: delete link + warning message.
- When warnings hit threshold: user is muted for `MUTE_SECONDS`.
- If warnings are already at/above threshold:
  - warning count is capped at threshold,
  - links are still deleted,
  - user is muted if currently not restricted.
- Dynamic remove rules: regex-based ban rules configurable per chat.
- Link routes: keyword-based destination replies; can require membership in another group.
- Hide join/leave system messages: toggle in `/settings`.
- Warning delivery mode: toggle in `/settings` (group message or DM).

## Anonymous Admin Limitation

If a message is sent as anonymous admin identity (`sender_chat`, often shown like `@GroupAnonymousBot`), Telegram may not expose a targetable user for restriction. In this case, the bot can delete the link but may not be able to mute that sender identity.

## Logs

- Console logs are enabled by default.
- Rotating file logs are written to `LOG_DIR/bot.log`.
- HTTP request noise (`httpx`, `httpcore`) is reduced to warning level.

## Database Migrations

- SQLite schema is managed with SQL migrations in `group_manager_bot/migrations/`.
- Applied versions are tracked in `schema_version`.
- Current migration set:
  - `001_init.sql`
  - `002_outbox.sql`
  - `003_indexes.sql`
  - `004_dynamic_rules_and_routes.sql`
  - `005_warn_delivery.sql`
  - `006_warn_group_delivery.sql`
  - `007_participation_gates.sql`

## Odoo API (Scaffold)

- Client module: `group_manager_bot/integrations/odoo_api_client.py`
- Runtime provider with cache + DB fallback: `group_manager_bot/config_provider.py`
- Odoo addon scaffold: `odoo_addons/telegram_group_manager/`
- Implemented endpoint methods:
  - `GET /api/telegram/groups`
  - `GET /api/telegram/groups/{chat_id}/settings`
  - `GET /api/telegram/groups/{chat_id}/rules`
  - `GET /api/telegram/groups/{chat_id}/routes`
  - `GET /api/telegram/groups/{chat_id}/gates`
  - `POST /api/telegram/logs/mod`
  - `POST /api/telegram/events/action`
  - `POST /api/telegram/groups/{chat_id}/rules`
  - `DELETE /api/telegram/groups/{chat_id}/rules/{rule_id}`
  - `POST /api/telegram/groups/{chat_id}/routes`
  - `DELETE /api/telegram/groups/{chat_id}/routes/{keyword}`
  - `POST /api/telegram/groups/{chat_id}/gates`
  - `DELETE /api/telegram/groups/{chat_id}/gates/{gate_group_id}`

Write sync hooks are enabled for `/addrule`, `/delrule`, `/addroute`, `/delroute`, `/addgate`, `/delgate` (best-effort; local DB still succeeds if API fails).

## Project Entry

- Main script: `bot.py`
- Package: `group_manager_bot/`
