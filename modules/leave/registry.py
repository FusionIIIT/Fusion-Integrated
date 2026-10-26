"""Leave permissions available to the IAM role and permission registry."""
MODULE = {
    "code": "leave", "label": "Employee Leave", "icon": "Calendar",
    "base_path": "/leave", "nav_section": "Employee Services", "sort_order": 40,
    "status": "active",
}

PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests"),
    ("leave.request.create", "Apply for leave"),
    ("leave.request.delete", "Cancel own pending leave request"),
    ("leave.request.approve", "Approve or reject a leave request"),
    ("leave.balance.update", "Adjust a leave balance"),
    ("leave.calendar.manage", "Create a holiday calendar"),
    ("leave.calendar.publish", "Publish a holiday calendar"),
]

_EMPLOYEE = [
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.delete",
]
_UNIT_HEAD = [
    "leave.request.approve",
]
_LEAVE_ADMIN = [
    "leave.balance.update",
    "leave.calendar.manage",
    "leave.calendar.publish",
]

ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Unit Head": _UNIT_HEAD,
    "Leave Administrator": _LEAVE_ADMIN,
}
