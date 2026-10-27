"""Module registration and permissions for Employee Leave Management."""

MODULE = {
    "code": "leave",
    "label": "Employee Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Employee Services",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.requests",
        "label": "My Leave Requests",
        "icon": "CalendarBlank",
        "to": "/leave/requests",
        "required_permission": "leave.request.view_self",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests"),
    ("leave.request.create", "Submit leave requests"),
    ("leave.request.withdraw", "Withdraw own pending leave requests"),
]

_EMPLOYEE = [
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.withdraw",
]

ROLE_GRANTS = {
    "faculty": list(_EMPLOYEE),
    "staff": list(_EMPLOYEE),
    "Dean Academic": list(_EMPLOYEE),
}
