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
    {"code": "elm.my_leave", "label": "My Leave",
     "icon": "CalendarPlus", "to": "/elm/my-leave",
     "required_permission": "elm.leave.view_self", "sort_order": 5},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.leave.apply", "Apply for leave"),
    ("elm.leave.view_self", "View own leave"),
    ("elm.leave.withdraw", "Withdraw leave"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

_FACULTY_STAFF = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.withdraw",
]

_UNIT_HEAD = [
    *_FACULTY_STAFF,
]

_DEPUTY_REGISTRAR_ESTT = [
    *_FACULTY_STAFF,
]

_DEAN = [
    *_FACULTY_STAFF,
]

_REGISTRAR = [
    *_FACULTY_STAFF,
]

_DIRECTOR = [
    *_FACULTY_STAFF,
]

_LEAVE_ADMINISTRATOR = [
    *_FACULTY_STAFF,
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


