{
    "name": "Telegram Group Manager",
    "version": "1.0",
    "summary": "Bot configuration and API backend for Telegram group manager",
    "author": "Local",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "security/tgm_security_rules.xml",
        "views/group_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu.xml",
    ],
    "application": True,
    "installable": True,
}
