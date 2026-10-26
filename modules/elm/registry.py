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
     "icon": "CalendarBlank", "to": "/elm/leave-requests",
     "required_permission": "elm.leave_request.view", "sort_order": 10},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.leave_request.view", "See leave requests"),
    ("elm.leave_request.create", "Create a leave request"),
    ("elm.leave_request.approve", "Approve a leave request"),
    ("elm.leave_request.reject", "Reject a leave request"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "elm.leave_request.approve",
    "elm.leave_request.reject",
]

_STAFF = [
    "elm.leave_request.view",
    "elm.leave_request.create",
]

_MANAGER = [
    *_STAFF,
    "elm.leave_request.approve",
    "elm.leave_request.reject",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "staff": _STAFF,
    "manager": _MANAGER,
}
