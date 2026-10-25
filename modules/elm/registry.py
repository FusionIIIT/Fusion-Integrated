"""ELM module registry for Fusion ERP navigation and permissions."""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Academics",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.apply",
        "label": "Apply Leave",
        "icon": "ClipboardText",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("elm.leave.apply", "Apply for employee leave"),
    ("elm.leave.view", "View personal leave applications"),
    ("elm.leave.review", "Review submitted leave applications"),
    ("elm.leave.approve", "Approve or reject leave applications"),
    ("elm.leave.balance_view", "View leave balance quota"),
]
