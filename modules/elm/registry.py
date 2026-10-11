"""Registry declaration for Employee Leave Management."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Academic",
    "sort_order": 30,
    "status": "planned",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("elm.leave_request.view_self", "View own leave requests"),
    ("elm.leave_request.create", "Create a leave request"),
    ("elm.leave_request.withdraw", "Withdraw a pending leave request"),
    ("elm.leave_request.view", "View leave requests within scope"),
    ("elm.leave_request.approve", "Approve or reject leave requests"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {}