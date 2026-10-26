"""What the server tells the shell about the ELM module."""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "HR & Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.balance",
        "label": "Leave Balance",
        "icon": "ClipboardText",
        "to": "/elm/balance",
        "required_permission": "elm.balance.view",
        "sort_order": 10,
    },
    {
        "code": "elm.application",
        "label": "Leave Application",
        "icon": "FileText",
        "to": "/elm/application",
        "required_permission": "elm.application.create",
        "sort_order": 20,
    },
    {
        "code": "elm.history",
        "label": "Leave History",
        "icon": "ClockCounterClockwise",
        "to": "/elm/history",
        "required_permission": "elm.balance.view",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("elm.balance.view", "View leave balance"),
    ("elm.application.create", "Submit a leave application"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "faculty": ["elm.balance.view", "elm.application.create"],
    "staff": ["elm.balance.view", "elm.application.create"],
}
