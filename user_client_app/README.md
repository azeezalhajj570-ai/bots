# Telegram User Client (Separate App)

This is a separate app from your bot.  
It logs in as a **real Telegram user account** using MTProto (`API_ID` + `API_HASH`).

## Choose library

- `Telethon`: more low-level control/flexibility
- `Pyrogram`: cleaner high-level API

## Setup

1. Install deps:

```bash
pip install -r requirements-user-client.txt
```

2. Create `.env.user` from `.env.user.example`:

```env
API_ID=123456
API_HASH=YOUR_API_HASH
PHONE_NUMBER=+15551234567
SESSION_NAME=user_client
JOIN_LINKS=https://t.me/example_group,https://t.me/+InviteToken
```

Get `API_ID` and `API_HASH` from: https://my.telegram.org

## Run (Telethon)

```bash
python user_client_app/telethon_user_client.py
```

- First run asks for login code.
- If 2FA is enabled, it asks for password.
- Creates a local session file (`SESSION_NAME.session`).

## Run (Pyrogram)

```bash
python user_client_app/pyrogram_user_client.py
```

- First run performs login flow in terminal.
- Also creates local session file.
- If `JOIN_LINKS` is set, app tries to join those groups/channels at startup.

## Notes

- Keep your `API_HASH` and session file private.
- Do not use user-account automation in ways that violate Telegram Terms.
- On Python 3.13 (Windows), `tgcrypto` may fail to compile without MSVC Build Tools.
  - App still works without it (slower crypto path).
  - If you need max speed, install Microsoft C++ Build Tools then install `tgcrypto`.
