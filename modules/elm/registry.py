"""What the server tells the shell about this module (ADR-0010)."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.leave_requests",
        "label": "Leave Requests",
        "icon": "List",
        "to": "/elm/leave-requests",
        "required_permission": "elm.leave_request.view",
        "sort_order": 10,
    },
    {
        "code": "elm.create_request",
        "label": "Apply for Leave",
        "icon": "Plus",
        "to": "/elm/leave-requests/create",
        "required_permission": "elm.leave_request.create",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("elm.leave_request.view", "View leave requests"),
    ("elm.leave_request.create", "Apply for leave"),
    ("elm.leave_request.approve", "Approve leave requests"),
]

ROLE_GRANTS = {
    "faculty": ["elm.leave_request.view", "elm.leave_request.create"],
    "staff": ["elm.leave_request.view", "elm.leave_request.create"],
    "HOD": ["elm.leave_request.view", "elm.leave_request.create", "elm.leave_request.approve"],
}
