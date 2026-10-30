"""Leave module registry configuration."""

MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/leave",
    "nav_section": "Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.dashboard",
        "label": "Leave Dashboard",
        "icon": "FaCalendarAlt",
        "to": "/leave/dashboard",
        "required_permission": "leave.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "leave.apply",
        "label": "Apply for Leave",
        "icon": "FaPlusCircle",
        "to": "/leave/apply",
        "required_permission": "leave.application.create",
        "sort_order": 20,
    },
    {
        "code": "leave.approvals",
        "label": "Approvals & Tasks",
        "icon": "FaTasks",
        "to": "/leave/approvals",
        "required_permission": "leave.application.review",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("leave.application.view_self", "View own leave applications and balance"),
    ("leave.application.create", "Create and submit leave requests"),
    ("leave.application.review", "Review and sanction leave applications"),
    ("leave.substitute.respond", "Accept or decline nominated substitute requests"),
    ("leave.admin.manage", "Maintain leave policy, calendar, and offline records"),
]

SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []

_EMPLOYEE = [
    "leave.application.view_self",
    "leave.application.create",
    "leave.substitute.respond",
]

_REVIEWER = [
    *_EMPLOYEE,
    "leave.application.review",
]

_ADMIN = [
    *_REVIEWER,
    "leave.admin.manage",
]

ROLE_GRANTS = {
    "faculty": _REVIEWER,
    "staff": _EMPLOYEE,
    "HOD": _REVIEWER,
    "Director": _REVIEWER,
    "Registrar": _REVIEWER,
    "Dean Academic": _REVIEWER,
    "acadadmin": _ADMIN,
    "placement_officer": _EMPLOYEE,
    "placement_coordinator": _EMPLOYEE,
    "placement_chairman": _REVIEWER,
}
