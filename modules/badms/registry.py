MODULE = {
    "code": "badms",
    "label": "Backup & Database Archive Management System",
    "icon": "Database",
    "base_path": "/badms",
    "nav_section": "Administration",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "badms.backups",
        "label": "Backups",
        "icon": "HardDrives",
        "to": "/badms/backups",
        "required_permission": "badms.backup.view",
        "sort_order": 10,
    },
    {
        "code": "badms.schedules",
        "label": "Backup Schedules",
        "icon": "CalendarCheck",
        "to": "/badms/schedules",
        "required_permission": "badms.backup.view",
        "sort_order": 20,
    },
    {
        "code": "badms.archival_requests",
        "label": "Secure Archival",
        "icon": "Archive",
        "to": "/badms/archival-requests",
        "required_permission": "badms.archival.view",
        "sort_order": 30,
    },
    {
        "code": "badms.storage_extensions",
        "label": "Storage Extensions",
        "icon": "CloudArrowUp",
        "to": "/badms/storage-extensions",
        "required_permission": "badms.storage.view",
        "sort_order": 40,
    },
    {
        "code": "badms.restorations",
        "label": "Restorations",
        "icon": "ArrowCounterClockwise",
        "to": "/badms/restorations",
        "required_permission": "badms.restoration.view",
        "sort_order": 50,
    },
    {
        "code": "badms.audit_logs",
        "label": "Audit Logs",
        "icon": "ShieldCheck",
        "to": "/badms/audit-logs",
        "required_permission": "badms.audit.view",
        "sort_order": 60,
    },
    {
        "code": "badms.reports",
        "label": "Reports",
        "icon": "ChartBar",
        "to": "/badms/reports",
        "required_permission": "badms.report.view",
        "sort_order": 70,
    },
    {
        "code": "badms.security_policies",
        "label": "Security Policies",
        "icon": "LockKey",
        "to": "/badms/security-policies",
        "required_permission": "badms.security.manage",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("badms.backup.view", "View backup status, history, and schedules"),
    ("badms.backup.manage", "Trigger manual backups and configure local schedules"),
    ("badms.backup_policy.manage", "Define global backup schedules and default policies"),
    ("badms.archival.view", "View secure archival requests and status"),
    ("badms.archival.create", "Submit secure archival requests"),
    ("badms.archival.approve", "Approve or reject archival requests within department"),
    ("badms.archival.review", "Review and assign authoritative data classification"),
    ("badms.archival.manage", "Execute special archival operations"),
    ("badms.storage.view", "View storage extension requests and quota status"),
    ("badms.storage.create", "Submit storage extension requests"),
    ("badms.storage.approve", "Approve or reject storage extension requests within department"),
    ("badms.restoration.view", "View data restoration requests and history"),
    ("badms.restoration.create", "Submit data restoration requests"),
    ("badms.restoration.approve", "Approve or reject sensitive data restoration requests"),
    ("badms.restoration.restore", "Execute technical data restoration"),
    ("badms.security.manage", "Configure encryption for sensitive archives and security policies"),
    ("badms.audit.view", "View system audit logs and data activity history"),
    ("badms.report.view", "View department data management and operational reports"),
]

SYSTEM_PERMISSIONS = [
    "badms.backup.auto_execute",
    "badms.storage.auto_monitor",
    "badms.failure.auto_escalate",
]

SCOPE_PERMISSIONS: list[str] = []

_STUDENT = [
    "badms.archival.view",
    "badms.archival.create",
    "badms.storage.view",
    "badms.storage.create",
    "badms.restoration.view",
    "badms.restoration.create",
]

_FACULTY = _STUDENT
_STAFF = _STUDENT

_HOD = [
    "badms.backup.view",
    "badms.archival.view",
    "badms.archival.create",
    "badms.archival.approve",
    "badms.storage.view",
    "badms.storage.create",
    "badms.storage.approve",
    "badms.restoration.view",
    "badms.restoration.create",
    "badms.report.view",
]

_SYSADMIN = [
    "badms.backup.view",
    "badms.backup.manage",
    "badms.archival.view",
    "badms.archival.review",
    "badms.storage.view",
    "badms.restoration.view",
    "badms.restoration.approve",
    "badms.restoration.restore",
    "badms.audit.view",
    "badms.report.view",
]

_SUPER_ADMIN = [
    "badms.backup.view",
    "badms.backup.manage",
    "badms.backup_policy.manage",
    "badms.archival.view",
    "badms.archival.manage",
    "badms.storage.view",
    "badms.restoration.view",
    "badms.audit.view",
    "badms.report.view",
]

_IT_SECURITY = [
    "badms.archival.view",
    "badms.security.manage",
    "badms.audit.view",
    "badms.report.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "staff": _STAFF,
    "HOD (CSE)": _HOD,
    "HOD (ECE)": _HOD,
    "HOD (ME)": _HOD,
    "HOD (Design)": _HOD,
    "HOD (NS)": _HOD,
    "HOD (Liberal Arts)": _HOD,
    "HOD": _HOD,
    "acadadmin": _SYSADMIN,
    "SysAdmin": _SYSADMIN,
    "Director": _SUPER_ADMIN,
    "Super Admin": _SUPER_ADMIN,
    "IT Security": _IT_SECURITY,
}


def readiness() -> list[str]:
    """Returns a list of unmet prerequisites for BADMS operational readiness."""
    return []
