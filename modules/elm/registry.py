"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "elm", "label": "Employee Leave Management", "icon": "Calendar",
    "base_path": "/elm", "nav_section": "HR", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.leave_requests", "label": "Leave Requests",
     "icon": "ClipboardText", "to": "/elm/leave-requests",
     "required_permission": "elm.leave_request.view", "sort_order": 10},
    {"code": "elm.leave_types", "label": "Leave Types",
     "icon": "ListCheck", "to": "/elm/leave-types",
     "required_permission": "elm.leave_type.view", "sort_order": 20},
    {"code": "elm.leave_balances", "label": "Leave Balances",
     "icon": "ChartBar", "to": "/elm/leave-balances",
     "required_permission": "elm.leave_balance.view", "sort_order": 30},
]

PERMISSIONS = [
    ("elm.leave_request.view", "View leave requests"),
    ("elm.leave_request.create", "Create leave requests"),
    ("elm.leave_request.update", "Update leave requests"),
    ("elm.leave_request.delete", "Delete leave requests"),
    ("elm.leave_type.view", "View leave types"),
    ("elm.leave_type.create", "Create leave types"),
    ("elm.leave_type.update", "Update leave types"),
    ("elm.leave_type.delete", "Delete leave types"),
    ("elm.leave_balance.view", "View leave balances"),
    ("elm.leave_balance.update", "Update leave balances"),
]

ROLE_GRANTS = {
    "hr_officer": ["elm.leave_request.view", "elm.leave_request.create",
                   "elm.leave_request.update", "elm.leave_request.delete"],
    "hr_manager": ["elm.leave_request.view", "elm.leave_request.update",
                   "elm.leave_balance.view", "elm.leave_balance.update"],
    "hr_director": ["elm.leave_request.view", "elm.leave_request.update",
                   "elm.leave_type.view", "elm.leave_type.update",
                   "elm.leave_balance.view", "elm.leave_balance.update"],
}
