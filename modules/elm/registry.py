"""What the server tells the shell about Employee Leave Management (ELM).

Server-driven navigation and RBAC configuration for ELM.
"""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/elm",
    "nav_section": "HR & Admin",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "FaPlusCircle",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 10,
    },
    {
        "code": "elm.mine",
        "label": "My Leaves & Balances",
        "icon": "FaHistory",
        "to": "/elm/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 20,
    },
    {
        "code": "elm.substitute",
        "label": "Substitute Requests",
        "icon": "FaUserCheck",
        "to": "/elm/substitute-requests",
        "required_permission": "elm.leave.substitute",
        "sort_order": 30,
    },
    {
        "code": "elm.unit_head",
        "label": "Unit Head Reviews",
        "icon": "FaUserTie",
        "to": "/elm/unit-head-reviews",
        "required_permission": "elm.leave.review",
        "sort_order": 40,
    },
    {
        "code": "elm.sanction",
        "label": "Sanction Decisions",
        "icon": "FaStamp",
        "to": "/elm/sanction-decisions",
        "required_permission": "elm.leave.sanction",
        "sort_order": 50,
    },
    {
        "code": "elm.admin",
        "label": "Leave Administration",
        "icon": "FaCogs",
        "to": "/elm/admin",
        "required_permission": "elm.leave.admin",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("elm.leave.apply", "Apply for leave and station leave"),
    ("elm.leave.view_self", "View own leave applications and balances"),
    ("elm.leave.substitute", "Respond to substitute responsibility coverage requests"),
    ("elm.leave.review", "Review and recommend applications as Unit Head"),
    ("elm.leave.sanction", "Sanction or reject applications as Competent Authority"),
    ("elm.leave.admin", "Maintain leave balances and holiday calendars"),
]

SYSTEM_PERMISSIONS = [
    "elm.leave.year_end_process",
]

_EMPLOYEE = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.substitute",
]

_HEAD = [
    *_EMPLOYEE,
    "elm.leave.review",
]

_AUTHORITY = [
    *_HEAD,
    "elm.leave.sanction",
]

_ADMIN = [
    *_AUTHORITY,
    "elm.leave.admin",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "student": ["elm.leave.view_self"],
    "Dean Academic": _AUTHORITY,
    "acadadmin": _ADMIN,
    "placement_chairman": _HEAD,
    "placement_officer": _HEAD,
}
