"""Server-side module descriptor and permission catalog for ELM."""
MODULE = {
    "code": "leave_management", "label": "Employee Leave Management",
    "icon": "Calendar", "base_path": "/leave", "nav_section": "People",
    "sort_order": 20, "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.mine", "label": "My Leave", "icon": "Calendar",
     "to": "/leave", "required_permission": "leave_management.request.view_self", "sort_order": 10},
    {"code": "leave.tasks", "label": "Leave Tasks", "icon": "Checks",
     "to": "/leave/tasks", "required_permission": "leave_management.workflow.task.view", "sort_order": 20},
    {"code": "leave.substitutions", "label": "Substitute Requests", "icon": "UserCheck",
     "to": "/leave/substitutions", "required_permission": "leave_management.substitute.respond", "sort_order": 25},
    {"code": "leave.balances", "label": "Leave Balances", "icon": "Wallet",
     "to": "/leave/balances", "required_permission": "leave_management.balance.view_self", "sort_order": 30},
    {"code": "leave.calendar", "label": "Holiday Calendar", "icon": "CalendarBlank",
     "to": "/leave/calendar", "required_permission": "leave_management.calendar.view", "sort_order": 40},
]

PERMISSIONS = [
    ("leave_management.request.view_self", "View own leave requests"),
    ("leave_management.request.view_all", "View all leave requests"),
    ("leave_management.request.create", "Create and submit own leave requests"),
    ("leave_management.request.withdraw", "Withdraw own pending requests"),
    ("leave_management.request.cancel", "Request cancellation of own approved leave"),
    ("leave_management.balance.view_self", "View own leave balances and account history"),
    ("leave_management.balance.view_all", "View employee leave balances"),
    ("leave_management.substitute.respond", "Accept or decline a substitute assignment"),
    ("leave_management.workflow.task.view", "View assigned leave workflow tasks"),
    ("leave_management.workflow.task.decide", "Review or decide assigned workflow tasks"),
    ("leave_management.policy.view", "View current policy parameters"),
    ("leave_management.policy.manage", "Maintain current policy parameters"),
    ("leave_management.calendar.view", "View published calendars"),
    ("leave_management.calendar.manage", "Maintain and publish calendars"),
    ("leave_management.records.manage", "Maintain authorized records and offline-sanctioned leave"),
    ("leave_management.sla.manage", "Configure workflow SLA thresholds"),
    ("leave_management.routing.manage", "Maintain current authority routing"),
]
