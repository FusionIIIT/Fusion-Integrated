
MODULE_CODE = "elm"
MODULE_LABEL = "Employee Leave Management"

MODULE = { 
    "code": MODULE_CODE,
    "label": MODULE_LABEL,
    "icon": "FaCalendar",
    "base_path": f"/{MODULE_CODE}",
    "nav_section": MODULE_LABEL,
    "sort_order": 11,
    "status": "active",
} 

NAV_ITEMS = [ 
    {
        "code": f"{MODULE_CODE}.leave_applications",
        "label": "Leave Applications",
        "icon": "FaCalendarAlt",
        "to": f"/{MODULE_CODE}/applications",
        "required_permission": f"{MODULE_CODE}.application.view",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    (f"{MODULE_CODE}.application.view", "View leave applications"),
    (f"{MODULE_CODE}.application.create", "Create leave applications"),
    (f"{MODULE_CODE}.application.manage", "Manage leave applications"),
] 

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {}