"""
What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "leave", "label": "Leave Management", "icon": "CalendarBlank",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("leave.request.create", "Apply for leave"),
    ("leave.request.view_self", "See own leave requests"),
    ("leave.request.delete", "Withdraw own pending request"),
    ("leave.balance.view_self", "See own leave balances"),
]

SYSTEM_PERMISSIONS = []

_STUDENT = [
    "leave.request.create",
    "leave.request.view_self",
    "leave.request.delete",
    "leave.balance.view_self",
]

ROLE_GRANTS = {
    "faculty": _STUDENT,
    "staff": _STUDENT,
}
