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
    {"code": "elm.approvals", "label": "Approvals",
     "icon": "CheckCircle", "to": "/elm/approvals",
     "required_permission": "elm.approval.manage", "sort_order": 20},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.leave_request.view", "View leave requests"),
    ("elm.leave_request.create", "Create a new leave request"),
    ("elm.leave_request.approve", "Approve or reject a leave request"),
    ("elm.leave_request.cancel", "Cancel a pending leave request"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    # Add any system-level permissions here if needed
]

_STUDENT = [
    "elm.leave_request.view",
    "elm.leave_request.create",
]

_COORDINATOR = [
    "elm.leave_request.view",
    "elm.leave_request.approve",
]

_OFFICER = [
    *_COORDINATOR,
    "elm.leave_request.cancel",
]

#: Oversees rather than operates: no shortlisting and no offers.
_CHAIRMAN = [
    "elm.leave_request.view",
    "elm.leave_request.approve",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "hr_coordinator": _COORDINATOR,
    "hr_officer": _OFFICER,
    "hr_chairman": _CHAIRMAN,
}
