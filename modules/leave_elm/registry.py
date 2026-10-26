"""What the server tells the shell about this module (ADR-0010)."""

MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leaves",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("leave_elm.application.view_self", "View own leave applications and balances"),
    ("leave_elm.application.apply", "Submit a new leave application"),
    ("leave_elm.application.withdraw", "Withdraw own pending leave request"),
    ("leave_elm.application.review", "Review, recommend or sanction leave requests"),
    ("leave_elm.substitute.respond", "Accept or decline nominated substitute request"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave_elm.application.view_self",
    "leave_elm.application.apply",
    "leave_elm.application.withdraw",
    "leave_elm.substitute.respond",
]

_APPROVER = [
    *_EMPLOYEE,
    "leave_elm.application.review",
]

ROLE_GRANTS = {
    "student": [],
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Unit Head": _APPROVER,
    "Dean": _APPROVER,
    "Registrar": _APPROVER,
    "Director": _APPROVER,
}
