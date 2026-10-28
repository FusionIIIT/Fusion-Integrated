"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "elm", "label": "Leave Management", "icon": "CalendarBlank",
    "base_path": "/elm", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

PERMISSIONS = [
    ("elm.leave.apply", "Apply for Leave"),
    ("elm.leave.view_self", "View Own Leave Applications"),
    ("elm.leave.cancel", "Cancel Leave Application"),
    ("elm.leave.view_pending", "View Pending Leave Applications"),
    ("elm.leave.approve", "Approve Leave Applications"),
]

ROLE_GRANTS = {
    "Employee": ["elm.leave.apply", "elm.leave.view_self", "elm.leave.cancel"],
    "Leave Approver": ["elm.leave.view_pending", "elm.leave.approve"],
}

NAV_ITEMS = [
    {"code": "elm.apply", "label": "Apply for Leave",
     "icon": "CalendarBlank", "to": "/elm/apply",
     "required_permission": "elm.leave.apply"},
    {"code": "elm.my-leaves", "label": "My Leaves",
     "icon": "User", "to": "/elm/my-leaves",
     "required_permission": "elm.leave.view_self"},
    {"code": "elm.approve-leaves", "label": "Approve Leave Applications",
     "icon": "Check", "to": "/elm/approve-leaves",
     "required_permission": "elm.leave.approve"},
]