"""What the server tells the shell about the Employee Leave Management (ELM) module (ADR-0010)."""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "FaCalendarCheck",
    "base_path": "/elm",
    "nav_section": "Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.mine",
        "label": "My Leaves",
        "icon": "FaCalendarAlt",
        "to": "/elm/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply Leave",
        "icon": "FaPlusCircle",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 20,
    },
    {
        "code": "elm.tasks",
        "label": "Leave Inbox",
        "icon": "FaInbox",
        "to": "/elm/tasks",
        "required_permission": "elm.leave.review",
        "sort_order": 30,
    },
    {
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "FaChartPie",
        "to": "/elm/balances",
        "required_permission": "elm.leave.view_self",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("elm.leave.apply", "Apply for leave, request cancellation, or withdraw requests"),
    ("elm.leave.view_self", "View own leave applications and balances"),
    ("elm.leave.substitute", "Accept or decline substitute responsibility requests"),
    ("elm.leave.review", "Recommend or approve routed leave applications"),
    ("elm.leave.admin", "Manage leave policies, calendars, and sync offline leaves"),
]

SYSTEM_PERMISSIONS: list[str] = []

_EMPLOYEE = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.substitute",
]

_APPROVER = [
    *_EMPLOYEE,
    "elm.leave.review",
]

_ADMIN = [
    *_APPROVER,
    "elm.leave.admin",
]

ROLE_GRANTS = {
    "faculty": _APPROVER,
    "staff": _APPROVER,
    "unit_head": _APPROVER,
    "dean": _APPROVER,
    "registrar": _APPROVER,
    "director": _APPROVER,
    "admin": _ADMIN,
}
