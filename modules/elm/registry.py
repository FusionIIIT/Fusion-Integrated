# Module registration and permissions for Employee Leave Management (ELM)
# Reflecting full role and permission matrix per Fusion Base and ELM specs

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "HR & Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.dashboard",
        "label": "My Leaves & Balances",
        "icon": "ClipboardText",
        "to": "/elm/dashboard",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply Leave",
        "icon": "PlusCircle",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 20,
    },
    {
        "code": "elm.substitute_requests",
        "label": "Substitute Requests",
        "icon": "UserSwitch",
        "to": "/elm/substitute-requests",
        "required_permission": "elm.substitute.respond",
        "sort_order": 25,
    },
    {
        "code": "elm.unit_head_approvals",
        "label": "Unit Head Approvals",
        "icon": "Checks",
        "to": "/elm/unit-head-approvals",
        "required_permission": "elm.leave.review_unit_head",
        "sort_order": 30,
    },
    {
        "code": "elm.sanctions",
        "label": "Sanctioning Queue",
        "icon": "Stamp",
        "to": "/elm/sanctioning-queue",
        "required_permission": "elm.leave.sanction_final",
        "sort_order": 35,
    },
    {
        "code": "elm.admin_offline",
        "label": "Offline & Year-End Admin",
        "icon": "Gear",
        "to": "/elm/admin",
        "required_permission": "elm.admin.manage",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave applications, balances, and history"),
    ("elm.leave.apply", "Submit a new leave application"),
    ("elm.leave.withdraw", "Withdraw own pending leave request"),
    ("elm.leave.cancel", "Cancel own approved leave request"),
    ("elm.leave.extend", "Submit extension for ongoing EL/COL/VL"),
    ("elm.leave.resume", "Submit return from leave / duty resumption"),
    ("elm.substitute.respond", "Accept or decline substitute nomination"),
    ("elm.leave.review_unit_head", "Unit head: approve CL/RH or recommend SCL/EL/COL/VL"),
    ("elm.leave.sanction_final", "Sanctioning authority: final decision for SCL/EL/COL/VL"),
    ("elm.leave.verify_resumption", "Verify duty resumption and restore early return balance"),
    ("elm.admin.record_offline", "Record offline/paper sanctioned leave"),
    ("elm.admin.yearend_process", "Execute year-end lapse, carry-forward, and conversion"),
    ("elm.admin.manage", "General ELM administrative access"),
]

# Role Grants mapped to standard Fusion designations
_EMPLOYEE = [
    "elm.leave.view_self",
    "elm.leave.apply",
    "elm.leave.withdraw",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
    "elm.substitute.respond",
]

_UNIT_HEAD = _EMPLOYEE + [
    "elm.leave.review_unit_head",
    "elm.leave.verify_resumption",
]

_SANCTIONING_AUTHORITY = _UNIT_HEAD + [
    "elm.leave.sanction_final",
]

_ESTABLISHMENT_ADMIN = _EMPLOYEE + [
    "elm.admin.record_offline",
    "elm.admin.yearend_process",
    "elm.admin.manage",
]

_DIRECTOR = _EMPLOYEE + [
    "elm.leave.review_unit_head",
    "elm.leave.sanction_final",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "hod": _UNIT_HEAD,
    "unit_head": _UNIT_HEAD,
    "dean": _SANCTIONING_AUTHORITY,
    "director": _DIRECTOR,
    "establishment_admin": _ESTABLISHMENT_ADMIN,
    "admin": _SANCTIONING_AUTHORITY + _ESTABLISHMENT_ADMIN,
}
