
"""Server-side navigation and permissions for Employee Leave Management."""

MODULE = {
    "code": "employee_leave_management",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Administration",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.my-leaves",
        "label": "My Leave Applications",
        "icon": "Calendar",
        "to": "/elm/applications",
        "required_permission": "elm.application.view_self",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("elm.application.view_self", "View own leave applications"),
    ("elm.application.create", "Submit leave applications"),
    ("elm.application.review", "Review leave applications"),
    ("elm.application.sanction", "Sanction leave applications"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "employee": [
        "elm.application.view_self",
        "elm.application.create",
    ],
    "Unit Head": [
        "elm.application.view_self",
        "elm.application.review",
    ],
}
