"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending.
"""
MODULE = {
    "code": "leave", "label": "Employee Leave", "icon": "CalendarBlank",
    "base_path": "/leave", "nav_section": "Establishment", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.mine", "label": "My Leave",
     "icon": "User", "to": "/leave/mine",
     "required_permission": "leave.application.view", "sort_order": 10},
    {"code": "leave.apply", "label": "Apply",
     "icon": "NotePencil", "to": "/leave/apply",
     "required_permission": "leave.application.create", "sort_order": 20},
    {"code": "leave.balance", "label": "Balances",
     "icon": "Wallet", "to": "/leave/balances",
     "required_permission": "leave.balance.view", "sort_order": 30},
    {"code": "leave.substitute", "label": "Substitute tasks",
     "icon": "Users", "to": "/leave/substitute",
     "required_permission": "leave.substitute.review", "sort_order": 40},
    {"code": "leave.queue", "label": "Review queue",
     "icon": "Checks", "to": "/leave/queue",
     "required_permission": "leave.application.review", "sort_order": 50},
    {"code": "leave.sanction", "label": "Sanction queue",
     "icon": "Stamp", "to": "/leave/sanction",
     "required_permission": "leave.application.approve", "sort_order": 60},
    {"code": "leave.policy", "label": "Policy",
     "icon": "Gear", "to": "/leave/policy",
     "required_permission": "leave.policy.publish", "sort_order": 70},
    {"code": "leave.calendar", "label": "Holiday calendar",
     "icon": "Calendar", "to": "/leave/calendar",
     "required_permission": "leave.calendar.publish", "sort_order": 80},
    {"code": "leave.offline", "label": "Offline leave",
     "icon": "Archive", "to": "/leave/offline",
     "required_permission": "leave.offline.create", "sort_order": 90},
]

PERMISSIONS = [
    ("leave.application.view", "See leave applications in scope"),
    ("leave.application.create", "Submit a leave application"),
    ("leave.application.update", "Modify a pending leave application"),
    ("leave.application.delete", "Withdraw a pending leave application"),
    ("leave.application.review", "Record Unit Head / Establishment review"),
    ("leave.application.approve", "Approve or reject a routed leave request"),
    ("leave.application.export", "Export a printable leave application"),
    ("leave.substitute.review", "Accept or decline a substitute nomination"),
    ("leave.balance.view", "See leave balances and account history"),
    ("leave.policy.publish", "Create, revise and publish leave policy"),
    ("leave.calendar.publish", "Create, revise and publish holiday/RH calendars"),
    ("leave.offline.create", "Record already-sanctioned offline leave"),
    ("leave.account.restore", "System year-end lapse, conversion and carry-forward"),
    ("leave.task.manage", "System SLA reminder and escalation"),
]

SYSTEM_PERMISSIONS = [
    "leave.account.restore",
    "leave.task.manage",
]

_EMPLOYEE = [
    "leave.application.view",
    "leave.application.create",
    "leave.application.update",
    "leave.application.delete",
    "leave.application.export",
    "leave.substitute.review",
    "leave.balance.view",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "leave.application.review",
    "leave.application.approve",
]

_ESTABLISHMENT = [
    *_EMPLOYEE,
    "leave.application.review",
]

_SANCTION = [
    *_EMPLOYEE,
    "leave.application.review",
    "leave.application.approve",
]

_ADMIN = [
    *_SANCTION,
    "leave.policy.publish",
    "leave.calendar.publish",
    "leave.offline.create",
]

# Derived from ELM actors (00 domain context; EL-UC-001..016; BR-EL-016..020).
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Unit Head": _UNIT_HEAD,
    "HOD": _UNIT_HEAD,
    "Deputy Registrar (Estt.)": _ESTABLISHMENT,
    "Dean": _SANCTION,
    "Registrar": _SANCTION,
    "Director": _SANCTION,
    "Leave Administrator": _ADMIN,
}
