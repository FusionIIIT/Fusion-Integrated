"""Registry declaration for Super Admin module."""

from __future__ import annotations

MODULE = {
    "code": "superadmin",
    "label": "Super Admin",
    "icon": "ShieldCheck",
    "base_path": "/superadmin",
    "nav_section": "Administration",
    "sort_order": 1,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "superadmin.dashboard",
        "label": "Dashboard",
        "icon": "ChartBar",
        "to": "/superadmin/dashboard",
        "required_permission": "superadmin.user.view",
        "sort_order": 10,
    },
    {
        "code": "superadmin.users",
        "label": "User Accounts",
        "icon": "Users",
        "to": "/superadmin/users",
        "required_permission": "superadmin.user.view",
        "sort_order": 20,
    },
    {
        "code": "superadmin.roles",
        "label": "Role Assignments",
        "icon": "IdentificationBadge",
        "to": "/superadmin/roles",
        "required_permission": "superadmin.role.view",
        "sort_order": 30,
    },
    {
        "code": "superadmin.archive",
        "label": "Archive & Restoration",
        "icon": "Archive",
        "to": "/superadmin/archive",
        "required_permission": "superadmin.archive.view",
        "sort_order": 40,
    },
    {
        "code": "superadmin.purge",
        "label": "Purge Authorizations",
        "icon": "Trash",
        "to": "/superadmin/purge",
        "required_permission": "superadmin.purge.approve",
        "sort_order": 50,
    },
    {
        "code": "superadmin.audit",
        "label": "Audit Logs",
        "icon": "Scroll",
        "to": "/superadmin/audit",
        "required_permission": "superadmin.audit_log.view",
        "sort_order": 60,
    },
    {
        "code": "superadmin.config",
        "label": "System Policy",
        "icon": "GearSix",
        "to": "/superadmin/config",
        "required_permission": "superadmin.system_config.view",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("superadmin.user.view", "View user accounts and profiles"),
    ("superadmin.user.create", "Create new basic user accounts"),
    ("superadmin.user.update", "Update user profiles and statuses"),
    ("superadmin.user.delete", "Deactivate user accounts"),
    ("superadmin.user.restore", "Reactivate or restore user accounts"),
    ("superadmin.user.import", "Bulk import user accounts from CSV"),
    ("superadmin.user.export", "Export user account directories"),
    ("superadmin.role.view", "Inspect role definitions and assignments"),
    ("superadmin.role.assign", "Assign or reassign roles to users"),
    ("superadmin.role.revoke", "Revoke held role assignments"),
    ("superadmin.role.update", "Extend validity of active role assignments"),
    ("superadmin.archive.view", "Search and inspect archived records"),
    ("superadmin.archive.create", "Archive deactivated users or historical data"),
    ("superadmin.archive.restore", "Restore reversible archived users or data"),
    ("superadmin.archive.export", "Export archive status reports"),
    ("superadmin.purge.create", "Request permanent data purge"),
    ("superadmin.purge.approve", "Authorize permanent data purge (IT Head)"),
    ("superadmin.audit_log.view", "Inspect security and audit event logs"),
    ("superadmin.audit_log.export", "Export compliance audit reports"),
    ("superadmin.system_config.view", "View system parameter configurations"),
    ("superadmin.system_config.update", "Update system parameter policies"),
]

SYSTEM_PERMISSIONS = []

_SUPER_ADMIN_PERMISSIONS = [
    "superadmin.user.view",
    "superadmin.user.create",
    "superadmin.user.update",
    "superadmin.user.delete",
    "superadmin.user.restore",
    "superadmin.user.import",
    "superadmin.user.export",
    "superadmin.role.view",
    "superadmin.role.assign",
    "superadmin.role.revoke",
    "superadmin.role.update",
    "superadmin.archive.view",
    "superadmin.archive.create",
    "superadmin.archive.restore",
    "superadmin.archive.export",
    "superadmin.purge.create",
    "superadmin.audit_log.view",
    "superadmin.audit_log.export",
    "superadmin.system_config.view",
    "superadmin.system_config.update",
]

_IT_HEAD_PERMISSIONS = [
    "superadmin.purge.approve",
    "superadmin.audit_log.view",
]

ROLE_GRANTS = {
    "Super Admin": _SUPER_ADMIN_PERMISSIONS,
    "super_admin": _SUPER_ADMIN_PERMISSIONS,
    "iam_admin": _SUPER_ADMIN_PERMISSIONS,
    "IT Head": _IT_HEAD_PERMISSIONS,
    "Director": _IT_HEAD_PERMISSIONS,
}


def readiness() -> list[str]:
    # Returns list of unmet prerequisites before module can be active.
    return []
