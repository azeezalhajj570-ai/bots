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
```

Notes:
- `MUTE_SECONDS` is the exact mute duration.
- `TEST_MODE=1` enables strict test behavior globally.

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

## Anonymous Admin Limitation

If a message is sent as anonymous admin identity (`sender_chat`, often shown like `@GroupAnonymousBot`), Telegram may not expose a targetable user for restriction. In this case, the bot can delete the link but may not be able to mute that sender identity.

## Logs

- Console logs are enabled by default.
- Rotating file logs are written to `LOG_DIR/bot.log`.
- HTTP request noise (`httpx`, `httpcore`) is reduced to warning level.

## Project Entry

- Main script: `bot.py`
- Package: `group_manager_bot/`

