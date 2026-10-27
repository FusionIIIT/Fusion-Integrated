"""Server-driven navigation metadata for Employee Leave Management."""
MODULE = {
    "code": "employee_leave_management",
    "label": "Employee Leave Management",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "Employee Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.my_requests", "label": "My Leave Requests", "icon": "Calendar",
     "to": "/elm/requests", "required_permission": "elm.request.view_self", "sort_order": 10},
    {"code": "elm.apply", "label": "Apply for Leave", "icon": "CalendarPlus",
     "to": "/elm/requests/new", "required_permission": "elm.request.apply", "sort_order": 20},
    {"code": "elm.approvals", "label": "Leave Approvals", "icon": "ClipboardCheck",
     "to": "/elm/tasks", "required_permission": "elm.task.review", "sort_order": 30},
    {"code": "elm.balances", "label": "Leave Balance", "icon": "Wallet",
     "to": "/elm/balance", "required_permission": "elm.balance.view_self", "sort_order": 40},
    {"code": "elm.admin", "label": "Leave Configuration", "icon": "Settings",
     "to": "/elm/configuration", "required_permission": "elm.policy.manage", "sort_order": 50},
]
