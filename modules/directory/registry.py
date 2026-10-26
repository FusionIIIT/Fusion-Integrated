"""Directory permissions and the read-only directory screen."""

MODULE = {
    "code": "directory",
    "label": "Directory",
    "icon": "Users",
    "base_path": "/directory",
    "nav_section": "Institute Services",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "directory.users",
        "label": "People Directory",
        "icon": "Users",
        "to": "/directory",
        "required_permission": "directory.user.search",
        "sort_order": 10,
    },
]

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
