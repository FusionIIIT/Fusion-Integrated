MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/elm",
    "nav_section": "People",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.leave_applications",
        "label": "Leave Applications",
        "icon": "FaCalendarAlt",
        "to": "/elm/leave-applications",
        "required_permission": "elm.leave_application.view_self",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("elm.leave_application.view_self", "View own leave applications"),
    ("elm.leave_application.apply", "Submit a leave application"),
    ("elm.leave_application.manage", "Manage employee leave applications"),
]

ROLE_GRANTS = {
    "employee": [
        "elm.leave_application.view_self",
        "elm.leave_application.apply",
    ],
    "hr": [
        "elm.leave_application.view_self",
        "elm.leave_application.apply",
        "elm.leave_application.manage",
    ],
}