"""What the server tells the shell about this module (ADR-0010)."""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.apply",
        "label": "Apply Leave",
        "icon": "PlusCircle",
        "to": "/elm/apply",
        "required_permission": "elm.leave_request.create",
        "sort_order": 10,
    },
    {
        "code": "elm.mine",
        "label": "My Leaves",
        "icon": "List",
        "to": "/elm/mine",
        "required_permission": "elm.leave_request.view",
        "sort_order": 20,
    },
    {
        "code": "elm.approvals",
        "label": "Leave Approvals",
        "icon": "CheckSquare",
        "to": "/elm/approvals",
        "required_permission": "elm.leave_request.review",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("elm.leave_request.create", "Apply for leave"),
    ("elm.leave_request.review", "Approve or reject leave requests"),
    ("elm.leave_request.view", "View leave requests"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "elm.leave_request.create",
    "elm.leave_request.view",
]

_MANAGER = [
    "elm.leave_request.create",
    "elm.leave_request.view",
    "elm.leave_request.review",
]

ROLE_GRANTS = {
    "student": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "manager": _MANAGER,
    "hr": _MANAGER,
    "admin": _MANAGER,
    "placement_officer": _MANAGER,
    "Dean Academic": _MANAGER,
}
