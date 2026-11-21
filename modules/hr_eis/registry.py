MODULE = {
    "code": "hr_eis",
    "label": "HR & Employee Information",
    "icon": "Users",
    "base_path": "/hr-eis",
    "nav_section": "Administration",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "label": "Employees",
        "to": "/hr-eis/employees",
        "icon": "Users",
    },
    {
        "label": "Departments",
        "to": "/hr-eis/departments",
        "icon": "Building2",
    },
    {
        "label": "Positions",
        "to": "/hr-eis/positions",
        "icon": "Briefcase",
    },
]
PERMISSIONS = []
SYSTEM_PERMISSIONS = []
ROLE_GRANTS = {}
