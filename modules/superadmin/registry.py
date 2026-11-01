"""Super Admin module registry definition for Fusion ERP."""

MODULE = {
    "code": "superadmin",
    "label": "Super Admin",
    "icon": "ShieldCheck",
    "base_path": "/superadmin",
    "nav_section": "Administration",
    "sort_order": 5,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "superadmin.users",
        "label": "User Accounts",
        "icon": "Users",
        "to": "/superadmin/users",
        "required_permission": "superadmin.user.manage",
        "sort_order": 1,
    },
]

PERMISSIONS = [
    ("superadmin.user.manage", "Create, maintain, and archive user accounts"),
    ("superadmin.role.manage", "Assign and revoke additional roles"),
    ("superadmin.audit.view", "Inspect system-wide audit logs"),
]

SYSTEM_PERMISSIONS: list[str] = []

ROLE_GRANTS = {
    "super_admin": [
        "superadmin.user.manage",
        "superadmin.role.manage",
        "superadmin.audit.view",
    ],
    "Director": [
        "superadmin.user.manage",
        "superadmin.role.manage",
        "superadmin.audit.view",
    ],
}
