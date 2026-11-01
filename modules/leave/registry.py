"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending, so
a screen a role cannot use never reaches the browser. `ROLE_GRANTS` is the
visibility decision, keyed by designation exactly as the IAM spells it.
"""
MODULE = {
    "code": "leave", "label": "Leave", "icon": "Umbrella",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.balances", "label": "My Balances", "icon": "Wallet",
     "to": "/leave/balances", "required_permission": "leave.balance.view",
     "sort_order": 10},
    {"code": "leave.requests", "label": "My Requests", "icon": "ListChecks",
     "to": "/leave/requests", "required_permission": "leave.request.view",
     "sort_order": 20},
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "NotePencil",
     "to": "/leave/apply", "required_permission": "leave.request.create",
     "sort_order": 30},
    {"code": "leave.substitutes", "label": "Responsibility Requests",
     "icon": "UserCheck", "to": "/leave/substitute-requests",
     "required_permission": "leave.substitute.review", "sort_order": 40},
    {"code": "leave.queue", "label": "Awaiting My Decision",
     "icon": "ClipboardText", "to": "/leave/queue",
     "required_permission": "leave.request.review", "sort_order": 50},
    {"code": "leave.calendar", "label": "Holiday Calendar",
     "icon": "CalendarBlank", "to": "/leave/calendar",
     "required_permission": "leave.calendar.publish", "sort_order": 60},
    {"code": "leave.policy", "label": "Policy and Hierarchy",
     "icon": "Sliders", "to": "/leave/policy",
     "required_permission": "leave.policy.update", "sort_order": 70},
    {"code": "leave.records", "label": "Leave Records", "icon": "FileText",
     "to": "/leave/records", "required_permission": "leave.record.view",
     "sort_order": 80},
    {"code": "leave.thresholds", "label": "SLA Thresholds", "icon": "Clock",
     "to": "/leave/sla-thresholds",
     "required_permission": "leave.threshold.update", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave.request.view", "See leave requests within your scope"),
    ("leave.request.create", "Apply for leave, and nominate a substitute"),
    ("leave.request.delete", "Withdraw your own pending leave request"),
    ("leave.request.review", "Review a request and record the recommendation"),
    ("leave.request.approve", "Record the final sanctioning decision"),
    ("leave.cancellation.create", "Ask to cancel your own approved leave"),
    ("leave.extension.create", "Ask to extend your own ongoing leave"),
    ("leave.resumption.create", "Submit your own resumption of duty"),
    ("leave.resumption.review", "Review a submitted resumption of duty"),
    ("leave.substitute.review", "Accept or decline a responsibility request"),
    ("leave.record.view", "See leave records as an administrator"),
    ("leave.record.update", "Maintain records and log offline-sanctioned leave"),
    ("leave.calendar.view", "See the effective holiday calendar"),
    ("leave.calendar.publish", "Create and publish the holiday/RH calendar"),
    ("leave.policy.update", "Maintain the policy parameters and the hierarchy"),
    ("leave.threshold.update", "Configure the workflow SLA thresholds"),
    ("leave.balance.view", "See your own leave balances and history"),
    ("leave.application.export", "Obtain a printable copy of an application"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    # EL-UC-020: year-end lapses, carry-forward and the VL conversion.
    "leave.account.update",
    # XTP-EL-01: an SLA escalation that changes routing or responsibility.
    "leave.request.assign",
]

#: Enforced by narrowing a queryset rather than by refusing a request, so
#: holding one widens what you see; not holding it simply shows you less.
SCOPE_PERMISSIONS = [
    "leave.request.view",
    "leave.record.view",
]

#: Everyone on the payroll applies for their own leave, and nobody else's.
_EMPLOYEE = [
    "leave.request.view",
    "leave.request.create",
    "leave.request.delete",
    "leave.cancellation.create",
    "leave.extension.create",
    "leave.resumption.create",
    "leave.substitute.review",
    "leave.balance.view",
    "leave.application.export",
    "leave.calendar.view",
]

#: The Establishment step: verify and route, and record for the office.
_ESTABLISHMENT = [
    "leave.request.view",
    "leave.request.review",
    "leave.record.view",
]

#: A resolved final authority: recommends may pass through it, decisions end here.
_AUTHORITY = [
    "leave.request.view",
    "leave.request.review",
    "leave.request.approve",
    "leave.resumption.review",
    "leave.record.view",
]

#: The administrative role: configuration and record maintenance, no sanctions.
_ADMIN = [
    "leave.request.view",
    "leave.record.view",
    "leave.record.update",
    "leave.calendar.view",
    "leave.calendar.publish",
    "leave.policy.update",
    "leave.threshold.update",
]

#: Keyed by the designation name as it exists in globals_designation. The
#: per-department Unit Head designations also need leave.request.review, and
#: they are enumerated in the module's open questions rather than guessed here.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Deputy Registrar (Estt.)": [*_ESTABLISHMENT, "leave.request.approve"],
    "Dean Academic": _AUTHORITY,
    "Registrar": _AUTHORITY,
    "Director": _AUTHORITY,
    "acadadmin": _ADMIN,
}
