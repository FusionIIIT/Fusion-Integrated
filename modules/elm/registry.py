"""Module metadata and navigation for Employee Leave Management (ADR-0010)."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "Employee Leave Management",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.applications",
        "label": "My Leave Applications",
        "icon": "CalendarCheck",
        "to": "/elm/applications",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "FileText",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 20,
    },
    {
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "Clock",
        "to": "/elm/balances",
        "required_permission": "elm.leave.view_self",
        "sort_order": 30,
    },
    {
        "code": "elm.substitute",
        "label": "Substitute Requests",
        "icon": "UserCheck",
        "to": "/elm/substitute",
        "required_permission": "elm.leave.substitute",
        "sort_order": 40,
    },
    {
        "code": "elm.unit_head_reviews",
        "label": "Unit Head Reviews",
        "icon": "CheckSquare",
        "to": "/elm/unit-head-reviews",
        "required_permission": "elm.leave.unit_head_review",
        "sort_order": 50,
    },
    {
        "code": "elm.sanctions",
        "label": "Leave Sanctions",
        "icon": "Award",
        "to": "/elm/sanctions",
        "required_permission": "elm.leave.sanction",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave applications and balances"),
    ("elm.leave.apply", "Apply, withdraw, cancel, or extend own leave"),
    ("elm.leave.substitute", "Respond to substitute responsibility requests"),
    ("elm.leave.unit_head_review", "Review and approve/recommend leave as Unit Head"),
    ("elm.leave.establishment", "Route higher-sanction leave at Establishment"),
    ("elm.leave.sanction", "Sanction leave as Dean, Registrar, or Director"),
    ("elm.leave.admin", "Administer policy, records, and holiday calendar"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "faculty": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.leave.substitute",
    ],
    "staff": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.leave.substitute",
    ],
    "unit_head": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.leave.substitute",
        "elm.leave.unit_head_review",
    ],
    "establishment": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.leave.establishment",
    ],
    "dean": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.leave.sanction",
    ],
    "registrar": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.leave.sanction",
    ],
    "director": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.leave.sanction",
    ],
    "leave_admin": [
        "elm.leave.view_self",
        "elm.leave.admin",
    ],
}
