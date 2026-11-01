"""Super Admin module's currently implemented routes and grants.

The identity directory and role catalog remain owned by IAM. The module only
publishes the permission-gated UI/API that is backed by documented IAM routes.
"""

MODULE = {
    "code": "superadmin",
    "label": "Super Admin",
    "icon": "FaLayerGroup",
    "base_path": "/superadmin",
    "nav_section": "Super Admin",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "superadmin.users",
        "label": "Users",
        "icon": "FaUsers",
        "to": "/superadmin/users",
        "required_permission": "superadmin.user.view",
        "sort_order": 10,
    },
    {
        "code": "superadmin.roles",
        "label": "Roles",
        "icon": "FaIdBadge",
        "to": "/superadmin/roles",
        "required_permission": "superadmin.role.view",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("superadmin.user.view", "View the institute user directory"),
    ("superadmin.user.create", "Create supported faculty and staff users"),
    ("superadmin.user.update", "Request an IAM password reset"),
    ("superadmin.user.bulk_create", "Import users through the IAM service"),
    ("superadmin.role.view", "View IAM role metadata and user roles"),
    ("superadmin.role.assign", "Replace a user's role assignments through IAM"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "Super Admin": [permission for permission, _label in PERMISSIONS],
}
