"""What the server tells the shell about this module."""
MODULE = {
    "code": "elm", "label": "Leave", "icon": "Calendar",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "planned",
}

NAV_ITEMS = []

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

