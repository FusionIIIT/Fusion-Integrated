"""What the server tells the shell about this module  (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "HR",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.dashboard", "label": "Dashboard", "icon": "Home", "to": "/elm",
     "required_permission": "elm.dashboard.view", "sort_order": 10},
    {"code": "elm.leaves", "label": "Leave Requests", "icon": "ClipboardList",
     "to": "/elm/leaves", "required_permission": "elm.leave.view", "sort_order": 20},
    {"code": "elm.reports", "label": "Reports", "icon": "ChartBar", "to": "/elm/reports",
     "required_permission": "elm.report.view", "sort_order": 30},
]

PERMISSIONS = [
    ("elm.dashboard.view", "View ELM dashboard"),
    ("elm.leave.view", "View leave requests"),
    ("elm.leave.create", "Create leave requests"),
    ("elm.leave.approve", "Approve leave requests"),
    ("elm.leave.reject", "Reject leave requests"),
    ("elm.report.view", "View reports"),
]

ROLE_GRANTS = {
    "staff": ["elm.dashboard.view", "elm.leave.view", "elm.report.view"],
    "hr": ["elm.dashboard.view", "elm.leave.view", "elm.leave.create",
           "elm.leave.approve", "elm.leave.reject", "elm.report.view"],
    "admin": ["elm.dashboard.view", "elm.leave.view", "elm.leave.create",
              "elm.leave.approve", "elm.leave.reject", "elm.report.view"],
}
