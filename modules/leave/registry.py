"""Leave module registration and permissions for Fusion shell."""

MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "HR & Admin",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.apply",
        "label": "Apply Leave",
        "icon": "CalendarPlus",
        "to": "/leave/apply",
        "required_permission": "leave.application.create",
        "sort_order": 10,
    },
    {
        "code": "leave.my_leaves",
        "label": "My Leaves",
        "icon": "CalendarCheck",
        "to": "/leave/mine",
        "required_permission": "leave.application.view_self",
        "sort_order": 20,
    },
    {
        "code": "leave.balances",
        "label": "Leave Balances",
        "icon": "Clock",
        "to": "/leave/balances",
        "required_permission": "leave.balance.view",
        "sort_order": 30,
    },
    {
        "code": "leave.approvals",
        "label": "Pending Approvals",
        "icon": "CheckSquare",
        "to": "/leave/approvals",
        "required_permission": "leave.application.approve",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("leave.application.view_self", "View own leave applications"),
    ("leave.application.create", "Apply for leave"),
    ("leave.application.cancel", "Cancel own pending leave"),
    ("leave.application.approve", "Approve or reject leave applications"),
    ("leave.balance.view", "View leave balances"),
    ("leave.balance.manage", "Allocate and manage employee leave balances"),
]

_EMPLOYEE = [
    "leave.application.view_self",
    "leave.application.create",
    "leave.application.cancel",
    "leave.balance.view",
]

_APPROVER = _EMPLOYEE + [
    "leave.application.approve",
]

_ADMIN = _APPROVER + [
    "leave.balance.manage",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "hod": _APPROVER,
    "dean": _APPROVER,
    "admin": _ADMIN,
}
