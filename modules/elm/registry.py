"""Registry configuration for Employee Leave Management (ELM) module.
Defines module metadata, navigation items, permissions, and role grants.
"""

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
        "code": "elm.dashboard",
        "label": "Leave Dashboard",
        "icon": "FaTachometerAlt",
        "to": "/elm/dashboard",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply Leave",
        "icon": "FaCalendarPlus",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 20,
    },
    {
        "code": "elm.history",
        "label": "My Applications",
        "icon": "FaHistory",
        "to": "/elm/history",
        "required_permission": "elm.leave.view_self",
        "sort_order": 30,
    },
    {
        "code": "elm.approvals",
        "label": "Leave Approvals",
        "icon": "FaClipboardCheck",
        "to": "/elm/approvals",
        "required_permission": "elm.leave.review",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave balances and applications"),
    ("elm.leave.apply", "Submit leave application"),
    ("elm.leave.cancel", "Cancel own leave application"),
    ("elm.leave.review", "Review and recommend leave requests as Unit Head"),
    ("elm.leave.sanction", "Sanction or reject leave requests as Sanctioning Authority"),
    ("elm.leave.view_all", "View all employee leave records"),
]

SYSTEM_PERMISSIONS = []

_APPLICANT = [
    "elm.leave.view_self",
    "elm.leave.apply",
    "elm.leave.cancel",
]

_REVIEWER = [
    *_APPLICANT,
    "elm.leave.review",
]

_SANCTIONER = [
    *_REVIEWER,
    "elm.leave.sanction",
    "elm.leave.view_all",
]

ROLE_GRANTS = {
    "faculty": _APPLICANT,
    "staff": _APPLICANT,
    "student": _APPLICANT,
    "HOD": _REVIEWER,
    "unit_head": _REVIEWER,
    "Dean": _SANCTIONER,
    "Director": _SANCTIONER,
    "admin": _SANCTIONER,
}
