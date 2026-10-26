"""What the server tells the shell about Employee Leave Management (ADR-0010).

Nav items carry required_permission and the server filters before sending.
"""

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
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "ChartPie",
        "to": "/elm/balances",
        "required_permission": "elm.leave_request.view",
        "sort_order": 5,
    },
    {
        "code": "elm.leave_requests",
        "label": "My Requests",
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
    {
        "code": "elm.substitute_requests",
        "label": "Substitute Requests",
        "icon": "UserCheck",
        "to": "/elm/substitute-requests",
        "required_permission": "elm.leave_request.view",
        "sort_order": 30,
    },
    {
        "code": "elm.approvals",
        "label": "Leave Approvals",
        "icon": "Checks",
        "to": "/elm/approvals",
        "required_permission": "elm.leave_request.approve",
        "sort_order": 40,
    },
    {
        "code": "elm.calendar_admin",
        "label": "Holiday Calendar",
        "icon": "CalendarCheck",
        "to": "/elm/calendar",
        "required_permission": "elm.calendar.publish",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("elm.leave_request.view", "View personal leave records and balances"),
    ("elm.leave_request.create", "Apply for leave and withdraw pending requests"),
    ("elm.leave_request.approve", "Review, recommend, or approve leave requests"),
    ("elm.calendar.publish", "Create and publish institute holiday/RH calendar"),
    ("elm.admin.manage", "Perform administrative leave record synchronization"),
]

ROLE_GRANTS = {
    "faculty": [
        "elm.leave_request.view",
        "elm.leave_request.create",
    ],
    "staff": [
        "elm.leave_request.view",
        "elm.leave_request.create",
    ],
    "HOD": [
        "elm.leave_request.view",
        "elm.leave_request.create",
        "elm.leave_request.approve",
    ],
    "Dean Academic": [
        "elm.leave_request.view",
        "elm.leave_request.create",
        "elm.leave_request.approve",
    ],
    "Registrar": [
        "elm.leave_request.view",
        "elm.leave_request.create",
        "elm.leave_request.approve",
    ],
    "Director": [
        "elm.leave_request.view",
        "elm.leave_request.create",
        "elm.leave_request.approve",
    ],
    "leave_admin": [
        "elm.leave_request.view",
        "elm.leave_request.approve",
        "elm.calendar.publish",
        "elm.admin.manage",
    ],
}
