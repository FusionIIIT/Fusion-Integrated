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
        "code": "leave.balances",
        "label": "Leave Balances",
        "icon": "Gauge",
        "to": "/leave/balances",
        "required_permission": "leave.balance.view",
        "sort_order": 10,
    },
    {
        "code": "leave.apply",
        "label": "Apply Leave",
        "icon": "PlusCircle",
        "to": "/leave/apply",
        "required_permission": "leave.application.create",
        "sort_order": 20,
    },
    {
        "code": "leave.history",
        "label": "My Requests",
        "icon": "CalendarCheck",
        "to": "/leave/history",
        "required_permission": "leave.application.view_self",
        "sort_order": 30,
    },
    {
        "code": "leave.approvals",
        "label": "Pending Approvals",
        "icon": "Checks",
        "to": "/leave/approvals",
        "required_permission": "leave.application.approve",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("leave.application.view_self", "View own leave applications"),
    ("leave.application.create", "Apply for leave"),
    ("leave.application.cancel", "Cancel own pending leave"),
    ("leave.application.recommend", "Recommend leave applications"),
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

_RECOMMENDER = _EMPLOYEE + [
    "leave.application.recommend",
]

_APPROVER = _RECOMMENDER + [
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
    "director": _APPROVER,
    "admin": _ADMIN,
}
