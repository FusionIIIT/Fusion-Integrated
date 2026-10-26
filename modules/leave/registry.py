"""What the server tells the shell about the Employee Leave Management module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering.
"""

MODULE = {
    "code": "leave_module",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Administration",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.apply",
        "label": "Apply for Leave",
        "icon": "CalendarPlus",
        "to": "/leave/apply",
        "required_permission": "leave_module.request.create",
        "sort_order": 10,
    },
    {
        "code": "leave.mine",
        "label": "My Leaves & Balances",
        "icon": "CalendarCheck",
        "to": "/leave/mine",
        "required_permission": "leave_module.request.view_self",
        "sort_order": 20,
    },
    {
        "code": "leave.substitute",
        "label": "Substitute Requests",
        "icon": "UserCheck",
        "to": "/leave/substitute",
        "required_permission": "leave_module.substitute.respond",
        "sort_order": 30,
    },
    {
        "code": "leave.approvals",
        "label": "Leave Approvals",
        "icon": "Checks",
        "to": "/leave/approvals",
        "required_permission": "leave_module.request.review",
        "sort_order": 40,
    },
    {
        "code": "leave.admin",
        "label": "Leave Administration",
        "icon": "Gear",
        "to": "/leave/admin",
        "required_permission": "leave_module.admin.manage",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("leave_module.request.create", "Apply for leave"),
    ("leave_module.request.view_self", "View own leave requests and balances"),
    ("leave_module.substitute.respond", "Accept or decline substitute requests"),
    ("leave_module.request.review", "Review, recommend, or sanction leave requests"),
    ("leave_module.admin.manage", "Maintain leave policies, calendars, and records"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave_module.request.create",
    "leave_module.request.view_self",
    "leave_module.substitute.respond",
]

_REVIEWER = [
    *_EMPLOYEE,
    "leave_module.request.review",
]

_ADMIN = [
    "leave_module.request.view_self",
    "leave_module.admin.manage",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "student": _EMPLOYEE,
    "HOD": _REVIEWER,
    "Dean": _REVIEWER,
    "Registrar": _REVIEWER,
    "Director": _REVIEWER,
    "Leave Administrator": _ADMIN,
    "acadadmin": _ADMIN,
}
