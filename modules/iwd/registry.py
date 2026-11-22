"""What the server tells the shell about Institute Works Department."""

MODULE = {
    "code": "iwd",
    "label": "Institute Works",
    "icon": "Wrench",
    "base_path": "/iwd",
    "nav_section": "Institute Works",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "iwd.complaints",
        "label": "Maintenance Complaints",
        "icon": "ClipboardText",
        "to": "/iwd/complaints",
        "required_permission": "iwd.complaint.view",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("iwd.complaint.view", "View maintenance complaints"),
    ("iwd.complaint.create", "Submit maintenance complaints"),
    ("iwd.complaint.manage", "Manage complaints and estimates"),
    ("iwd.complaint.approve", "Approve works and estimates"),
    ("iwd.complaint.audit", "Audit and verify final bills"),
    ("iwd.complaint.settle", "Settle payment accounts"),
]

SYSTEM_PERMISSIONS = []

_USER_PERMS = [
    "iwd.complaint.view",
    "iwd.complaint.create",
]

_ENGINEER_PERMS = [
    "iwd.complaint.view",
    "iwd.complaint.create",
    "iwd.complaint.manage",
]

_APPROVER_PERMS = [
    "iwd.complaint.view",
    "iwd.complaint.approve",
]

ROLE_GRANTS = {
    "student": _USER_PERMS,
    "faculty": _USER_PERMS,
    "staff": _USER_PERMS,
    "Director": _APPROVER_PERMS,
    "HOD": _APPROVER_PERMS,
    "Dean": ["iwd.complaint.view"],
}
