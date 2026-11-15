"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "system_admin",
    "label": "System Admin",
    "icon": "FaShieldAlt",
    "base_path": "/admin",
    "nav_section": "Administration",
    "sort_order": 99,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "system_admin.dashboard",
        "label": "Overview",
        "icon": "FaThLarge",
        "to": "/admin/dashboard",
        "required_permission": "system_admin.dashboard.view",
        "sort_order": 10,
    },
    {
        "code": "system_admin.users",
        "label": "User Accounts",
        "icon": "FaUsers",
        "to": "/admin/users",
        "required_permission": "system_admin.user.view",
        "sort_order": 20,
    },
    {
        "code": "system_admin.roles",
        "label": "Roles & Delegation",
        "icon": "FaIdBadge",
        "to": "/admin/roles",
        "required_permission": "system_admin.role.view",
        "sort_order": 30,
    },
    {
        "code": "system_admin.archival",
        "label": "Archival & Purge",
        "icon": "FaArchive",
        "to": "/admin/archival",
        "required_permission": "system_admin.archival.view",
        "sort_order": 40,
    },
    {
        "code": "system_admin.audit",
        "label": "Audit Trail",
        "icon": "FaHistory",
        "to": "/admin/audit",
        "required_permission": "system_admin.audit.view",
        "sort_order": 50,
    },
    {
        "code": "system_admin.settings",
        "label": "System Parameters",
        "icon": "FaCog",
        "to": "/admin/settings",
        "required_permission": "system_admin.config.view",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("system_admin.dashboard.view", "View administrative dashboard and telemetry"),
    ("system_admin.user.view", "View basic user directory and profiles"),
    ("system_admin.user.manage", "Create, update, and change status of user accounts"),
    ("system_admin.role.view", "View role definitions and user assignments"),
    ("system_admin.role.manage", "Assign, reassign, extend, and revoke user roles"),
    ("system_admin.archival.view", "View archived accounts and retention status"),
    ("system_admin.archival.manage", "Archive or restore accounts within window"),
    ("system_admin.purge.request", "Initiate permanent purge requests"),
    ("system_admin.purge.authorize", "Authorize or reject permanent purge (IT Head)"),
    ("system_admin.audit.view", "Inspect system security and administrative audit logs"),
    ("system_admin.config.view", "View dynamic system runtime parameters"),
    ("system_admin.config.manage", "Modify dynamic system runtime parameters"),
]

SYSTEM_PERMISSIONS = [
    "system_admin.archival.manage",
]

_ADMIN_PERMS = [
    "system_admin.dashboard.view",
    "system_admin.user.view",
    "system_admin.user.manage",
    "system_admin.role.view",
    "system_admin.role.manage",
    "system_admin.archival.view",
    "system_admin.archival.manage",
    "system_admin.purge.request",
    "system_admin.audit.view",
    "system_admin.config.view",
    "system_admin.config.manage",
]

_IT_HEAD_PERMS = [
    "system_admin.dashboard.view",
    "system_admin.purge.authorize",
    "system_admin.audit.view",
]

ROLE_GRANTS = {
    "super_admin": _ADMIN_PERMS,
    "system_admin": _ADMIN_PERMS,
    "it_head": _IT_HEAD_PERMS,
    "director": _IT_HEAD_PERMS,
}
