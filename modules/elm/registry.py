PERMISSIONS = [
    ("leave_elm.application.view", "View applications"),
    ("leave_elm.application.apply", "Apply for leave"),
    ("leave_elm.application.approve", "Approve leave"),
    ("leave_elm.application.manage", "Manage leaves"),
]

_EMPLOYEE = ["leave_elm.application.view", "leave_elm.application.apply"]
_APPROVER = ["leave_elm.application.view", "leave_elm.application.approve"]
_UNIT_HEAD = ["leave_elm.application.view", "leave_elm.application.approve", "leave_elm.application.manage"]
_LEAVE_ADMIN = ["leave_elm.application.view", "leave_elm.application.approve", "leave_elm.application.manage"]

ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Leave Approver": _APPROVER,
    "Unit Head": _UNIT_HEAD,
    "Leave Administrator": _LEAVE_ADMIN,
}

NAV_ITEMS = [
    {"title": "Leave Management", "url": "/leave_elm/", "required_permission": "leave_elm.application.view"},
]
