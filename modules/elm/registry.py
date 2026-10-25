"""Server-side module metadata, navigation, permissions, and role grants for ELM.

Scanned by manage.py permission_manifest and manage.py seed_modules.
"""
MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Services",
    "sort_order": 20,
    "status": "planned",
}

NAV_ITEMS = [
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "CalendarPlus",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 10,
    },
    {
        "code": "elm.mine",
        "label": "My Leaves",
        "icon": "CalendarCheck",
        "to": "/elm/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 20,
    },
    {
        "code": "elm.approvals",
        "label": "Leave Approvals",
        "icon": "Checks",
        "to": "/elm/approvals",
        "required_permission": "elm.leave.review_unit_head",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View one's own leave applications and balances"),
    ("elm.leave.apply", "Apply for leave and station leave"),
    ("elm.leave.withdraw", "Withdraw pending leave application"),
    ("elm.leave.substitute_respond", "Accept or decline nominated substitute role"),
    ("elm.leave.review_unit_head", "Review and recommend/approve leave as Unit Head"),
    ("elm.leave.sanction", "Sanction or reject leave applications"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "elm.leave.view_self",
    "elm.leave.apply",
    "elm.leave.withdraw",
    "elm.leave.substitute_respond",
]

_APPROVER = [
    *_EMPLOYEE,
    "elm.leave.review_unit_head",
    "elm.leave.sanction",
]

ROLE_GRANTS = {
    "student": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "placement_coordinator": _EMPLOYEE,
    "placement_officer": _EMPLOYEE,
    "placement_chairman": _APPROVER,
    "HOD": _APPROVER,
    "Dean Academic": _APPROVER,
    "Registrar": _APPROVER,
    "Director": _APPROVER,
}
