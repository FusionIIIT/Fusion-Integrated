"""Employee Leave Management module registry."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "Employee Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.my_leaves",
        "label": "My Leave Applications",
        "icon": "Calendar",
        "to": "/elm/applications",
        "required_permission": "elm.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "CalendarPlus",
        "to": "/elm/apply",
        "required_permission": "elm.application.create",
        "sort_order": 20,
    },
    {
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "Wallet",
        "to": "/elm/balances",
        "required_permission": "elm.balance.view_self",
        "sort_order": 30,
    },
    {
        "code": "elm.approvals",
        "label": "Leave Approvals",
        "icon": "ClipboardCheck",
        "to": "/elm/approvals",
        "required_permission": "elm.application.approve",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("elm.application.view_self", "View own leave applications"),
    ("elm.application.create", "Apply for leave"),
    ("elm.application.withdraw", "Withdraw own pending leave application"),
    ("elm.application.view", "View employee leave applications"),
    ("elm.application.recommend", "Recommend leave applications"),
    ("elm.application.approve", "Approve or reject leave applications"),
    ("elm.balance.view_self", "View own leave balances"),
    ("elm.balance.manage", "Manage employee leave balances"),
    ("elm.policy.manage", "Manage leave types and policies"),
    ("elm.calendar.manage", "Manage leave calendar"),
    ("elm.substitute.respond", "Accept or decline substitute requests"),
    ("elm.leave.record_offline", "Record offline-sanctioned leave"),
    ("elm.leave.process_year_end", "Process year-end leave carry-forward"),
]

_STUDENT = [
    "elm.application.view_self",
    "elm.application.create",
    "elm.application.withdraw",
    "elm.balance.view_self",
]

_EMPLOYEE = [
    "elm.application.view_self",
    "elm.application.create",
    "elm.application.withdraw",
    "elm.balance.view_self",
    "elm.substitute.respond",
]

_ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": [
        "elm.application.view",
        "elm.application.recommend",
        "elm.application.approve",
        "elm.balance.view_self",
    ],
    "Dean Academic": [
        "elm.application.view",
        "elm.application.approve",
        "elm.balance.view_self",
    ],
    "admin": [
        "elm.application.view",
        "elm.application.recommend",
        "elm.application.approve",
        "elm.balance.view_self",
        "elm.balance.manage",
        "elm.policy.manage",
        "elm.calendar.manage",
        "elm.leave.record_offline",
        "elm.leave.process_year_end",
    ],
}

ROLE_GRANTS = _ROLE_GRANTS
