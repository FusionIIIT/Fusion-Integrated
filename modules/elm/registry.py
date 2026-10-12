MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "FaCalendar",
    "base_path": "/elm",
    "nav_section": "Employee Leave Management",
    "sort_order": 11,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.leave_applications",
        "label": "Leave Applications",
        "icon": "FaCalendarAlt",
        "to": "/elm/applications",
        "required_permission": "elm.application.view",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("elm.application.view", "View leave applications"),
    ("elm.application.create", "Create leave applications"),
    ("elm.application.manage", "Manage leave applications"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {}