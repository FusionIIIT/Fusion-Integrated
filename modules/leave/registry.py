"""Fusion sidebar and IAM permissions for Employee Leave Management."""

MODULE = {
    "code": "leave", "label": "Employee Leave Management", "icon": "FaCalendarAlt",
    "base_path": "/leave", "nav_section": "People", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.mine", "label": "My Leave", "icon": "FaCalendarAlt",
     "to": "/leave/mine", "required_permission": "leave.request.view_self", "sort_order": 10},
    {"code": "leave.team", "label": "Leave Requests", "icon": "FaClipboardCheck",
     "to": "/leave/requests", "required_permission": "leave.request.review", "sort_order": 20},
]

PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests and balances"),
    ("leave.request.create", "Submit leave requests"),
    ("leave.request.cancel", "Cancel own pending leave requests"),
    ("leave.request.view", "View leave requests for managed employees"),
    ("leave.request.review", "Approve or reject leave requests"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = ["leave.request.view_self", "leave.request.create", "leave.request.cancel"]
_MANAGER = [*_EMPLOYEE, "leave.request.view", "leave.request.review"]
ROLE_GRANTS = {
    "student": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "placement_coordinator": _MANAGER,
    "placement_officer": _MANAGER,
    "placement_chairman": _MANAGER,
    "Dean Academic": _MANAGER,
    "acadadmin": _MANAGER,
}
