"""Permissions this module recognises. No nav: it has no screens of its own."""

PERMISSIONS = [
    ("elm.leave.apply", "Apply for leave"),
    ("elm.leave.view", "View own leave applications and balances"),
    ("elm.leave.approve", "Approve leave applications"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = ["elm.leave.apply", "elm.leave.view"]
_APPROVER = _EMPLOYEE + ["elm.leave.approve"]

#: Keyed by the designation name as it exists in globals_designation.
#: PLACEHOLDER roles: replace with the designations that should apply/approve.
ROLE_GRANTS = {
    "acadadmin": _APPROVER,
    "Dean Academic": _APPROVER,
}
