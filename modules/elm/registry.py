"""What the server tells the shell about this module  (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/elm",
    "nav_section": "HR",
    "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.leave-requests", "label": "My Leave Requests",
     "icon": "FaCalendarAlt", "to": "/elm/leave-requests",
     "required_permission": "elm.leave_request.view", "sort_order": 10},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.leave_request.view", "See leave requests"),
    ("elm.leave_request.manage", "Submit and withdraw own leave requests"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "elm.leave_request.view",
    "elm.leave_request.manage",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "staff": _EMPLOYEE,
    "faculty": _EMPLOYEE,
}
