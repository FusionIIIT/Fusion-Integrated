"""Server-side module and navigation registry for ELM (ADR-0010)."""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Administration",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.dashboard",
        "label": "Leave Dashboard",
        "icon": "SquaresFour",
        "to": "/elm",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply Leave",
        "icon": "CalendarPlus",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 20,
    },
    {
        "code": "elm.requests",
        "label": "My Requests",
        "icon": "ListBullets",
        "to": "/elm/requests",
        "required_permission": "elm.leave.view_self",
        "sort_order": 30,
    },
    {
        "code": "elm.substitute",
        "label": "Substitute Requests",
        "icon": "UserSwitch",
        "to": "/elm/substitute",
        "required_permission": "elm.leave.substitute",
        "sort_order": 40,
    },
    {
        "code": "elm.approvals",
        "label": "Sanctions & Approvals",
        "icon": "CheckSquare",
        "to": "/elm/approvals",
        "required_permission": "elm.leave.approve",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    {"code": "elm.leave.view_self", "label": "View own leave balances and requests"},
    {"code": "elm.leave.apply", "label": "Apply for leave and nominate substitute"},
    {"code": "elm.leave.substitute", "label": "Accept or decline substitute requests"},
    {"code": "elm.leave.approve", "label": "Review, recommend, and sanction leaves"},
]

ROLE_GRANTS = [
    {
        "role": "faculty",
        "permissions": ["elm.leave.view_self", "elm.leave.apply", "elm.leave.substitute"],
    },
    {
        "role": "staff",
        "permissions": ["elm.leave.view_self", "elm.leave.apply", "elm.leave.substitute"],
    },
    {
        "role": "unit_head",
        "permissions": ["elm.leave.view_self", "elm.leave.apply", "elm.leave.substitute", "elm.leave.approve"],
    },
    {
        "role": "admin",
        "permissions": ["elm.leave.view_self", "elm.leave.apply", "elm.leave.substitute", "elm.leave.approve"],
    },
]
