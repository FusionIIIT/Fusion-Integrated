"""What ELM tells the shell and the IAM: its module, permissions and who holds them."""

MODULE = {
    "code": "elm", "label": "Leave Management", "icon": "CalendarBlank",
    "base_path": "/elm", "nav_section": "Leave", "sort_order": 40, "status": "active",
}

#: No client screens yet; add an item here together with its route in the client.
NAV_ITEMS: list[dict] = []

PERMISSIONS = [
    ("elm.leave.apply", "Apply for, modify, withdraw and cancel one's own leave"),
    ("elm.leave.view", "View one's own leave, balances and notifications"),
    ("elm.leave.review", "Unit Head: review leave in one's unit and verify resumption"),
    ("elm.leave.route", "Establishment: route higher-sanction leave to its authority"),
    ("elm.leave.sanction", "Take the final sanction decision on higher-sanction leave"),
    ("elm.leave.self_sanction", "Director: sanction one's own leave"),
    ("elm.leave.administer", "Record offline leave, maintain the calendar, run year end"),
]

SYSTEM_PERMISSIONS: list[str] = []

_EMPLOYEE = ["elm.leave.apply", "elm.leave.view"]
_UNIT_HEAD = [*_EMPLOYEE, "elm.leave.review"]
_ESTABLISHMENT = [*_EMPLOYEE, "elm.leave.route"]
_SANCTION = [*_EMPLOYEE, "elm.leave.sanction"]
_DIRECTOR = [*_EMPLOYEE, "elm.leave.self_sanction"]
_ADMIN = [*_EMPLOYEE, "elm.leave.administer"]

#: Keyed by the designation name as it exists in globals_designation (20 characters at most).
ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Unit Head": _UNIT_HEAD,
    "Deputy Registrar": _ESTABLISHMENT,
    "Dean Academic": _SANCTION,
    "Registrar": _SANCTION,
    "Director": _DIRECTOR,
    "Leave Administrator": _ADMIN,
    "acadadmin": _ADMIN,
}
