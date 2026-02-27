from __future__ import annotations

from telegram.ext import ContextTypes


SUPPORTED_LANGS = {"en", "ar"}


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "menu_open_settings": "Settings",
        "menu_route_wizard": "Route Wizard",
        "menu_help": "Help",
        "menu_language": "Language",
        "welcome": "Welcome to Group Manager Bot.\n\nUse the menu below to open settings or start guided setup.",
        "settings_menu": "Settings menu",
        "choose_groups": "Choose Group(s)",
        "start_route_wizard": "Start Route Wizard",
        "back": "Back",
        "back_home": "Back to Home",
        "choose_group_settings": "Choose a group to open settings:",
        "choose_group_route": "Choose a group to start route wizard:",
        "no_manageable_groups": "No manageable groups found yet.\nUse /settings in each group once, then open this list again.",
        "language_title": "Choose language:",
        "language_saved": "Language updated.",
        "help_text": "Help\n\nUse /settings to configure your groups.\nUse Auto Reply Settings for keyword responses.\nUse Ban Settings for moderation and temp-ban controls.\nUse Advertise Settings for required-membership groups.",
        "support_text": "Support\n\nIf you need technical help, contact the bot admin/support team.",
        "contact_text": "Contact\n\nFor inquiries, contact the bot administrator.",
        "lang_english": "English",
        "lang_arabic": "Arabic",
        "group_settings_home": "Group Settings\n\n- Chat ID: {chat_id}\n- Auto replies saved: {routes_count}\n- Participation gates: {gates_count}\n\nChoose a settings section:",
        "section_auto": "Auto Reply Settings",
        "section_ban": "Ban Settings",
        "section_adv": "Advertise Settings",
        "select_adv_groups": "Select Required Groups",
        "save_selection": "Save Selection",
        "adv_picker_title": "Select required groups for membership gate:\nTarget chat: `{chat_id}`",
        "adv_picker_empty": "No manageable groups available to select.",
        "adv_saved_result": "Added {added} groups. Skipped {skipped}.",
        "close": "Close",
        "refresh": "Refresh",
        "add_auto_reply": "Add Auto Reply",
        "auto_empty": "No auto replies saved yet.",
        "auto_header": "Saved responses:\n{lines}{tail}",
        "auto_tail": "\n... and {count} more",
        "auto_panel": "Auto Reply Settings\n\n{content}\n\nFormat:\n`keyword: response`\nYou can send multiple lines at once.",
        "adv_empty": "No participation groups required yet.",
        "adv_header": "Required membership groups:\n{lines}{tail}",
        "adv_panel": "Advertise Settings\nUsers can be blocked from participation unless they are members in required groups.\n\n{content}\n\nTo add/remove required groups use:\n- /addgate\n- /delgate",
        "ban_panel": "Ban Settings\n\n- Anti links: {anti_links}\n- Anti bots: {anti_bots}\n- Hide join/leave: {hide_system}\n- Warn in DM: {warn_in_dm}\n- Warn in group: {warn_in_group}\n- Temp ban before remove: {temp_ban_before_remove}\n- Temp ban duration: {temp_ban_duration}\n\nUse the buttons below to update each option.",
        "enabled": "Enabled",
        "disabled": "Disabled",
        "status_on": "ON",
        "status_off": "OFF",
        "anti_links": "Anti Links",
        "anti_bots": "Anti Bots",
        "hide_join_leave": "Hide Join/Leave",
        "warn_dm": "Warn in DM",
        "warn_group": "Warn in Group",
        "temp_ban_before_remove": "Temp ban before remove",
        "temp_ban_duration": "Temp ban duration",
        "add_ban_keywords": "Add Ban Keywords",
        "ban_keyword_prompt": "Send banned keywords, one per line.\nExample:\nspam\nscam\nfake",
        "ban_keyword_saved": "Saved {count} ban keywords for chat `{chat_id}`.",
        "ban_keyword_invalid": "No valid keywords found. Send at least one non-empty line.",
        "group_settings_home_short": "Group settings home.\nChoose a section:",
        "admins_only": "Admins only.",
        "wizard_started": "Auto reply setup started for selected group.\nSend `keyword: response`.\nYou can send multiple lines at once.\nSend 'cancel' anytime to stop.",
        "wizard_started_group": "Auto reply setup started.\nStep 1/3: send target group username or t.me link.\nSend 'cancel' anytime to stop.",
        "wizard_keyword_prompt": "Send `keyword: response` (example: `promo: https://example.com`).\nYou can send multiple lines at once.",
        "wizard_destination_prompt": "Send response content for the previously entered keyword.\nOr send multiple lines in format:\nkeyword: response",
        "wizard_saved_single": "Route saved for chat `{chat_id}`:\n`{keyword}`: {destination}",
        "wizard_saved_bulk": "Saved {count} routes for chat `{chat_id}`.",
        "wizard_bulk_invalid_line": "Invalid line: `{line}`\nUse format: keyword: destination",
        "main_commands": "Main commands:\n/settings - open group settings\n/help - help\n/support - support\n/contact - contact\n/addroute - add keyword route\n/listroutes - list routes\n/addgate - add participation gate\n/listrules - list dynamic remove rules",
        "cancelled": "Cancelled. Use /start to open the menu again.",
    },
    "ar": {
        "menu_open_settings": "الإعدادات",
        "menu_route_wizard": "معالج الردود",
        "menu_help": "مساعدة",
        "menu_language": "اللغة",
        "welcome": "مرحبًا بك في بوت إدارة المجموعات.\n\nاستخدم القائمة بالأسفل لفتح الإعدادات أو بدء الإعداد الموجّه.",
        "settings_menu": "قائمة الإعدادات",
        "choose_groups": "اختيار مجموعة",
        "start_route_wizard": "بدء معالج الردود",
        "back": "رجوع",
        "back_home": "العودة للرئيسية",
        "choose_group_settings": "اختر مجموعة لفتح الإعدادات:",
        "choose_group_route": "اختر مجموعة لبدء معالج الردود:",
        "no_manageable_groups": "لا توجد مجموعات متاحة للإدارة الآن.\nاستخدم /settings داخل كل مجموعة مرة واحدة ثم أعد فتح القائمة.",
        "language_title": "اختر اللغة:",
        "language_saved": "تم تحديث اللغة.",
        "help_text": "مساعدة\n\nاستخدم /settings لإعداد مجموعاتك.\nاستخدم إعدادات الرد التلقائي للردود بالكلمات المفتاحية.\nاستخدم إعدادات الحظر للمراقبة والحظر المؤقت.\nاستخدم إعدادات الإعلان للاشتراك الإجباري.",
        "support_text": "الدعم\n\nإذا احتجت مساعدة تقنية تواصل مع مسؤول أو فريق دعم البوت.",
        "contact_text": "التواصل\n\nللاستفسارات تواصل مع مسؤول البوت.",
        "lang_english": "English",
        "lang_arabic": "العربية",
        "group_settings_home": "إعدادات المجموعة\n\n- رقم المجموعة: {chat_id}\n- عدد الردود المحفوظة: {routes_count}\n- مجموعات الاشتراك الإجباري: {gates_count}\n\nاختر قسم الإعدادات:",
        "section_auto": "إعدادات الرد التلقائي",
        "section_ban": "إعدادات الحظر",
        "section_adv": "إعدادات الإعلان",
        "select_adv_groups": "اختيار المجموعات المطلوبة",
        "save_selection": "حفظ الاختيار",
        "adv_picker_title": "اختر المجموعات المطلوبة للاشتراك:\nالمجموعة المستهدفة: `{chat_id}`",
        "adv_picker_empty": "لا توجد مجموعات متاحة للاختيار.",
        "adv_saved_result": "تمت إضافة {added} مجموعات وتخطي {skipped}.",
        "close": "إغلاق",
        "refresh": "تحديث",
        "add_auto_reply": "إضافة رد تلقائي",
        "auto_empty": "لا توجد ردود تلقائية محفوظة.",
        "auto_header": "الردود المحفوظة:\n{lines}{tail}",
        "auto_tail": "\n... ويوجد {count} أكثر",
        "auto_panel": "إعدادات الرد التلقائي\n\n{content}\n\nالصيغة:\n`keyword: response`\nيمكنك إرسال عدة أسطر مرة واحدة.",
        "adv_empty": "لا توجد مجموعات اشتراك إجباري.",
        "adv_header": "مجموعات الاشتراك المطلوبة:\n{lines}{tail}",
        "adv_panel": "إعدادات الإعلان\nيمكن منع المستخدم من المشاركة حتى يكون عضوًا في المجموعات المطلوبة.\n\n{content}\n\nلإضافة/حذف المجموعات المطلوبة استخدم:\n- /addgate\n- /delgate",
        "ban_panel": "إعدادات الحظر\n\n- منع الروابط: {anti_links}\n- منع البوتات: {anti_bots}\n- إخفاء الدخول/الخروج: {hide_system}\n- تحذير في الخاص: {warn_in_dm}\n- تحذير في المجموعة: {warn_in_group}\n- حظر مؤقت قبل الإزالة: {temp_ban_before_remove}\n- مدة الحظر المؤقت: {temp_ban_duration}\n\nاستخدم الأزرار بالأسفل لتعديل الخيارات.",
        "enabled": "مفعل",
        "disabled": "متوقف",
        "status_on": "تشغيل",
        "status_off": "إيقاف",
        "anti_links": "منع الروابط",
        "anti_bots": "منع البوتات",
        "hide_join_leave": "إخفاء الدخول/الخروج",
        "warn_dm": "تحذير في الخاص",
        "warn_group": "تحذير في المجموعة",
        "temp_ban_before_remove": "حظر مؤقت قبل الإزالة",
        "temp_ban_duration": "مدة الحظر المؤقت",
        "add_ban_keywords": "إضافة كلمات حظر",
        "ban_keyword_prompt": "أرسل كلمات الحظر، كل كلمة في سطر.\nمثال:\nspam\nscam\nfake",
        "ban_keyword_saved": "تم حفظ {count} كلمات حظر للمجموعة `{chat_id}`.",
        "ban_keyword_invalid": "لا توجد كلمات صحيحة. أرسل سطرًا واحدًا على الأقل غير فارغ.",
        "group_settings_home_short": "واجهة إعدادات المجموعة.\nاختر القسم:",
        "admins_only": "للمشرفين فقط.",
        "wizard_started": "تم بدء إعداد الرد التلقائي للمجموعة المحددة.\nأرسل `keyword: response`.\nيمكنك إرسال عدة أسطر مرة واحدة.\nأرسل 'cancel' للإلغاء.",
        "wizard_started_group": "تم بدء إعداد الرد التلقائي.\nالخطوة 1/3: أرسل يوزر المجموعة أو رابط t.me.\nأرسل 'cancel' للإلغاء.",
        "wizard_keyword_prompt": "أرسل `keyword: response` (مثال: `promo: https://example.com`).\nيمكنك إرسال عدة أسطر مرة واحدة.",
        "wizard_destination_prompt": "أرسل الرد للكلمة التي أدخلتها سابقًا.\nأو أرسل عدة أسطر بالصيغة:\nkeyword: response",
        "wizard_saved_single": "تم حفظ الرد للمجموعة `{chat_id}`:\n`{keyword}`: {destination}",
        "wizard_saved_bulk": "تم حفظ {count} ردود للمجموعة `{chat_id}`.",
        "wizard_bulk_invalid_line": "سطر غير صحيح: `{line}`\nاستخدم الصيغة: keyword: destination",
        "main_commands": "الأوامر الرئيسية:\n/settings - فتح إعدادات المجموعة\n/help - مساعدة\n/support - دعم\n/contact - تواصل\n/addroute - إضافة رد بكلمة مفتاحية\n/listroutes - عرض الردود\n/addgate - إضافة اشتراك إجباري\n/listrules - عرض قواعد الحذف",
        "cancelled": "تم الإلغاء. استخدم /start لفتح القائمة من جديد.",
    },
}


def normalize_lang(value: str | None) -> str:
    if not value:
        return "en"
    lowered = value.lower()
    if lowered.startswith("ar"):
        return "ar"
    return "en"


def get_user_lang(context: ContextTypes.DEFAULT_TYPE, fallback_lang_code: str | None = None) -> str:
    lang = context.user_data.get("lang")
    if lang in SUPPORTED_LANGS:
        return lang
    resolved = normalize_lang(fallback_lang_code)
    context.user_data["lang"] = resolved
    return resolved


def set_user_lang(context: ContextTypes.DEFAULT_TYPE, lang: str) -> str:
    resolved = normalize_lang(lang)
    context.user_data["lang"] = resolved
    return resolved


def tr(lang: str, key: str, **kwargs) -> str:
    table = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    text = table.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text
