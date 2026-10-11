MODULE = {
    "code": "leave_management",
    "label": "Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/elm",
    "nav_section": "Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.portal",
        "label": "Leave Portal",
        "icon": "FaCalendarAlt",
        "to": "/elm",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leaves and balances"),
    ("elm.leave.apply", "Apply for leave"),
    ("elm.leave.review", "Review and sanction leaves"),
]

SYSTEM_PERMISSIONS = []

_APPLICANT = ["elm.leave.view_self", "elm.leave.apply"]
_APPROVER = [*_APPLICANT, "elm.leave.review"]

ROLE_GRANTS = {
    "faculty": _APPLICANT,
    "staff": _APPLICANT,
    "student": _APPLICANT,
    "HOD": _APPROVER,
    "Dean": _APPROVER,
    "admin": _APPROVER,
}
