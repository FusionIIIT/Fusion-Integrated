"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "super_admin", "label": "Super Admin", "icon": "ShieldCheck",
    "base_path": "/super_admin", "nav_section": "Admin", "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("super_admin.user.create", "Create basic user account"),
    ("super_admin.user.deactivate", "Deactivate user account"),
    ("super_admin.user.reactivate", "Reactivate user account"),
    ("super_admin.role.assign", "Assign additional role"),
    ("super_admin.role.reassign", "Reassign existing role"),
    ("super_admin.role.revoke", "Revoke active role"),
    ("super_admin.archive.user", "Archive user account"),
    ("super_admin.archive.restore", "Restore archived user"),
    ("super_admin.archive.purge", "Request permanent data purge"),
    ("super_admin.audit.view", "View system audit logs"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "super_admin": [
        "super_admin.user.create",
        "super_admin.user.deactivate",
        "super_admin.user.reactivate",
        "super_admin.role.assign",
        "super_admin.role.reassign",
        "super_admin.role.revoke",
        "super_admin.archive.user",
        "super_admin.archive.restore",
        "super_admin.archive.purge",
        "super_admin.audit.view",
    ],
}
