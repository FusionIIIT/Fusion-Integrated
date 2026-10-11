"""Module registration metadata for Employee Leave Management."""

MODULE = {
    "code": "leave_elm",
    "label": "Employee Leave Management",
    "icon": "CalendarCheck",
    "base_path": "/leave-elm",
    "nav_section": "Employee Services",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave_elm.applications",
        "label": "My Leave Applications",
        "icon": "Calendar",
        "to": "/leave-elm/applications",
        "required_permission": "leave_elm.application.view",
        "sort_order": 10,
    },
    {
        "code": "leave_elm.apply",
        "label": "Apply for Leave",
        "icon": "CalendarPlus",
        "to": "/leave-elm/applications/new",
        "required_permission": "leave_elm.application.apply",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("leave_elm.application.view", "View one's own leave applications"),
    ("leave_elm.application.apply", "Submit a leave application"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "Employee": [
        "leave_elm.application.view",
        "leave_elm.application.apply",
    ],
    "Leave Approver": [
        "leave_elm.application.view",
    ],
}
