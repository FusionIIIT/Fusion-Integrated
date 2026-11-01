"""System Admin Module Registry and Navigation Metadata.

Provides the server-driven navigation and permission catalogue as required
by ADR-0010 and the Super Admin specification baseline.
"""

MODULE = {
    "code": "systemadmin",
    "label": "System Administration",
    "icon": "FaShieldAlt",
    "base_path": "/systemadmin",
    "nav_section": "Administration",
    "sort_order": 1,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "systemadmin.dashboard",
        "label": "Dashboard",
        "icon": "FaChartPie",
        "to": "/systemadmin/dashboard",
        "required_permission": "systemadmin.dashboard.view",
        "sort_order": 10,
    },
    {
        "code": "systemadmin.users",
        "label": "User Directory",
        "icon": "FaUsers",
        "to": "/systemadmin/users",
        "required_permission": "systemadmin.user.view",
        "sort_order": 20,
    },
    {
        "code": "systemadmin.roles",
        "label": "Role Directory",
        "icon": "FaIdBadge",
        "to": "/systemadmin/roles",
        "required_permission": "systemadmin.role.view",
        "sort_order": 30,
    },
    {
        "code": "systemadmin.assignments",
        "label": "Role Assignments",
        "icon": "FaUserCheck",
        "to": "/systemadmin/assignments",
        "required_permission": "systemadmin.role.assign",
        "sort_order": 40,
    },
    {
        "code": "systemadmin.archival",
        "label": "Data & User Archival",
        "icon": "FaArchive",
        "to": "/systemadmin/archival",
        "required_permission": "systemadmin.archive.view",
        "sort_order": 50,
    },
    {
        "code": "systemadmin.audit",
        "label": "Audit Logs",
        "icon": "FaClipboardList",
        "to": "/systemadmin/audit",
        "required_permission": "systemadmin.audit.view",
        "sort_order": 60,
    },
    {
        "code": "systemadmin.reports",
        "label": "Audit Reports",
        "icon": "FaChartBar",
        "to": "/systemadmin/reports",
        "required_permission": "systemadmin.audit.report",
        "sort_order": 70,
    },
    {
        "code": "systemadmin.config",
        "label": "System Configuration",
        "icon": "FaCog",
        "to": "/systemadmin/configuration",
        "required_permission": "systemadmin.config.manage",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("systemadmin.dashboard.view", "View the Super Admin monitoring dashboard and metrics"),
    ("systemadmin.user.view", "View basic user profiles and directory information"),
    ("systemadmin.user.create", "Create Student, Faculty, and Staff basic-user accounts"),
    ("systemadmin.user.edit", "Update editable basic-user profile information"),
    ("systemadmin.user.status", "Deactivate and reactivate basic-user accounts"),
    ("systemadmin.user.bulk", "Execute bulk CSV user creation and batch status operations"),
    ("systemadmin.role.view", "Inspect system-maintained role definitions and availability"),
    ("systemadmin.role.assign", "Assign additional roles to eligible basic users"),
    ("systemadmin.role.reassign", "Reassign active roles to new holders with work handover"),
    ("systemadmin.role.revoke", "Revoke active and scheduled role assignments early"),
    ("systemadmin.role.extend", "Extend validity of time-bound role assignments"),
    ("systemadmin.archive.view", "Search and view archived users and historical records"),
    ("systemadmin.archive.execute", "Archive eligible deactivated users and historical data"),
    ("systemadmin.archive.restore", "Restore eligible archived users and historical datasets"),
    ("systemadmin.purge.request", "Submit dual-authorization permanent data purge requests"),
    ("systemadmin.purge.authorize", "Authorize or reject permanent data purge requests as IT Head"),
    ("systemadmin.audit.view", "Inspect immutable Super Admin audit logs"),
    ("systemadmin.audit.report", "Generate and export tabular and graphical audit reports"),
    ("systemadmin.config.manage", "Configure permitted system-wide parameters"),
]

SYSTEM_PERMISSIONS = [
    "systemadmin.role.activate_scheduled",
    "systemadmin.role.auto_expire",
    "systemadmin.archive.finalize_non_restorable",
]

_SUPER_ADMIN = [
    "systemadmin.dashboard.view",
    "systemadmin.user.view",
    "systemadmin.user.create",
    "systemadmin.user.edit",
    "systemadmin.user.status",
    "systemadmin.user.bulk",
    "systemadmin.role.view",
    "systemadmin.role.assign",
    "systemadmin.role.reassign",
    "systemadmin.role.revoke",
    "systemadmin.role.extend",
    "systemadmin.archive.view",
    "systemadmin.archive.execute",
    "systemadmin.archive.restore",
    "systemadmin.purge.request",
    "systemadmin.audit.view",
    "systemadmin.audit.report",
    "systemadmin.config.manage",
]

_IT_HEAD = [
    "systemadmin.dashboard.view",
    "systemadmin.archive.view",
    "systemadmin.purge.authorize",
    "systemadmin.audit.view",
]

ROLE_GRANTS = {
    "Super Admin": _SUPER_ADMIN,
    "IT Head": _IT_HEAD,
}
