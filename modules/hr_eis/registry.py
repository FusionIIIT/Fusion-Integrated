# modules/hr_eis/registry.py
"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "hr_eis",
    "label": "HR & Employee Information",
    "icon": "User",
    "base_path": "/hr-eis",
    "nav_section": "Administration",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "hr_eis.profile",
        "label": "My Profile",
        "icon": "User",
        "to": "/hr-eis/profile",
        "required_permission": "hr_eis.profile.view_self",
        "sort_order": 10,
    },
    {
        "code": "hr_eis.directory",
        "label": "Employee Directory",
        "icon": "Users",
        "to": "/hr-eis/directory",
        "required_permission": "hr_eis.profile.view_all",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    {
        "code": "hr_eis.profile.view_self",
        "label": "View own employee profile",
        "description": "Allows an employee to view their own profile and work experiences.",
    },
    {
        "code": "hr_eis.profile.manage_self",
        "label": "Manage own employee experiences",
        "description": "Allows an employee to create or remove their own work experiences.",
    },
    {
        "code": "hr_eis.profile.view_all",
        "label": "View all employee profiles",
        "description": "Allows HR/admin staff to search and view all employee profiles.",
    },
]
