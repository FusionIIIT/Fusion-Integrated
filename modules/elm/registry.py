"""IAM-owned module and permission declarations for Employee Leave Management."""
MODULE = {
    "code": "leave_elm",
    "label": "Employee Leave Management",
    "icon": "CalendarDays",
    "base_path": "/leave",
    "nav_section": "Employee Services",
    "sort_order": 30,
    "status": "planned",
}

PERMISSIONS = [
    ("leave_elm.application.view_self", "View own leave applications"),
    ("leave_elm.application.apply", "Submit a leave application"),
    ("leave_elm.balance.view_self", "View own leave balances"),
    ("leave_elm.application.view", "View leave applications for review"),
    ("leave_elm.application.approve", "Recommend or decide a leave application"),
    ("leave_elm.application.cancel", "Request or decide leave cancellation"),
]

NAV_ITEMS = [
    {"code": "leave_elm.my_requests", "label": "My Leave Requests", "icon": "CalendarDays",
     "to": "/leave/requests", "required_permission": "leave_elm.application.view_self",
     "sort_order": 10},
    {"code": "leave_elm.my_balances", "label": "My Leave Balances", "icon": "Wallet",
     "to": "/leave/balances", "required_permission": "leave_elm.balance.view_self",
     "sort_order": 20},
]

_EMPLOYEE = [
    "leave_elm.application.view_self",
    "leave_elm.application.apply",
    "leave_elm.balance.view_self",
    "leave_elm.application.cancel",
]

ROLE_GRANTS = {
    "faculty": list(_EMPLOYEE),
    "staff": list(_EMPLOYEE),
    "hr_officer": [
        "leave_elm.application.view",
        "leave_elm.application.approve",
        "leave_elm.application.cancel",
    ],
}
