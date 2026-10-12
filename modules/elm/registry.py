"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "elm", "label": "ELM", "icon": "Calendar",
    "base_path": "/elm", "nav_section": "ELM", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.leave-types", "label": "Leave Types",
     "icon": "ClipboardList", "to": "/elm/leave-types",
     "required_permission": "elm.leave_type.view", "sort_order": 10},
    {"code": "elm.leave-balances", "label": "Leave Balances",
     "icon": "Clock", "to": "/elm/leave-balances",
     "required_permission": "elm.leave_balance.view", "sort_order": 20},
    {"code": "elm.leave-applications", "label": "Leave Applications",
     "icon": "PencilAlt", "to": "/elm/leave-applications",
     "required_permission": "elm.leave_application.view", "sort_order": 30},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.leave_type.view", "View leave types"),
    ("elm.leave_balance.view", "View leave balances"),
    ("elm.leave_application.view", "View leave applications"),
    ("elm.leave_application.create", "Create leave application"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "elm.leave_type.view",
    "elm.leave_balance.view",
    "elm.leave_application.view",
    "elm.leave_application.create",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "employee": _EMPLOYEE,
}
