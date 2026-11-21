"""BADMS module registry: navigation, permissions, and grants."""

MODULE = {
    "code": "badms",
    "label": "Backup & Archive",
    "icon": "Database",
    "base_path": "/badms",
    "nav_section": "Administration",
    "sort_order": 70,
    "status": "active",
}

NAV_ITEMS = [
    # -- General User Nav Items ---
    {
        "code": "badms.my_archivals",
        "label": "My Archival Requests",
        "icon": "Archive",
        "to": "/badms/archivals",
        "required_permission": "badms.archival.request",
        "sort_order": 10,
    },
    {
        "code": "badms.my_restorations",
        "label": "My Restorations",
        "icon": "ArrowCounterClockwise",
        "to": "/badms/restorations",
        "required_permission": "badms.restoration.request",
        "sort_order": 20,
    },
    {
        "code": "badms.my_storage",
        "label": "Storage Extension",
        "icon": "HardDrives",
        "to": "/badms/storage-extensions",
        "required_permission": "badms.storage.request",
        "sort_order": 30,
    },
    # -- SysAdmin Nav Items ---
    {
        "code": "badms.backups",
        "label": "Backup Operations",
        "icon": "CloudArrowUp",
        "to": "/badms/backups",
        "required_permission": "badms.backup.view",
        "sort_order": 40,
    },
    {
        "code": "badms.schedules",
        "label": "Backup Schedules",
        "icon": "CalendarCheck",
        "to": "/badms/schedules",
        "required_permission": "badms.schedule.view",
        "sort_order": 50,
    },
    # -- HoD Nav Items ---
    {
        "code": "badms.department_approvals",
        "label": "Department Approvals",
        "icon": "CheckSquare",
        "to": "/badms/department-approvals",
        "required_permission": "badms.department.review",
        "sort_order": 60,
    },
    # -- IT Security Nav Items ---
    {
        "code": "badms.security_encryption",
        "label": "Security & Encryption",
        "icon": "ShieldCheck",
        "to": "/badms/security",
        "required_permission": "badms.security.manage",
        "sort_order": 70,
    },
    # -- Audit Nav Items ---
    {
        "code": "badms.audit_logs",
        "label": "Audit Logs",
        "icon": "FileText",
        "to": "/badms/audit-logs",
        "required_permission": "badms.audit.view",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    # Backup & Schedules
    ("badms.backup.view", "View backup operations history and status"),
    ("badms.backup.trigger", "Trigger manual database/system backup"),
    ("badms.schedule.view", "View backup schedules"),
    ("badms.schedule.manage_local", "Create or edit local backup schedule"),
    ("badms.schedule.manage_global", "Create or edit global backup schedule"),
    # Archival
    ("badms.archival.request", "Submit archival request and track status"),
    ("badms.archival.classify_authoritative", "Assign authoritative classification"),
    ("badms.archival.special", "Execute special archival request"),
    # Restoration
    ("badms.restoration.request", "Submit data restoration request"),
    ("badms.restoration.approve_sensitive", "Approve restoration of sensitive data"),
    # Storage Extension
    ("badms.storage.request", "Submit storage quota extension request"),
    ("badms.storage.view_threshold", "Monitor user storage quotas"),
    # Department Head
    ("badms.department.review", "Review department archival and extension requests"),
    ("badms.department.reports", "View departmental backup and archival reports"),
    # Security
    ("badms.security.manage", "Configure encryption and security policies"),
    ("badms.security.audit", "Audit data activity logs for unauthorized access"),
    # Audit & Reporting
    ("badms.audit.view", "View BADMS audit logs and operational history"),
    # Automated system tasks
    ("badms.system.execute_schedule", "Execute scheduled automatic backups"),
    ("badms.system.alert_failure", "Process failure alerts and escalations"),
]

SYSTEM_PERMISSIONS = [
    "badms.system.execute_schedule",
    "badms.system.alert_failure",
]

_USER_PERMS = [
    "badms.archival.request",
    "badms.restoration.request",
    "badms.storage.request",
    "badms.backup.view",
]

_SYSADMIN_PERMS = [
    *_USER_PERMS,
    "badms.backup.trigger",
    "badms.schedule.view",
    "badms.schedule.manage_local",
    "badms.archival.classify_authoritative",
    "badms.restoration.approve_sensitive",
    "badms.storage.view_threshold",
    "badms.audit.view",
]

_SUPERADMIN_PERMS = [
    *_SYSADMIN_PERMS,
    "badms.schedule.manage_global",
    "badms.archival.special",
]

_HOD_PERMS = [
    *_USER_PERMS,
    "badms.department.review",
    "badms.department.reports",
]

_IT_SECURITY_PERMS = [
    *_USER_PERMS,
    "badms.security.manage",
    "badms.security.audit",
    "badms.audit.view",
]

GRANTS = {
    "student": _USER_PERMS,
    "faculty": _USER_PERMS,
    "staff": _USER_PERMS,
    "sysadmin": _SUPERADMIN_PERMS,
    "hod": _HOD_PERMS,
    "it_security": _IT_SECURITY_PERMS,
}
