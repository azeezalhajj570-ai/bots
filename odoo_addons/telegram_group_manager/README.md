# Telegram Group Manager (Odoo Addon)

This addon provides:
- Odoo UI models for Telegram groups/settings/rules/routes/gates
- API endpoints used by `group_manager_bot`
- Mod/action log intake endpoints

## Install

1. Add `odoo_addons` to your Odoo `addons_path`.
2. Update apps list.
3. Install module: `Telegram Group Manager`.

## API Auth (Per Company)

Set bearer token per company in Odoo:

- Switch to target company
- Telegram Bot Manager -> Settings -> API Token

Then set bot env:
- `ODOO_API_BASE_URL=https://your-odoo-host`
- `ODOO_API_TOKEN=<token of that company>`

Requests are scoped to the company matched by bearer token.
If no company has a token configured, API falls back to current Odoo company (local/dev behavior).

## Endpoints

- `GET /api/telegram/groups`
- `GET /api/telegram/groups/{chat_id}/settings`
- `GET /api/telegram/groups/{chat_id}/rules`
- `GET /api/telegram/groups/{chat_id}/routes`
- `GET /api/telegram/groups/{chat_id}/gates`
- `POST /api/telegram/groups/{chat_id}/rules`
- `DELETE /api/telegram/groups/{chat_id}/rules/{rule_id}`
- `POST /api/telegram/groups/{chat_id}/routes`
- `DELETE /api/telegram/groups/{chat_id}/routes/{keyword}`
- `POST /api/telegram/groups/{chat_id}/gates`
- `DELETE /api/telegram/groups/{chat_id}/gates/{gate_group_id}`
- `POST /api/telegram/logs/mod`
- `POST /api/telegram/events/action`
