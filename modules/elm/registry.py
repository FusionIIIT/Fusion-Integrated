"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "elm", "label": "Employee Leave Management", "icon": "Calendar",
    "base_path": "/elm", "nav_section": "Employee Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.apply", "label": "Apply for Leave",
     "icon": "CalendarPlus", "to": "/elm/apply",
     "required_permission": "elm.leave.apply", "sort_order": 5},
    {"code": "elm.view", "label": "View Own Leave",
     "icon": "CalendarCheck", "to": "/elm/view",
     "required_permission": "elm.leave.view_self", "sort_order": 10},
    {"code": "elm.withdraw", "label": "Withdraw Leave",
     "icon": "CalendarX", "to": "/elm/withdraw",
     "required_permission": "elm.leave.withdraw", "sort_order": 15},
    {"code": "elm.respond", "label": "Respond as Substitute",
     "icon": "UserSwitch", "to": "/elm/respond",
     "required_permission": "elm.leave.respond", "sort_order": 20},
    {"code": "elm.review", "label": "Review as Unit Head",
     "icon": "UserCheck", "to": "/elm/review",
     "required_permission": "elm.leave.review", "sort_order": 25},
    {"code": "elm.sanction", "label": "Sanction",
     "icon": "ShieldCheck", "to": "/elm/sanction",
     "required_permission": "elm.leave.sanction", "sort_order": 30},
    {"code": "elm.cancel", "label": "Cancel Leave",
     "icon": "CalendarMinus", "to": "/elm/cancel",
     "required_permission": "elm.leave.cancel", "sort_order": 35},
    {"code": "elm.extend", "label": "Extend Leave",
     "icon": "CalendarPlus", "to": "/elm/extend",
     "required_permission": "elm.leave.extend", "sort_order": 40},
    {"code": "elm.resume", "label": "Resume Leave",
     "icon": "CalendarPlay", "to": "/elm/resume",
     "required_permission": "elm.leave.resume", "sort_order": 45},
    {"code": "elm.admin", "label": "Administer Leave Records",
     "icon": "Database", "to": "/elm/admin",
     "required_permission": "elm.leave.admin", "sort_order": 50},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.leave.apply", "Apply for leave"),
    ("elm.leave.view_self", "View own leave"),
    ("elm.leave.withdraw", "Withdraw leave"),
    ("elm.leave.respond", "Respond as substitute"),
    ("elm.leave.review", "Review as unit head"),
    ("elm.leave.sanction", "Sanction leave"),
    ("elm.leave.cancel", "Cancel leave"),
    ("elm.leave.extend", "Extend leave"),
    ("elm.leave.resume", "Resume leave"),
    ("elm.leave.admin", "Administer leave records"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

_FACULTY_STAFF = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.withdraw",
    "elm.leave.respond",
]

_UNIT_HEAD = [
    *_FACULTY_STAFF,
    "elm.leave.review",
]

_DEPUTY_REGISTRAR_ESTT = [
    *_FACULTY_STAFF,
    "elm.leave.sanction",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
]

_DEAN = [
    *_FACULTY_STAFF,
    "elm.leave.sanction",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
]

_REGISTRAR = [
    *_FACULTY_STAFF,
    "elm.leave.sanction",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
]

_DIRECTOR = [
    *_FACULTY_STAFF,
    "elm.leave.sanction",
    "elm.leave.cancel",
    "elm.leave.extend",
    "elm.leave.resume",
]

_LEAVE_ADMINISTRATOR = [
    *_FACULTY_STAFF,
    "elm.leave.admin",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "faculty": _FACULTY_STAFF,
    "staff": _FACULTY_STAFF,
    "Unit Head": _UNIT_HEAD,
    "Deputy Registrar (Estt.)": _DEPUTY_REGISTRAR_ESTT,
    "Dean": _DEAN,
    "Registrar": _REGISTRAR,
    "Director": _DIRECTOR,
    "Leave Administrator": _LEAVE_ADMINISTRATOR,
}
