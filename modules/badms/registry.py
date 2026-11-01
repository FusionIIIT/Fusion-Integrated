"""Module registry for BADMS per ADR-0010.

Defines module navigation, permissions, and role grants.
"""

MODULE_NAME = "badms"
MODULE_LABEL = "Backup & Archival"
MODULE_DESCRIPTION = "Backup and Database Archive Management System"
MODULE_ICON = "database"

NAVIGATION = [
    {
        "label": "Dashboard",
        "url": "/badms/dashboard/",
        "icon": "layout-dashboard",
        "permission": None,
    },
    {
        "label": "Secure Archival",
        "url": "/badms/archival/",
        "icon": "archive",
        "permission": "badms.archival.submit",
    },
    {
        "label": "HoD Approval Queue",
        "url": "/badms/hod-queue/",
        "icon": "clipboard-check",
        "permission": "badms.archival.review_hod",
    },
    {
        "label": "SysAdmin Classification",
        "url": "/badms/classification/",
        "icon": "tag",
        "permission": "badms.archival.classify_sysadmin",
    },
    {
        "label": "Backup Management",
        "url": "/badms/backups/",
        "icon": "hard-drive",
        "permission": "badms.backup.view_history",
    },
    {
        "label": "Restoration Requests",
        "url": "/badms/restoration/",
        "icon": "rotate-ccw",
        "permission": "badms.restoration.request",
    },
    {
        "label": "Audit Logs",
        "url": "/badms/audit/",
        "icon": "shield-alert",
        "permission": "badms.audit.view_operational",
    },
]

PERMISSIONS = [
    ("badms.backup.trigger_manual", "Trigger manual on-demand backup"),
    ("badms.backup.view_history", "View backup execution history and status"),
    ("badms.schedule.manage_local", "Configure dataset-specific local backup schedules"),
    ("badms.schedule.manage_global", "Define institution-wide global backup schedules and default policies"),
    ("badms.archival.submit", "Submit secure archival requests"),
    ("badms.archival.review_hod", "Review and decide archival requests for own department"),
    ("badms.archival.classify_sysadmin", "Assign authoritative classification to approved archival requests"),
    ("badms.archival.configure_encryption", "Configure AES-256 encryption for Sensitive archival data"),
    ("badms.archival.special_operate", "Perform offline-triggered special archival operations"),
    ("badms.storage.request_extension", "Submit storage quota extension request"),
    ("badms.storage.review_extension", "Review departmental storage extension requests"),
    ("badms.storage.monitor_threshold", "Monitor storage quotas and threshold alerts"),
    ("badms.restoration.request", "Request data restoration for archived files"),
    ("badms.restoration.approve_sensitive", "Approve restoration requests for Sensitive data"),
    ("badms.restoration.execute", "Execute technical data restoration"),
    ("badms.audit.view_operational", "View BADMS audit logs and operational reports"),
    ("badms.security.administer", "Manage RBAC permissions and security administration"),
]

ROLE_GRANTS = {
    "student": [
        "badms.archival.submit",
        "badms.storage.request_extension",
        "badms.restoration.request",
    ],
    "faculty": [
        "badms.archival.submit",
        "badms.storage.request_extension",
        "badms.restoration.request",
    ],
    "staff": [
        "badms.archival.submit",
        "badms.storage.request_extension",
        "badms.restoration.request",
    ],
    "hod": [
        "badms.archival.submit",
        "badms.archival.review_hod",
        "badms.storage.request_extension",
        "badms.storage.review_extension",
        "badms.restoration.request",
        "badms.audit.view_operational",
    ],
    "sysadmin": [
        "badms.backup.trigger_manual",
        "badms.backup.view_history",
        "badms.schedule.manage_local",
        "badms.archival.classify_sysadmin",
        "badms.storage.monitor_threshold",
        "badms.restoration.approve_sensitive",
        "badms.restoration.execute",
        "badms.audit.view_operational",
    ],
    "it_security": [
        "badms.archival.configure_encryption",
        "badms.security.administer",
        "badms.audit.view_operational",
    ],
    "superadmin": [
        "badms.backup.trigger_manual",
        "badms.backup.view_history",
        "badms.schedule.manage_local",
        "badms.schedule.manage_global",
        "badms.archival.classify_sysadmin",
        "badms.archival.special_operate",
        "badms.storage.monitor_threshold",
        "badms.restoration.approve_sensitive",
        "badms.restoration.execute",
        "badms.audit.view_operational",
        "badms.security.administer",
    ],
}
