"""Backup and Database Archive Management System (BADMS) module registry."""

MODULE = {
    "code": "badms",
    "label": "Backup & Archive",
    "icon": "Database",
    "base_path": "/badms",
    "nav_section": "System Services",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "badms.archives",
        "label": "My Archives",
        "icon": "Archive",
        "to": "/badms/archives",
        "required_permission": "badms.archive.view_self",
        "sort_order": 10,
    },
    {
        "code": "badms.hod_review",
        "label": "HoD Review",
        "icon": "CheckSquare",
        "to": "/badms/hod-review",
        "required_permission": "badms.archive.review",
        "sort_order": 20,
    },
    {
        "code": "badms.classification",
        "label": "Classification",
        "icon": "Tag",
        "to": "/badms/classification",
        "required_permission": "badms.archive.classify",
        "sort_order": 30,
    },
    {
        "code": "badms.security",
        "label": "Security & Encryption",
        "icon": "Shield",
        "to": "/badms/security",
        "required_permission": "badms.archive.encrypt",
        "sort_order": 40,
    },
    {
        "code": "badms.backups",
        "label": "Backups & Schedules",
        "icon": "HardDrive",
        "to": "/badms/backups",
        "required_permission": "badms.backup.view",
        "sort_order": 50,
    },
    {
        "code": "badms.restorations",
        "label": "Restorations",
        "icon": "RotateCcw",
        "to": "/badms/restorations",
        "required_permission": "badms.restoration.view_self",
        "sort_order": 60,
    },
    {
        "code": "badms.storage",
        "label": "Storage Quota",
        "icon": "Server",
        "to": "/badms/storage",
        "required_permission": "badms.storage.view_self",
        "sort_order": 70,
    },
    {
        "code": "badms.audit_reports",
        "label": "Audit & Reports",
        "icon": "FileText",
        "to": "/badms/audit-reports",
        "required_permission": "badms.report.view",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("badms.archive.view_self", "View own archive requests"),
    ("badms.archive.create", "Submit an archival request"),
    ("badms.archive.view", "View department or institute archive requests"),
    ("badms.archive.review", "Review department archive requests as HoD"),
    ("badms.archive.classify", "Assign authoritative archive classification"),
    ("badms.archive.encrypt", "Configure encryption for sensitive archives"),
    ("badms.archive.special", "Execute special offline archival"),
    ("badms.backup.view", "View backups, history, and schedules"),
    ("badms.backup.create", "Trigger a manual backup"),
    ("badms.backup.manage", "Manage local backup schedules"),
    ("badms.policy.manage", "Manage global backup schedules and policies"),
    ("badms.restoration.view_self", "View own restoration requests"),
    ("badms.restoration.create", "Submit a restoration request"),
    ("badms.restoration.view", "View all restoration requests"),
    ("badms.restoration.approve", "Approve sensitive restoration requests"),
    ("badms.restoration.restore", "Execute a restoration request"),
    ("badms.storage.view_self", "View own storage extension requests"),
    ("badms.storage.create", "Request a storage quota extension"),
    ("badms.storage.view", "View department storage extension requests"),
    ("badms.storage.review", "Review storage extension requests as HoD"),
    ("badms.audit.view", "View BADMS audit logs"),
    ("badms.report.view", "View BADMS operational and department reports"),
]

_USER = [
    "badms.archive.view_self",
    "badms.archive.create",
    "badms.restoration.view_self",
    "badms.restoration.create",
    "badms.storage.view_self",
    "badms.storage.create",
]

_HOD = [
    *_USER,
    "badms.archive.view",
    "badms.archive.review",
    "badms.storage.view",
    "badms.storage.review",
    "badms.report.view",
]

_SYSADMIN = [
    *_USER,
    "badms.archive.view",
    "badms.archive.classify",
    "badms.backup.view",
    "badms.backup.create",
    "badms.backup.manage",
    "badms.restoration.view",
    "badms.restoration.approve",
    "badms.restoration.restore",
    "badms.storage.view",
    "badms.audit.view",
    "badms.report.view",
]

_SUPER_ADMIN = [
    *_SYSADMIN,
    "badms.archive.special",
    "badms.policy.manage",
]

_IT_SECURITY = [
    "badms.archive.view",
    "badms.archive.encrypt",
    "badms.backup.view",
    "badms.restoration.view",
    "badms.audit.view",
    "badms.report.view",
]

_DIRECTOR_IT = [
    "badms.backup.view",
    "badms.report.view",
]

ROLE_GRANTS = {
    "student": _USER,
    "faculty": _USER,
    "staff": _USER,
    "HOD": _HOD,
    "sysadmin": _SYSADMIN,
    "SysAdmin": _SYSADMIN,
    "Super Admin": _SUPER_ADMIN,
    "admin": _SUPER_ADMIN,
    "IT Security": _IT_SECURITY,
    "it_security": _IT_SECURITY,
    "Director of IT": _DIRECTOR_IT,
}
