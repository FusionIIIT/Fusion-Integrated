"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "elm", "label": "Employee Leave Management", "icon": "Calendar",
    "base_path": "/elm", "nav_section": "Leave Management", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.requests", "label": "Leave Requests",
     "icon": "CalendarBlank", "to": "/elm/requests",
     "required_permission": "elm.leave.request.view",
     "sort_order": 5},
    {"code": "leave.approvals", "label": "Leave Approvals",
     "icon": "CheckCircle", "to": "/elm/approvals",
     "required_permission": "elm.leave.approve",
     "sort_order": 10},
    {"code": "leave.cancellations", "label": "Leave Cancellations",
     "icon": "XCircle", "to": "/elm/cancellations",
     "required_permission": "elm.leave.cancel",
     "sort_order": 20},
    {"code": "leave.withdrawals", "label": "Leave Withdrawals",
     "icon": "ArrowLeft", "to": "/elm/withdrawals",
     "required_permission": "elm.leave.withdraw",
     "sort_order": 30},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.leave.request.view", "View leave requests"),
    ("elm.leave.approve", "Approve leave requests"),
    ("elm.leave.cancel", "Cancel leave requests"),
    ("elm.leave.withdraw", "Withdraw leave requests"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "elm.leave.request.auto_withdraw",
    "elm.leave.cancellation.expire",
]

_STUDENT = [
    "elm.leave.request.view",
    "elm.leave.withdraw",
]

_COORDINATOR = [
    "elm.leave.request.view",
    "elm.leave.approve",
    "elm.leave.cancel",
]

_OFFICER = [
    *_COORDINATOR,
    "elm.leave.request.create",
    "elm.leave.request.review",
    "elm.leave.cancellation.expire",
]

#: Oversees rather than operates: no shortlisting and no offers.
_CHAIRMAN = [
    "elm.leave.request.view",
    "elm.leave.approve",
    "elm.leave.cancel",
    "elm.leave.withdraw",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "leave_coordinator": _COORDINATOR,
    "leave_officer": _OFFICER,
    "leave_chairman": _CHAIRMAN,
    "Dean Academic": _CHAIRMAN,
}
