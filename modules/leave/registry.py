MODULE = {
    "code": "leave",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "People",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.my_leave",
        "label": "My Leave",
        "icon": "CalendarRange",
        "to": "/leave",
        "required_permission": "leave.leave_request.view_self",
        "sort_order": 10,
    },
    {
        "code": "leave.approvals",
        "label": "Approvals",
        "icon": "Checklist",
        "to": "/leave/approvals",
        "required_permission": "leave.leave_request.view_all",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("leave.leave_request.view_self", "View own leave requests"),
    ("leave.leave_request.create", "Submit a leave request"),
    ("leave.leave_request.view_all", "View all leave requests within scope"),
    ("leave.leave_request.approve", "Review and approve leave requests"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave.leave_request.view_self",
    "leave.leave_request.create",
]

_MANAGER = [
    *_EMPLOYEE,
    "leave.leave_request.view_all",
    "leave.leave_request.approve",
]

ROLE_GRANTS = {
    "student": _EMPLOYEE,
    "faculty": _MANAGER,
    "staff": _MANAGER,
}
