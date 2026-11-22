MODULE = {
    "code": "badms",
    "label": "Backup and Data Management",
    "icon": "FaDatabase",
    "base_path": "/badms",
    "nav_section": "Operations",
    "sort_order": 40,
    "status": "planned",
}

NAV_ITEMS = [
    {"code": "badms.backups", "label": "Backups", "icon": "FaDatabase",
     "to": "/badms/backups", "required_permission": "badms.backup.view",
     "sort_order": 10},
    {"code": "badms.archives", "label": "Secure Archives", "icon": "FaArchive",
     "to": "/badms/archives", "required_permission": "badms.archive.view",
     "sort_order": 20},
    {"code": "badms.restores", "label": "Restoration", "icon": "FaUndoAlt",
     "to": "/badms/restores", "required_permission": "badms.restore.view",
     "sort_order": 30},
    {"code": "badms.extensions", "label": "Storage Extensions",
     "icon": "FaHdd", "to": "/badms/storage-extensions",
     "required_permission": "badms.storage_extension.view", "sort_order": 40},
    {"code": "badms.schedules", "label": "Schedules", "icon": "FaCalendarAlt",
     "to": "/badms/schedules", "required_permission": "badms.schedule.view",
     "sort_order": 50},
    {"code": "badms.audit", "label": "Audit History", "icon": "FaListAlt",
     "to": "/badms/audit", "required_permission": "badms.audit_event.view",
     "sort_order": 60},
    {"code": "badms.reports", "label": "Reports", "icon": "FaChartBar",
     "to": "/badms/reports", "required_permission": "badms.report.view",
     "sort_order": 70},
    {"code": "badms.security", "label": "Security Policies",
     "icon": "FaShieldAlt", "to": "/badms/security-policies",
     "required_permission": "badms.security_policy.manage", "sort_order": 80},
]

PERMISSIONS = [
    ("badms.backup.view", "View authorized backup history"),
    ("badms.backup.create", "Trigger a manual backup"),
    ("badms.schedule.view", "View backup schedules"),
    ("badms.schedule.create", "Create a backup schedule"),
    ("badms.schedule.update", "Update a backup schedule"),
    ("badms.archive.view", "View authorized archival requests"),
    ("badms.archive.create", "Submit an archival request"),
    ("badms.archive.review", "Review an archival request"),
    ("badms.archive.approve", "Decide an archival request"),
    ("badms.archive.assign", "Assign an authoritative classification"),
    ("badms.encryption.manage", "Configure Sensitive-data encryption"),
    ("badms.restore.view", "View authorized restoration requests"),
    ("badms.restore.create", "Request restoration"),
    ("badms.restore.approve", "Approve Sensitive-data restoration"),
    ("badms.restore.restore", "Execute an approved restoration"),
    ("badms.storage_extension.view", "View authorized storage requests"),
    ("badms.storage_extension.create", "Request a storage extension"),
    ("badms.storage_extension.review", "Review a storage extension request"),
    ("badms.storage_extension.approve", "Decide a storage extension request"),
    ("badms.audit_event.view", "View authorized audit history"),
    ("badms.audit_event.create", "Record an audit event"),
    ("badms.report.view", "View authorized operational reports"),
    ("badms.security_policy.manage", "Manage BADMS security policy versions"),
]

SYSTEM_PERMISSIONS = [
    "badms.audit_event.create",
]

SCOPE_PERMISSIONS = [
    "badms.archive.view",
    "badms.backup.view",
    "badms.report.view",
    "badms.restore.view",
    "badms.restore.restore",
    "badms.storage_extension.view",
    "badms.audit_event.view",
]

_REQUESTER = [
    "badms.backup.view",
    "badms.archive.view", "badms.archive.create",
    "badms.restore.view", "badms.restore.create", "badms.restore.restore",
    "badms.storage_extension.view", "badms.storage_extension.create",
]
_SYSADMIN = [
    "badms.backup.view", "badms.backup.create",
    "badms.schedule.view", "badms.schedule.create", "badms.schedule.update",
    "badms.archive.view", "badms.archive.review", "badms.archive.assign",
    "badms.restore.view", "badms.restore.approve", "badms.restore.restore",
    "badms.audit_event.view", "badms.report.view",
]
_SUPER_ADMIN = [
    *_SYSADMIN, "badms.schedule.view", "badms.schedule.create",
    "badms.schedule.update", "badms.archive.view", "badms.archive.create",
    "badms.report.view",
]
_IT_SECURITY = [
    "badms.archive.view", "badms.encryption.manage",
    "badms.security_policy.manage",
    "badms.audit_event.view", "badms.report.view",
]
_HOD = [
    "badms.archive.view", "badms.archive.review", "badms.archive.approve",
    "badms.storage_extension.view", "badms.storage_extension.review",
    "badms.storage_extension.approve", "badms.report.view",
]

ROLE_GRANTS = {
    "student": _REQUESTER,
    "faculty": _REQUESTER,
    "staff": _REQUESTER,
    "SysAdmin": _SYSADMIN,
    "Super Admin": _SUPER_ADMIN,
    "IT Security Team": _IT_SECURITY,
    "HOD (CSE)": _HOD,
    "HOD (ECE)": _HOD,
    "HOD (ME)": _HOD,
    "HOD (Design)": _HOD,
    "HOD (NS)": _HOD,
    "HOD (Liberal Arts)": _HOD,
}
