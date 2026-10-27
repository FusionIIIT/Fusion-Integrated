"""Leave permissions and a deliberately non-public module registration."""

MODULE = {
    "code": "leave", "label": "Leave", "icon": "FaCalendarAlt",
    "base_path": "/leave", "nav_section": "Services", "sort_order": 30,
    # The API foundation is not a complete employee workflow yet.
    "status": "planned",
}

NAV_ITEMS = []

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
