"""Leave permissions and its self-service navigation entry."""

MODULE = {
    "code": "leave", "label": "Leave", "icon": "FaCalendarAlt",
    "base_path": "/leave", "nav_section": "Services", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.requests", "label": "My Leave Requests",
        "icon": "FaCalendarAlt", "to": "/leave/requests",
        "required_permission": "leave.request.view_self", "sort_order": 10,
    },
]

PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests"),
    ("leave.request.create", "Apply for leave"),
    ("leave.request.delete", "Withdraw own pending leave request"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [code for code, _ in PERMISSIONS]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
}
