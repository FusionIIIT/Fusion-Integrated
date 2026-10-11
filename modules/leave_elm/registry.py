MODULE = {
    "code": "leave_elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/leave_elm",
    "nav_section": "Employee Services",
    "sort_order": 30,
    "status": "active",
}

PERMISSIONS = [
    ("leave_elm.request.view_self", "View own leave requests and balances"),
    ("leave_elm.request.create", "Create leave requests"),
    ("leave_elm.request.decide", "Record a leave request decision"),
]

SYSTEM_PERMISSIONS = []

NAV_ITEMS = [
    {
        "code": "leave_elm.home",
        "label": "My Leave",
        "icon": "Calendar",
        "to": "/leave_elm/my-leave",
        "required_permission": "leave_elm.request.view_self",
        "sort_order": 10,
    },
]

_EMPLOYEE = [
    "leave_elm.request.view_self",
    "leave_elm.request.create",
]
_APPROVER = [*_EMPLOYEE, "leave_elm.request.decide"]
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": _APPROVER,
    "Unit Head": _APPROVER,
    "Leave Administrator": _APPROVER,
}
