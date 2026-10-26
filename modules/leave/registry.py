MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

#: Headless / API-only in Phase 1: no client-side routes exist yet, so NAV_ITEMS is empty
#: to avoid dead links and pass ops/checks/nav_matches_routes.py per role-assignment-guide.md.
NAV_ITEMS = []

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

