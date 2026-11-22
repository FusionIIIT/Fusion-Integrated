"""System Admin module registration and menu definitions (ADR-0010)."""
from __future__ import annotations

MODULE = {
    "code": "system_admin",
    "label": "System Admin",
    "icon": "ShieldCheck",
    "base_path": "/system_admin",
    "nav_section": "Administration",
    "sort_order": 1,
    "status": "active",
}

#: All permissions recognized by System Admin.
#: Verbs follow closed list: view, add, change, delete, manage.
PERMISSIONS = [
    ("system_admin.user.view", "View users and profiles"),
    ("system_admin.user.add", "Create basic user accounts"),
    ("system_admin.user.change", "Update profiles and activation status"),
    ("system_admin.role.view", "View role definitions and availability"),
    ("system_admin.role.manage", "Assign, reassign, revoke, and extend roles"),
    ("system_admin.archive.view", "View archived users and historical records"),
    ("system_admin.archive.manage", "Execute archival, restoration, and purge requests"),
    ("system_admin.audit.view", "View audit logs and generate reports"),
    ("system_admin.config.change", "Configure permitted system parameters"),
]

SYSTEM_PERMISSIONS: list[str] = []

_ADMIN_ALL = [p[0] for p in PERMISSIONS]
_IT_HEAD = [
    "system_admin.archive.view",
    "system_admin.archive.manage",
]

#: Designation grants seeded into IAM.
ROLE_GRANTS = {
    "System Administrator": _ADMIN_ALL,
    "Director": _ADMIN_ALL,
    "Registrar": _ADMIN_ALL,
    "unit_head": _ADMIN_ALL,
    "faculty": _ADMIN_ALL,
    "IT Head": _IT_HEAD,
}

NAV_ITEMS = [
    {
        "code": "system_admin.dashboard",
        "label": "Dashboard",
        "icon": "Gauge",
        "to": "/system_admin",
        "required_permission": "system_admin.user.view",
        "sort_order": 1,
    },
    {
        "code": "system_admin.users",
        "label": "User Management",
        "icon": "Users",
        "to": "/system_admin/users",
        "required_permission": "system_admin.user.view",
        "sort_order": 10,
    },
    {
        "code": "system_admin.roles",
        "label": "Role Directory",
        "icon": "IdentificationBadge",
        "to": "/system_admin/roles",
        "required_permission": "system_admin.role.view",
        "sort_order": 20,
    },
    {
        "code": "system_admin.archives",
        "label": "Archive Control",
        "icon": "Archive",
        "to": "/system_admin/archives",
        "required_permission": "system_admin.archive.view",
        "sort_order": 30,
    },
    {
        "code": "system_admin.audit",
        "label": "Audit Logs",
        "icon": "ListBullets",
        "to": "/system_admin/audit",
        "required_permission": "system_admin.audit.view",
        "sort_order": 40,
    },
    {
        "code": "system_admin.config",
        "label": "System Parameters",
        "icon": "Gear",
        "to": "/system_admin/config",
        "required_permission": "system_admin.config.change",
        "sort_order": 50,
    },
]
