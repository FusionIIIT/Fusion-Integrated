"""What the server tells the shell about this module (ADR-0010), mirroring
modules/placement/registry.py's shape."""

MODULE = {
    "code": "elm", "label": "Employee Leave Management", "icon": "CalendarCheck",
    "base_path": "/elm", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.my_requests", "label": "My Leave Requests",
     "icon": "ClipboardText", "to": "/elm/my-requests",
     "required_permission": "elm.leave_request.view_self", "sort_order": 10},
    {"code": "elm.apply", "label": "Apply for Leave",
     "icon": "CalendarPlus", "to": "/elm/apply",
     "required_permission": "elm.leave_request.create", "sort_order": 20},
    {"code": "elm.approvals", "label": "Leave Approvals",
     "icon": "Checks", "to": "/elm/approvals",
     "required_permission": "elm.leave_request.decide", "sort_order": 30},
]

#: Every permission this module recognises.
PERMISSIONS = [
    ("elm.leave_request.create", "Submit a leave request for oneself"),
    ("elm.leave_request.view_self", "View one's own leave requests"),
    ("elm.leave_request.view", "View leave requests routed to one's role"),
    ("elm.leave_request.decide", "Record a Unit Head decision on a routed request"),
    ("elm.leave_request.withdraw", "Withdraw one's own pending request"),
    ("elm.leave_request.cancel", "Cancel one's own approved, not-yet-started leave"),
]

_EMPLOYEE = [
    "elm.leave_request.create",
    "elm.leave_request.view_self",
    "elm.leave_request.withdraw",
    "elm.leave_request.cancel",
]

#: Designation holding Unit Head responsibility for their organisational unit.
_UNIT_HEAD = [
    *_EMPLOYEE,
    "elm.leave_request.view",
    "elm.leave_request.decide",
]

ROLE_GRANTS = {
    "employee": _EMPLOYEE,
    "unit_head": _UNIT_HEAD,
}
