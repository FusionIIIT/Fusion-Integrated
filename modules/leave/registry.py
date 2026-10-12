"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "leave", "label": "Leave Management", "icon": "FaCalendarAlt",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    # -- employees: themselves first ----------------------------------------
    {"code": "leave.mine", "label": "My Leave",
     "icon": "FaCalendarAlt", "to": "/leave/mine",
     "required_permission": "leave.request.view_self", "sort_order": 10},
    {"code": "leave.balances", "label": "Balances",
     "icon": "FaLayerGroup", "to": "/leave/balances",
     "required_permission": "leave.request.view_self", "sort_order": 20},
    {"code": "leave.tasks", "label": "Leave Tasks",
     "icon": "FaCheckDouble", "to": "/leave/tasks",
     "required_permission": "leave.substitute.respond", "sort_order": 30},

    # -- reviewers and authorities -----------------------------------------
    {"code": "leave.requests", "label": "All Requests",
     "icon": "FaClipboardList", "to": "/leave/requests",
     "required_permission": "leave.request.view", "sort_order": 40},
    {"code": "leave.admin", "label": "Administration",
     "icon": "FaCog", "to": "/leave/admin",
     "required_permission": "leave.type.manage", "sort_order": 50},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave.request.view_self", "View your own leave requests and balances"),
    ("leave.request.create", "Apply for leave and nominate a substitute"),
    ("leave.request.delete", "Withdraw your own pending request"),
    ("leave.request.view", "View leave requests, within scope"),
    ("leave.request.approve", "Unit Head: approve or recommend a request"),
    ("leave.request.route", "Establishment: verify and forward a request"),
    ("leave.request.sanction", "Give the final sanction on a request"),
    ("leave.substitute.respond", "Accept or decline a substitute charge"),
    ("leave.balance.view", "View any employee's leave balance"),
    ("leave.balance.update", "Adjust a leave balance (maintenance)"),
    ("leave.type.manage", "Configure leave types and entitlement rules"),
    ("leave.calendar.manage", "Maintain holiday, RH and vacation calendars"),
    ("leave.record.manage", "Enter offline leave and annotate records"),
    ("leave.sla.manage", "Configure review SLA thresholds and escalation"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

#: Everyone who can be away holds the employee set.
_SELF = [
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.delete",
    "leave.substitute.respond",
]

_UNIT_HEAD = [*_SELF, "leave.request.view", "leave.request.approve"]

_ESTABLISHMENT = [*_SELF, "leave.request.view", "leave.request.route"]

_AUTHORITY = [*_SELF, "leave.request.view", "leave.request.sanction"]

_ADMIN = [
    "leave.request.view",
    "leave.balance.view",
    "leave.balance.update",
    "leave.type.manage",
    "leave.calendar.manage",
    "leave.record.manage",
    "leave.sla.manage",
]

#: Keyed by the designation name as it exists in globals_designation.
#: The office roles below are the ELM baseline's sanctioning hierarchy
#: (BR-EL-016…020); `faculty` and `staff` are the basic kinds.
ROLE_GRANTS = {
    "faculty": _SELF,
    "staff": _SELF,
    "Unit Head": _UNIT_HEAD,
    "Establishment Section": _ESTABLISHMENT,
    "Dean Academic": _AUTHORITY,
    "Registrar": _AUTHORITY,
    "Director": _AUTHORITY,
    "Leave Administrator": _ADMIN,
}
