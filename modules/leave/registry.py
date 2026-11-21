"""What the server tells the shell about ELM (ADR-0010).

Who acts on a request is decided per request by the configured hierarchy
(BR-EL-019); `leave_request.review` only lets a person open their task inbox.
"""
MODULE = {
    "code": "leave_management", "label": "Leave", "icon": "CalendarCheck",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.mine", "label": "My Leave", "icon": "CalendarCheck",
     "to": "/leave/mine", "required_permission": "leave_management.leave_request.create",
     "sort_order": 10},
    {"code": "leave.tasks", "label": "Leave Tasks", "icon": "ListChecks",
     "to": "/leave/tasks", "required_permission": "leave_management.leave_request.review",
     "sort_order": 20},
    {"code": "leave.settings", "label": "Leave Settings", "icon": "Gear",
     "to": "/leave/settings", "required_permission": "leave_management.policy.manage",
     "sort_order": 30},
    {"code": "leave.calendar", "label": "Holiday Calendar", "icon": "CalendarBlank",
     "to": "/leave/calendar", "required_permission": "leave_management.calendar.publish",
     "sort_order": 40},
    {"code": "leave.records", "label": "Leave Records", "icon": "Notebook",
     "to": "/leave/records", "required_permission": "leave_management.leave_record.update",
     "sort_order": 50},
]

PERMISSIONS = [
    ("leave_management.leave_request.create",
     "Apply, withdraw, cancel, extend and resume one's own leave"),
    ("leave_management.leave_request.view", "See leave requests within one's scope"),
    ("leave_management.leave_request.review",
     "Act on leave tasks assigned by the hierarchy"),
    ("leave_management.leave_request.export", "Print one's own leave application"),
    ("leave_management.policy.manage", "Maintain leave policy, hierarchy and SLA"),
    ("leave_management.calendar.publish", "Create and publish the holiday/RH calendar"),
    ("leave_management.leave_record.import", "Record offline-sanctioned leave"),
    ("leave_management.leave_record.update", "Correct leave balances and see all records"),
    ("leave_management.leave_account.update", "Year-end leave processing"),
    ("leave_management.leave_request.assign", "SLA reminder and escalation"),
]

SYSTEM_PERMISSIONS = [
    "leave_management.leave_account.update",
    "leave_management.leave_request.assign",
]

SCOPE_PERMISSIONS = []

_EMPLOYEE = [
    "leave_management.leave_request.create",
    "leave_management.leave_request.view",
    "leave_management.leave_request.review",
    "leave_management.leave_request.export",
]

_ADMINISTRATOR = [
    "leave_management.leave_request.view",
    "leave_management.policy.manage",
    "leave_management.calendar.publish",
    "leave_management.leave_record.import",
    "leave_management.leave_record.update",
]

#: Keyed by designation; "Leave Administrator" is provisioned through the IAM console.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Leave Administrator": _ADMINISTRATOR,
}
