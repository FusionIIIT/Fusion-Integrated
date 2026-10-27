"""What the server tells the shell about this module."""
MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "Services",
    "sort_order": 20,
    "status": "ready",
}

NAV_ITEMS = [
    {
        "code": "leave_overview",
        "label": "Overview",
        "to": "/leave",
        "icon": "Calendar",
        "required_permission": "elm.leave.view_self",
    },
    {
        "code": "leave_apply",
        "label": "Apply Leave",
        "to": "/leave/apply",
        "icon": "PlusCircle",
        "required_permission": "elm.leave.create",
    },
    {
        "code": "leave_my_requests",
        "label": "My Requests",
        "to": "/leave/my-requests",
        "icon": "FileText",
        "required_permission": "elm.leave.view_self",
    },
    {
        "code": "leave_approvals",
        "label": "Approvals",
        "to": "/leave/approvals",
        "icon": "CheckSquare",
        "required_permission": "elm.leave.recommend",
    },
    {
        "code": "leave_balances",
        "label": "Leave Balances",
        "to": "/leave/balances",
        "icon": "PieChart",
        "required_permission": "elm.leave.view_self",
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "See one's own leave requests"),
    ("elm.leave.create", "Apply for leave"),
    ("elm.leave.withdraw", "Withdraw a pending leave request"),
    ("elm.leave.view", "See leave requests, within scope"),
    ("elm.leave.recommend", "Recommend leave as unit head"),
    ("elm.leave.verify", "Verify leave at establishment"),
    ("elm.leave.decide", "Approve or reject leave"),
    ("elm.leave.self_sanction", "Self-sanction leave as director"),
    ("elm.leave.cancel", "Cancel approved leave"),
    ("elm.leave.report", "See leave reports"),
]

SYSTEM_PERMISSIONS = [
    "elm.leave.auto_process",
]

SCOPE_PERMISSIONS = [
    "elm.leave.view",
    "elm.leave.report",
]

_EMPLOYEE = [
    "elm.leave.view_self",
    "elm.leave.create",
    "elm.leave.withdraw",
    "elm.leave.cancel",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "elm.leave.view",
    "elm.leave.recommend",
]

_ESTABLISHMENT = [
    "elm.leave.view",
    "elm.leave.verify",
    "elm.leave.report",
]

_AUTHORITY = [
    *_UNIT_HEAD,
    "elm.leave.verify",
    "elm.leave.decide",
    "elm.leave.report",
]

_DIRECTOR = [
    *_AUTHORITY,
    "elm.leave.self_sanction",
]

ROLE_GRANTS = {
    "employee": _EMPLOYEE,
    "unit_head": _UNIT_HEAD,
    "establishment": _ESTABLISHMENT,
    "sanctioning_authority": _AUTHORITY,
    "director": _DIRECTOR,
}
