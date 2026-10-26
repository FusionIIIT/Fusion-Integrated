"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering.
"""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Services",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.apply",
        "label": "Apply Leave",
        "icon": "CalendarPlus",
        "to": "/elm/apply",
        "required_permission": "elm.leave_request.create",
        "sort_order": 10,
    },
    {
        "code": "elm.my_leaves",
        "label": "My Leaves",
        "icon": "CalendarBlank",
        "to": "/elm/leaves",
        "required_permission": "elm.leave_request.view_self",
        "sort_order": 20,
    },
    {
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "Calculator",
        "to": "/elm/balances",
        "required_permission": "elm.leave_balance.view_self",
        "sort_order": 25,
    },
    {
        "code": "elm.approvals",
        "label": "Leave Approvals",
        "icon": "Checks",
        "to": "/elm/approvals",
        "required_permission": "elm.leave_request.review",
        "sort_order": 30,
    },
    {
        "code": "elm.leave_types",
        "label": "Leave Types",
        "icon": "ListChecks",
        "to": "/elm/types",
        "required_permission": "elm.leave_type.manage",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("elm.leave_request.create", "Apply for leave"),
    ("elm.leave_request.view_self", "View own leave requests"),
    ("elm.leave_request.view", "View all leave requests"),
    ("elm.leave_request.review", "Approve or reject leave requests"),
    ("elm.leave_balance.view_self", "View own leave balances"),
    ("elm.leave_balance.view", "View all leave balances"),
    ("elm.leave_type.view", "View leave types"),
    ("elm.leave_type.manage", "Manage leave types"),
]

SYSTEM_PERMISSIONS = []

SCOPE_PERMISSIONS = []

_EMPLOYEE = [
    "elm.leave_request.create",
    "elm.leave_request.view_self",
    "elm.leave_balance.view_self",
    "elm.leave_type.view",
]

_APPROVER = [
    *_EMPLOYEE,
    "elm.leave_request.view",
    "elm.leave_request.review",
    "elm.leave_balance.view",
]

_ADMIN = [
    *_APPROVER,
    "elm.leave_type.manage",
]

ROLE_GRANTS = {
    "staff": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "student": _EMPLOYEE,
    "Dean Academic": _ADMIN,
    "acadadmin": _ADMIN,
}
