MODULE = {
    "code": "leave_elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "Employee",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.requests", "label": "My Leave Requests", "icon": "Calendar",
     "to": "/leave/requests", "required_permission": "leave_elm.request.view_self", "sort_order": 10},
    {"code": "elm.balances", "label": "My Leave Balance", "icon": "Wallet",
     "to": "/leave/balances", "required_permission": "leave_elm.balance.view_self", "sort_order": 20},
    {"code": "elm.queue", "label": "Leave Approval Queue", "icon": "ClipboardList",
     "to": "/leave/queue", "required_permission": "leave_elm.request.review", "sort_order": 30},
]

PERMISSIONS = [
    ("leave_elm.request.view_self", "View own leave requests"),
    ("leave_elm.request.apply", "Apply for leave"),
    ("leave_elm.request.review", "Review leave requests"),
    ("leave_elm.balance.view_self", "View own leave balances"),
]

_EMPLOYEE = [
    "leave_elm.request.view_self",
    "leave_elm.request.apply",
    "leave_elm.balance.view_self",
]
_REVIEWER = _EMPLOYEE + ["leave_elm.request.review"]

ROLE_GRANTS = {
    "employee": _EMPLOYEE,
    "Faculty": _EMPLOYEE,
    "Staff": _EMPLOYEE,
    "Unit Head": _REVIEWER,
    "Leave Administrator": [p[0] for p in PERMISSIONS],
}
