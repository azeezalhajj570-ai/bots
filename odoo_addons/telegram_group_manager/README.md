# Telegram Group Manager (Odoo Addon)

This addon provides:
- Odoo UI models for Telegram groups/settings/rules/routes/gates
- API endpoints used by `group_manager_bot`
- Mod/action log intake endpoints

## Install

1. Add `odoo_addons` to your Odoo `addons_path`.
2. Update apps list.
3. Install module: `Telegram Group Manager`.

## API Auth

Set a shared bearer token in Odoo:

- Telegram Bot Manager -> Settings -> API Token
- (Stored as system parameter `telegram_group_manager.api_token`)

Then set bot env:
- `ODOO_API_BASE_URL=https://your-odoo-host`
- `ODOO_API_TOKEN=<same token>`

If system parameter is empty, API is open (for local dev only).

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
