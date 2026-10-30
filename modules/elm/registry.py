"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "planned",
}

NAV_ITEMS = []

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.leave.view", "See leave categories and own balances"),
    ("elm.leave.view_self", "See own leave applications"),
    ("elm.leave.create", "Apply for leave"),
    ("elm.leave.approve", "Review, recommend or sanction leave requests"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

_RESIDENT = ["elm.leave.view", "elm.leave.view_self", "elm.leave.create"]
_WARDEN = [*_RESIDENT, "elm.leave.approve"]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "faculty": _RESIDENT,
    "staff": _RESIDENT,
    "HOD": _WARDEN,
    "Deputy Registrar": _WARDEN,
    "Dean": _WARDEN,
    "Registrar": _WARDEN,
    "Director": _WARDEN,
}
