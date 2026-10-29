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
    {"code": "elm.leaves", "label": "Leaves", "icon": "ClipboardText", "to": "/elm/leaves", "required_permission": "elm.leave.view_self", "sort_order": 10},
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave requests"),
    ("elm.leave.create", "Create own leave requests"),
    ("elm.leave.view", "View employee leave requests"),
    ("elm.leave.manage", "Manage employee leave requests"),
]

SCOPE_PERMISSIONS = [
    "elm.leave.view_self",
]

ROLE_GRANTS = {
    "faculty": [
        "elm.leave.view_self",
        "elm.leave.create",
    ],
    "staff": [
        "elm.leave.view_self",
        "elm.leave.create",
    ],
    "Dean Academic": [
        "elm.leave.view",
        "elm.leave.manage",
    ],
    "acadadmin": [
        "elm.leave.view",
        "elm.leave.manage",
    ],
}