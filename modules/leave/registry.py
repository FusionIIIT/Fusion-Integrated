MODULE = {
    "code": "leave",
    "label": "Employee Leave",
    "icon": "FaCalendarAlt",
    "base_path": "/leave",
    "nav_section": "HR",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.apply",
        "label": "Apply for Leave",
        "icon": "FaClipboardList",
        "to": "/leave/apply",
        "required_permission": "leave.application.apply",
        "sort_order": 10,
    },
    {
        "code": "leave.my_leaves",
        "label": "My Leaves & Balances",
        "icon": "FaCalendarAlt",
        "to": "/leave/my-leaves",
        "required_permission": "leave.application.view_self",
        "sort_order": 20,
    },
    {
        "code": "leave.substitute_inbox",
        "label": "Substitute Requests",
        "icon": "FaUsers",
        "to": "/leave/substitute",
        "required_permission": "leave.application.view_self",
        "sort_order": 30,
    },
    {
        "code": "leave.reviews",
        "label": "Approval Queue",
        "icon": "FaClipboardCheck",
        "to": "/leave/reviews",
        "required_permission": "leave.application.review",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("leave.application.apply", "Apply for institute employee leave"),
    ("leave.application.view_self", "View own leave applications, balances, and history"),
    ("leave.application.review", "Review, recommend, and sanction employee leave applications"),
    ("leave.admin.manage", "Manage leave policies, holiday calendars, and offline synchronization"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave.application.apply",
    "leave.application.view_self",
]

_APPROVER = [
    *_EMPLOYEE,
    "leave.application.review",
]

_ADMIN = [
    *_APPROVER,
    "leave.admin.manage",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": _APPROVER,
    "hod": _APPROVER,
    "dean": _APPROVER,
    "director": _APPROVER,
    "leave_admin": _ADMIN,
}
