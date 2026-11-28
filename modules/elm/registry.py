MODULE = {
    "code": "elm", "label": "Employee Leave Management", "icon": "CalendarCheck",
    "base_path": "/elm", "nav_section": "Employee Services", "sort_order": 20,
    "status": "active",
}
NAV_ITEMS = [
    {"code": "elm.mine", "label": "My Leave", "icon": "CalendarCheck", "to": "/elm/mine",
     "required_permission": "elm.leave.view_self", "sort_order": 10},
    {"code": "elm.tasks", "label": "Leave Tasks", "icon": "ListChecks", "to": "/elm/tasks",
     "required_permission": "elm.leave.review", "sort_order": 20},
]
PERMISSIONS = [
    ("elm.leave.view_self", "View own leave balances and requests"),
    ("elm.leave.apply", "Apply for leave"),
    ("elm.leave.review", "Review assigned leave requests"),
    ("elm.policy.manage", "Maintain leave policy and calendars"),
]
ROLE_GRANTS = {
    "faculty": ["elm.leave.view_self", "elm.leave.apply"],
    "staff": ["elm.leave.view_self", "elm.leave.apply"],
    "Unit Head": ["elm.leave.view_self", "elm.leave.apply", "elm.leave.review"],
    "Leave Administrator": ["elm.leave.view_self", "elm.leave.review", "elm.policy.manage"],
}
