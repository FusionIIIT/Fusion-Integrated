"""What the server tells the shell about ELM (ADR-0010).

Nav items carry `required_permission` and the server filters before sending.
All permission codes start with `elm.` per the Fusion accesscontrol manifest.
"""
MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "HR",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.dashboard",
        "label": "Dashboard",
        "icon": "House",
        "to": "/elm",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "FilePlus",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 20,
    },
    {
        "code": "elm.mine",
        "label": "My Leaves",
        "icon": "UserCheck",
        "to": "/elm/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 30,
    },
    {
        "code": "elm.substitute",
        "label": "Substitute Requests",
        "icon": "Users",
        "to": "/elm/substitute",
        "required_permission": "elm.substitute.respond",
        "sort_order": 40,
    },
    {
        "code": "elm.approvals",
        "label": "Approvals Inbox",
        "icon": "CheckSquare",
        "to": "/elm/approvals",
        "required_permission": "elm.leave.review",
        "sort_order": 50,
    },
    {
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "Coins",
        "to": "/elm/balances",
        "required_permission": "elm.leave.view_self",
        "sort_order": 60,
    },
    {
        "code": "elm.admin",
        "label": "Administrative Records",
        "icon": "Gear",
        "to": "/elm/admin",
        "required_permission": "elm.admin.manage",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View one's own leave balances and requests"),
    ("elm.leave.apply", "Apply for leave and withdraw pending requests"),
    ("elm.substitute.respond", "Accept or decline nominated substitute responsibilities"),
    ("elm.leave.review", "Review and recommend routed leave requests"),
    ("elm.leave.sanction_unit_head", "Final approval authority for CL and RH requests"),
    ("elm.establishment.route", "Establishment verification and routing"),
    ("elm.leave.sanction_final", "Competent final sanctioning authority for higher-sanction leave"),
    ("elm.director.self_sanction", "Self-sanction approval for Director applicant"),
    ("elm.admin.manage", "Administrative leave records maintenance and policy configuration"),
    ("elm.offline.record", "Record already-sanctioned offline leave into the system"),
    ("elm.year_end.execute", "Execute year-end leave balance conversion and lapse"),
]

SYSTEM_PERMISSIONS = [
    "elm.year_end.execute",
]

_EMPLOYEE = [
    "elm.leave.view_self",
    "elm.leave.apply",
    "elm.substitute.respond",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "elm.leave.review",
    "elm.leave.sanction_unit_head",
]

_ESTABLISHMENT = [
    *_EMPLOYEE,
    "elm.leave.review",
    "elm.establishment.route",
]

_SANCTIONING_AUTHORITY = [
    *_EMPLOYEE,
    "elm.leave.review",
    "elm.leave.sanction_final",
]

_DIRECTOR = [
    *_EMPLOYEE,
    "elm.leave.review",
    "elm.leave.sanction_final",
    "elm.director.self_sanction",
]

_LEAVE_ADMIN = [
    *_EMPLOYEE,
    "elm.admin.manage",
    "elm.offline.record",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "student": ["elm.leave.view_self"],
    "HOD": _UNIT_HEAD,
    "Deputy Registrar": _ESTABLISHMENT,
    "Dean": _SANCTIONING_AUTHORITY,
    "Dean Academic": _SANCTIONING_AUTHORITY,
    "Registrar": _SANCTIONING_AUTHORITY,
    "Director": _DIRECTOR,
    "leave_admin": _LEAVE_ADMIN,
    "admin": [*_LEAVE_ADMIN, "elm.leave.review", "elm.leave.sanction_final"],
}
