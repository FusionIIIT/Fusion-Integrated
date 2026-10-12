MODULE = {
    "code": "elm",
    "label": "ELM",
    "icon": "Briefcase",
    "base_path": "/elm",
    "nav_section": "ELM",
    "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.leaves", "label": "Leaves", "icon": "ClipboardText", "to": "/elm/leaves", "required_permission": "elm.leave.view", "sort_order": 10},
]

PERMISSIONS = [
    ("elm.leave.view", "See leaves"),
    ("elm.leave.manage", "Create and manage leaves"),
]

ROLE_GRANTS = {
    "student": ["elm.leave.view"],
    "placement_coordinator": ["elm.leave.view", "elm.leave.manage"],
}
