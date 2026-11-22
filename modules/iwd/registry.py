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

# Back-office only — no IAM designation holds these directly
SYSTEM_PERMISSIONS = [
    "iwd.complaint.audit",
    "iwd.complaint.settle",
]

ROLE_GRANTS = {
    "student": [
        "iwd.complaint.view",
        "iwd.complaint.create",
    ],
    "acadadmin": [
        "iwd.complaint.view",
        "iwd.complaint.create",
        "iwd.complaint.manage",
    ],
    "Dean Academic": [
        "iwd.complaint.view",
        "iwd.complaint.approve",
    ],
}
