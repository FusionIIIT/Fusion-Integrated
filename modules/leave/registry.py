"""Navigation and permission registration for Employee Leave Management."""

MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Administration",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.apply",
        "label": "Apply Leave",
        "icon": "CalendarPlus",
        "to": "/leave/apply",
        "required_permission": "leave.application.apply",
        "sort_order": 10,
    },
    {
        "code": "leave.applications",
        "label": "My Applications",
        "icon": "CalendarBlank",
        "to": "/leave/applications",
        "required_permission": "leave.application.view",
        "sort_order": 20,
    },
    {
        "code": "leave.approvals",
        "label": "Leave Approvals",
        "icon": "Checks",
        "to": "/leave/approvals",
        "required_permission": "leave.application.approve",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("leave.application.view", "See leave applications"),
    ("leave.application.apply", "Submit a leave application"),
    ("leave.application.approve", "Approve or reject a leave application"),
]

_EMPLOYEE = ["leave.application.view", "leave.application.apply"]
_APPROVER = ["leave.application.view", "leave.application.approve"]

ROLE_GRANTS = {
    "student": _EMPLOYEE,
    "faculty": ["leave.application.view", "leave.application.apply", "leave.application.approve"],
    "staff": _EMPLOYEE,
    "Employee": _EMPLOYEE,
    "Leave Approver": _APPROVER,
}
