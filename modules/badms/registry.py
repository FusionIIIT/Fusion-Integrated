"""Server-driven navigation and RBAC configuration for BADMS (ADR-0010)."""

MODULE = {
    "code": "badms",
    "label": "Backup & Database Archive",
    "icon": "FaDatabase",
    "base_path": "/badms",
    "nav_section": "System Administration",
    "sort_order": 45,
    "status": "active",
}

# Navigation items for the sidebar (ADR-0010).
# Empty until React frontend routes are mounted in client/src/modules/badms/routes.tsx.
# The module dashboard is served via Django template at:
# modules/badms/templates/badms/dashboard.html
NAV_ITEMS: list[dict] = []

PERMISSIONS = [
    ("badms.backup.trigger", "Trigger on-demand manual database backups"),
    ("badms.backup.view", "View backup execution history and status"),
    ("badms.schedule.view", "View automated backup schedules"),
    ("badms.schedule.manage", "Create and modify local and global backup schedules"),
    ("badms.archival.submit", "Submit files and metadata for secure archival"),
    ("badms.archival.view", "View secure archival request status and history"),
    ("badms.archival.hod_decide", "Approve or reject departmental secure archival requests"),
    ("badms.archival.classify", "Assign authoritative data classification to archival requests"),
    ("badms.archival.encrypt", "Configure AES-256 encryption and build sensitive archives"),
    ("badms.special_archival.execute", "Execute offline-originated special archival operations"),
    ("badms.storage.view_self", "View own storage usage and quota allocation"),
    ("badms.storage.request_extension", "Request storage quota expansion when full"),
    ("badms.storage.view", "View storage extension requests"),
    ("badms.storage.hod_decide", "Approve or reject departmental storage extensions"),
    ("badms.restoration.request", "Request restoration of archived data"),
    ("badms.restoration.view", "View data restoration request history and status"),
    ("badms.restoration.approve", "Review and approve Sensitive data restoration requests"),
    ("badms.restoration.execute", "Execute technical restoration of archived data"),
    ("badms.audit.view", "View tamper-evident audit logs and activity histories"),
    ("badms.report.departmental", "View departmental data management operational reports"),
    ("badms.report.security", "View security audit reports and unauthorized access alerts"),
    ("badms.report.compliance", "View overall backup compliance and status reports"),
    ("badms.security.manage", "Manage BADMS RBAC permissions and security policies"),
]

SYSTEM_PERMISSIONS = [
    "badms.backup.execute_automatic",
    "badms.storage.monitor_thresholds",
]

_USER = [
    "badms.archival.submit",
    "badms.archival.view",
    "badms.storage.view_self",
    "badms.storage.request_extension",
    "badms.restoration.request",
    "badms.restoration.view",
    "badms.backup.view",
]

_HOD = [
    *_USER,
    "badms.archival.hod_decide",
    "badms.storage.hod_decide",
    "badms.storage.view",
    "badms.report.departmental",
]

_SYSADMIN = [
    *_USER,
    "badms.backup.trigger",
    "badms.backup.view",
    "badms.schedule.view",
    "badms.schedule.manage",
    "badms.archival.classify",
    "badms.restoration.approve",
    "badms.restoration.execute",
    "badms.audit.view",
    "badms.report.compliance",
]

_IT_SECURITY = [
    "badms.archival.encrypt",
    "badms.archival.view",
    "badms.audit.view",
    "badms.report.security",
    "badms.security.manage",
]

_SUPER_ADMIN = [
    *_SYSADMIN,
    "badms.special_archival.execute",
    "badms.security.manage",
]

ROLE_GRANTS = {
    "student": _USER,
    "faculty": _USER,
    "staff": _USER,
    "HOD (CSE)": _HOD,
    "HOD (ECE)": _HOD,
    "HOD (ME)": _HOD,
    "HOD (Design)": _HOD,
    "sysadmin": _SYSADMIN,
    "technical_officer": _SYSADMIN,
    "it_security_lead": _IT_SECURITY,
    "it_security_auditor": _IT_SECURITY,
    "Super Admin": _SUPER_ADMIN,
    "Director": _SUPER_ADMIN,
}
