"""Server-driven module navigation and IAM permission grants."""
MODULE = {
    "code": "leave", "label": "Employee Leave Management", "icon": "Calendar",
    "base_path": "/leave", "nav_section": "Employee Services", "sort_order": 30,
    "status": "planned",
}

NAV_ITEMS = [
    {"code": "leave.mine", "label": "My Leave", "icon": "User", "to": "/leave/mine",
     "required_permission": "leave.application.view", "sort_order": 10},
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "Plus",
     "to": "/leave/apply", "required_permission": "leave.application.create",
     "sort_order": 20},
    {"code": "leave.tasks", "label": "Assigned Tasks", "icon": "Clipboard",
     "to": "/leave/tasks", "required_permission": "leave.application.review",
     "sort_order": 30},
    {"code": "leave.balances", "label": "Balances and History", "icon": "History",
     "to": "/leave/balances", "required_permission": "leave.balance.view",
     "sort_order": 40},
    {"code": "leave.resumptions", "label": "Resumption of Duty", "icon": "Check",
     "to": "/leave/resumptions", "required_permission": "leave.application.create",
     "sort_order": 45},
    {"code": "leave.calendar", "label": "Leave Calendar", "icon": "Calendar",
     "to": "/leave/calendar", "required_permission": "leave.calendar.manage",
     "sort_order": 50},
    {"code": "leave.admin", "label": "Leave Administration", "icon": "Settings",
     "to": "/leave/admin", "required_permission": "leave.policy.manage",
     "sort_order": 60},
]

PERMISSIONS = [
    ("leave.application.view", "View leave applications within assigned scope"),
    ("leave.application.create", "Submit leave applications"),
    ("leave.application.update", "Update substitute nomination before routing"),
    ("leave.application.delete", "Withdraw or request cancellation of leave"),
    ("leave.application.review", "Review and route leave applications"),
    ("leave.application.approve", "Make final leave decisions"),
    ("leave.application.export", "Export an accessible leave application"),
    ("leave.year_end.process", "Process annual leave account closing"),
    ("leave.sla.process", "Process workflow SLA thresholds"),
    ("leave.substitute.update", "Respond to a substitute request"),
    ("leave.balance.view", "View leave balances and history"),
    ("leave.policy.manage", "Maintain leave policy and hierarchy"),
    ("leave.calendar.manage", "Maintain leave calendars"),
    ("leave.calendar.publish", "Publish a holiday and restricted-holiday calendar"),
    ("leave.record.import", "Record already-sanctioned offline leave"),
    ("leave.record.update", "Maintain authorized leave records"),
    ("leave.resumption.review", "Review leave resumption"),
    ("leave.sla.manage", "Configure workflow task SLA thresholds"),
]

SYSTEM_PERMISSIONS = ["leave.year_end.process", "leave.sla.process"]

_EMPLOYEE = [
    "leave.application.view", "leave.application.create", "leave.application.delete",
    "leave.application.update", "leave.application.export", "leave.substitute.update",
    "leave.balance.view",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Unit Head": ["leave.application.view", "leave.application.review"],
    "Deputy Registrar (Estt.) / Establishment Processing Role": [
        "leave.application.view", "leave.application.review"],
    "Sanctioning Authority": ["leave.application.view", "leave.application.approve",
                              "leave.resumption.review"],
    "Director": ["leave.application.view", "leave.application.approve",
                  "leave.resumption.review"],
    "Leave Administrator": [
        "leave.application.view", "leave.application.export", "leave.policy.manage",
        "leave.calendar.manage", "leave.calendar.publish", "leave.record.import",
        "leave.record.update", "leave.sla.manage"],
    "Authorized administrative role": [
        "leave.application.view", "leave.application.export", "leave.policy.manage",
        "leave.calendar.manage", "leave.calendar.publish", "leave.record.import",
        "leave.record.update", "leave.sla.manage"],
}
