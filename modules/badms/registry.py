"""BADMS navigation and permission manifest."""

MODULE = {
    "code": "badms",
    "label": "Backup & Archives",
    "icon": "FaLayerGroup",
    "base_path": "/badms",
    "nav_section": "Administration",
    "sort_order": 80,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "badms.dashboard", "label": "Backup & Archives", "icon": "FaLayerGroup",
     "to": "/badms", "required_permission": "badms.backup.view", "sort_order": 10},
]

PERMISSIONS = [
    ("badms.backup.view", "View authorized backup history"),
    ("badms.backup.run", "Run a manual database backup"),
    ("badms.archive.submit", "Submit and track archival requests"),
    ("badms.archive.review", "Review archival requests"),
    ("badms.archive.classify", "Assign authoritative archival classification"),
    ("badms.archive.secure", "Complete Sensitive-data encryption and archive creation"),
    ("badms.audit.view", "View authorized BADMS audit history"),
]

ROLE_GRANTS = {
    "SysAdmin": ["badms.backup.view", "badms.backup.run", "badms.archive.classify", "badms.audit.view"],
    "Super Admin": ["badms.backup.view", "badms.backup.run", "badms.archive.classify", "badms.audit.view"],
    "HoD": ["badms.backup.view", "badms.archive.review", "badms.audit.view"],
    "IT Security Team": ["badms.backup.view", "badms.archive.secure", "badms.audit.view"],
    "student": ["badms.backup.view", "badms.archive.submit"],
    "faculty": ["badms.backup.view", "badms.archive.submit"],
    "staff": ["badms.backup.view", "badms.archive.submit"],
}
