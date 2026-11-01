MODULE = {
    "code": "super_admin",
    "label": "Super Admin",
    "base_path": "/super_admin",
    "status": "active",
}

NAV_ITEMS = [
    {"code": "super_admin.users", "label": "User Management", "icon": "Users", "to": "/super_admin/users", "required_permission": "super_admin.user.manage", "sort_order": 1},
    {"code": "super_admin.roles", "label": "Role Control", "icon": "Key", "to": "/super_admin/roles", "required_permission": "super_admin.role.manage", "sort_order": 2},
    {"code": "super_admin.audit", "label": "Audit Logs", "icon": "FileText", "to": "/super_admin/audit", "required_permission": "super_admin.audit.view", "sort_order": 3},
]

PERMISSIONS = [
    ("super_admin.user.manage", "Manage basic user accounts"),
    ("super_admin.role.manage", "Assign and revoke roles"),
    ("super_admin.audit.view", "View audit logs"),
]

ROLE_GRANTS = {
    "super_admin": [
        "super_admin.user.manage",
        "super_admin.role.manage",
        "super_admin.audit.view",
    ],
}
