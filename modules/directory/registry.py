"""Permissions this module recognises. No nav: it has no screens of its own."""

PERMISSIONS = [
    ("directory.user.search", "Search the institute directory"),
]

SYSTEM_PERMISSIONS = []

_STAFF = ["directory.user.search"]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "placement_officer": _STAFF,
    "placement_coordinator": _STAFF,
    "placement_chairman": _STAFF,
    "Dean Academic": _STAFF,
    "acadadmin": _STAFF,
}
