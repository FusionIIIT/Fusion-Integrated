MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.applications",
        "label": "Leave Applications",
        "icon": "CalendarBlank",
        "to": "/leave",
        "required_permission": "leave.application.view",
        "sort_order": 10,
    },
    {
        "code": "leave.apply",
        "label": "Apply for Leave",
        "icon": "PlusCircle",
        "to": "/leave/apply",
        "required_permission": "leave.application.create",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("leave.application.view", "See leave applications"),
    ("leave.application.create", "Apply for leave"),
    ("leave.application.review", "Review and recommend leave applications"),
    ("leave.application.approve", "Sanction or reject leave applications"),
    ("leave.application.delete", "Withdraw a leave application"),
    ("leave.substitute.respond", "Accept or decline standing in for someone"),
    ("leave.balance.view", "See leave balances across employees"),
]

SYSTEM_PERMISSIONS = [
    "leave.application.auto_withdraw",
]

_EMPLOYEE = [
    "leave.application.view",
    "leave.application.create",
    "leave.application.delete",
    "leave.substitute.respond",
]

_APPROVER = [
    *_EMPLOYEE,
    "leave.application.review",
    "leave.application.approve",
    "leave.balance.view",
]

_ADMIN = [
    *_APPROVER,
]

ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Unit Head": _APPROVER,
    "Leave Approver": _APPROVER,
    "Dean Academic": _APPROVER,
    "Registrar": _APPROVER,
    "Director": _APPROVER,
    "acadadmin": _ADMIN,
}

