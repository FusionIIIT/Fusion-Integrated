MODULE = {
    "code": "leave_management",
    "label": "Leave Portal",
    "icon": "FaCalendarCheck",
    "base_path": "/elm",
    "nav_section": "Services",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.leave_portal",
        "label": "Leave Management",
        "icon": "FaCalendarCheck",
        "to": "/elm",
        "required_permission": "elm.leave.access",
        "sort_order": 15,
    },
]

PERMISSIONS = [
    ("elm.leave.access", "Access employee leave features"),
    ("elm.leave.submit", "Submit new leave application"),
    ("elm.leave.manage", "Review and approve leave applications"),
]

SYSTEM_PERMISSIONS = []

_STAFF = ["elm.leave.access", "elm.leave.submit"]
_AUTHORITY = [*_STAFF, "elm.leave.manage"]

ROLE_GRANTS = {
    "faculty": _STAFF,
    "staff": _STAFF,
    "student": _STAFF,
    "HOD": _AUTHORITY,
    "Dean": _AUTHORITY,
    "admin": _AUTHORITY,
}
