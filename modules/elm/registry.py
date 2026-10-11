"""ELM module metadata, navigation, and permission registry."""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Leave",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.mine",
        "label": "My Leaves",
        "icon": "CalendarBlank",
        "to": "/elm/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply Leave",
        "icon": "PlusCircle",
        "to": "/elm/apply",
        "required_permission": "elm.leave.create",
        "sort_order": 20,
    },
    {
        "code": "elm.approvals",
        "label": "Approvals",
        "icon": "CheckCircle",
        "to": "/elm/approvals",
        "required_permission": "elm.leave.approve",
        "sort_order": 30,
    },
    {
        "code": "elm.substitutes",
        "label": "Substitute Requests",
        "icon": "Users",
        "to": "/elm/substitutes",
        "required_permission": "elm.leave.substitute",
        "sort_order": 40,
    },
    {
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "ChartBar",
        "to": "/elm/balances",
        "required_permission": "elm.leave.view_self",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave applications and balances"),
    ("elm.leave.create", "Apply for leave"),
    ("elm.leave.approve", "Review and approve leave applications"),
    ("elm.leave.substitute", "Respond to substitute requests"),
    ("elm.leave.manage", "Administrative leave management"),
]

SYSTEM_PERMISSIONS = []

_STAFF = [
    "elm.leave.view_self",
    "elm.leave.create",
    "elm.leave.substitute",
]

_FACULTY = [
    "elm.leave.view_self",
    "elm.leave.create",
    "elm.leave.substitute",
]

_UNIT_HEAD = [
    *_FACULTY,
    "elm.leave.approve",
]

_DIRECTOR = [
    *_UNIT_HEAD,
    "elm.leave.manage",
]

ROLE_GRANTS = {
    "staff": _STAFF,
    "faculty": _FACULTY,
    "unit_head": _UNIT_HEAD,
    "director": _DIRECTOR,
}
