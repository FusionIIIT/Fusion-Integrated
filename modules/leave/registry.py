"""What the server tells the shell about this module (ADR-0010)."""

MODULE = {
    "code": "leave_management",
    "label": "Leave Management",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "HR/Admin",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("leave_management.application.view_self", "View own leave applications"),
    ("leave_management.application.create", "Submit a leave request or cancellation"),
    ("leave_management.application.respond", "Respond to substitute nomination"),
    ("leave_management.application.view", "View all leave applications"),
    ("leave_management.application.review", "Review and sanction leave applications"),
    ("leave_management.application.delete", "Withdraw a leave application"),
    ("leave_management.application.auto_withdraw", "System auto-withdrawal"),
    ("leave_management.balance.view", "View leave balances"),
    ("leave_management.balance.manage", "Manage leave balances (Admin)"),
]

SYSTEM_PERMISSIONS = [
    "leave_management.application.auto_withdraw",
]

_EMPLOYEE_BASE = [
    "leave_management.application.view_self",
    "leave_management.application.create",
    "leave_management.application.respond",
    "leave_management.application.delete",
    "leave_management.balance.view",
]

_REVIEWER = [
    *_EMPLOYEE_BASE,
    "leave_management.application.view",
    "leave_management.application.review",
]

_ADMIN = [
    *_REVIEWER,
    "leave_management.balance.manage",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "Junior Assistant": _EMPLOYEE_BASE,
    "faculty": _EMPLOYEE_BASE,
    "HOD (CSE)": _REVIEWER,
    "Dean Academic": _REVIEWER,
    "Registrar": _ADMIN,
    "Director": _REVIEWER,
    "acadadmin": _ADMIN,
}
