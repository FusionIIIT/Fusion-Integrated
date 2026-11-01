"""What the server tells the shell about System Admin (Super Admin).

The administrative control plane for Fusion ERP.
"""

MODULE = {
    "code": "system_admin",
    "label": "System Administrator",
    "icon": "FaUserShield",
    "base_path": "/sysadmin",
    "nav_section": "Administration",
    "sort_order": 1,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "system_admin.dashboard",
        "label": "Admin Dashboard",
        "icon": "FaTachometerAlt",
        "to": "/sysadmin/dashboard",
        "required_permission": "system_admin.audit.view",
        "sort_order": 1,
    },
    {
        "code": "system_admin.users",
        "label": "User Management",
        "icon": "FaUsers",
        "to": "/sysadmin/users",
        "required_permission": "system_admin.user.view",
        "sort_order": 10,
    },
    {
        "code": "system_admin.users.bulk",
        "label": "Bulk Operations",
        "icon": "FaFileUpload",
        "to": "/sysadmin/users/bulk",
        "required_permission": "system_admin.user.bulk_manage",
        "sort_order": 20,
    },
    {
        "code": "system_admin.roles",
        "label": "Role Management",
        "icon": "FaIdBadge",
        "to": "/sysadmin/roles",
        "required_permission": "system_admin.role.view",
        "sort_order": 30,
    },
    {
        "code": "system_admin.archival",
        "label": "Archive Control",
        "icon": "FaArchive",
        "to": "/sysadmin/archival",
        "required_permission": "system_admin.archive.view",
        "sort_order": 40,
    },
    {
        "code": "system_admin.purge",
        "label": "Data Purge",
        "icon": "FaTrashAlt",
        "to": "/sysadmin/purge",
        "required_permission": "system_admin.purge.request",
        "sort_order": 50,
    },
    {
        "code": "system_admin.audit",
        "label": "Audit Logs",
        "icon": "FaHistory",
        "to": "/sysadmin/audit",
        "required_permission": "system_admin.audit.view",
        "sort_order": 60,
    },
    {
        "code": "system_admin.config",
        "label": "System Parameters",
        "icon": "FaCogs",
        "to": "/sysadmin/config",
        "required_permission": "system_admin.config.view",
        "sort_order": 70,
    },
]

SYSTEM_PERMISSIONS = [
    "system_admin.role.auto_expire",
    "system_admin.role.auto_activate",
    "system_admin.archive.auto_finalize",
]

_SUPER_ADMIN_PERMISSIONS = [
    "system_admin.user.view",
    "system_admin.user.create",
    "system_admin.user.update",
    "system_admin.user.deactivate",
    "system_admin.user.reactivate",
    "system_admin.user.bulk_manage",
    "system_admin.role.view",
    "system_admin.role.assign",
    "system_admin.role.reassign",
    "system_admin.role.revoke",
    "system_admin.role.extend",
    "system_admin.archive.view",
    "system_admin.archive.create",
    "system_admin.archive.restore",
    "system_admin.archive.export",
    "system_admin.purge.request",
    "system_admin.audit.view",
    "system_admin.audit.report",
    "system_admin.config.view",
    "system_admin.config.update",
    "system_admin.session.manage",
]

_IT_HEAD_PERMISSIONS = [
    "system_admin.purge.authorize",
    "system_admin.audit.view",
]

_BASIC_USER_PERMISSIONS = [
    "system_admin.role.switch",
]

ROLE_GRANTS = {
    "super_admin": _SUPER_ADMIN_PERMISSIONS,
    "it_head": _IT_HEAD_PERMISSIONS,
    "student": _BASIC_USER_PERMISSIONS,
    "faculty": _BASIC_USER_PERMISSIONS,
    "staff": _BASIC_USER_PERMISSIONS,
}
