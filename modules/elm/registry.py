"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "leave_elm", "label": "Employee Leave Management",
    "icon": "CalendarBlank", "base_path": "/elm",
    "nav_section": "Employee Leave Management", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave_elm.my_applications", "label": "My Leave",
     "icon": "ClipboardText", "to": "/elm/applications",
     "required_permission": "leave_elm.application.view_self",
     "sort_order": 10},
    {"code": "leave_elm.apply", "label": "Apply for Leave",
     "icon": "CalendarBlank", "to": "/elm/apply",
     "required_permission": "leave_elm.application.apply",
     "sort_order": 20},
    {"code": "leave_elm.substitute_requests", "label": "Substitute Requests",
     "icon": "UserCheck", "to": "/elm/substitute-requests",
     "required_permission": "leave_elm.substitute.respond",
     "sort_order": 30},
    {"code": "leave_elm.unit_review", "label": "Unit Review",
     "icon": "Users", "to": "/elm/unit-review",
     "required_permission": "leave_elm.application.approve",
     "sort_order": 40},
    {"code": "leave_elm.establishment", "label": "Establishment Processing",
     "icon": "Checks", "to": "/elm/establishment",
     "required_permission": "leave_elm.application.verify",
     "sort_order": 50},
    {"code": "leave_elm.sanctions", "label": "Sanctioning Queue",
     "icon": "Signature", "to": "/elm/sanctions",
     "required_permission": "leave_elm.application.approve",
     "sort_order": 60},
    {"code": "leave_elm.resumptions", "label": "Resumptions",
     "icon": "Checks", "to": "/elm/resumptions",
     "required_permission": "leave_elm.resumption.review",
     "sort_order": 70},
    {"code": "leave_elm.calendar", "label": "Holiday / RH Calendar",
     "icon": "CalendarBlank", "to": "/elm/calendar",
     "required_permission": "leave_elm.calendar.view",
     "sort_order": 80},
    {"code": "leave_elm.admin", "label": "Leave Administration",
     "icon": "Buildings", "to": "/elm/admin",
     "required_permission": "leave_elm.admin.configure",
     "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave_elm.application.view_self", "View one's own leave applications"),
    ("leave_elm.application.view", "View leave applications within scope"),
    ("leave_elm.application.apply", "Submit a leave application"),
    ("leave_elm.application.withdraw", "Withdraw a pending leave application"),
    ("leave_elm.application.cancel", "Request cancellation of sanctioned leave"),
    ("leave_elm.application.extend", "Request an extension of sanctioned leave"),
    ("leave_elm.application.print", "Obtain a printable leave application"),
    ("leave_elm.application.approve", "Approve or reject a leave application"),
    ("leave_elm.application.recommend", "Recommend a leave application"),
    ("leave_elm.application.verify", "Verify leave details for processing"),
    ("leave_elm.application.route", "Route a leave application for decision"),
    ("leave_elm.substitute.nominate", "Nominate a replacement substitute"),
    ("leave_elm.substitute.respond", "Accept or decline a substitute request"),
    ("leave_elm.leave.balance.view", "View one's own leave balances"),
    ("leave_elm.leave.history.view", "View one's own leave history"),
    ("leave_elm.resumption.submit", "Submit a leave resumption"),
    ("leave_elm.resumption.review", "Review a leave resumption"),
    ("leave_elm.admin.offline_record", "Record offline-sanctioned leave"),
    ("leave_elm.admin.configure", "Maintain leave policy and hierarchy configuration"),
    ("leave_elm.calendar.view", "View the holiday and restricted-holiday calendar"),
    ("leave_elm.calendar.publish", "Publish the holiday and restricted-holiday calendar"),
    ("leave_elm.records.manage", "Maintain authorized leave records"),
    ("leave_elm.sla.configure", "Configure leave processing SLA thresholds"),
]

_EMPLOYEE = [
    "leave_elm.application.view_self",
    "leave_elm.application.apply",
    "leave_elm.application.withdraw",
    "leave_elm.application.cancel",
    "leave_elm.application.extend",
    "leave_elm.application.print",
    "leave_elm.substitute.nominate",
    "leave_elm.leave.balance.view",
    "leave_elm.leave.history.view",
    "leave_elm.resumption.submit",
    "leave_elm.calendar.view",
]

_SUBSTITUTE = [
    "leave_elm.substitute.respond",
]

_UNIT_HEAD = [
    "leave_elm.application.view",
    "leave_elm.application.approve",
    "leave_elm.application.recommend",
    "leave_elm.resumption.review",
]

_ESTABLISHMENT = [
    "leave_elm.application.view",
    "leave_elm.application.verify",
    "leave_elm.application.route",
    "leave_elm.application.approve",
    "leave_elm.resumption.review",
]

_SANCTIONING_AUTHORITY = [
    "leave_elm.application.view",
    "leave_elm.application.approve",
    "leave_elm.resumption.review",
]

_LEAVE_ADMIN = [
    "leave_elm.application.view",
    "leave_elm.admin.offline_record",
    "leave_elm.admin.configure",
    "leave_elm.calendar.view",
    "leave_elm.calendar.publish",
    "leave_elm.records.manage",
    "leave_elm.sla.configure",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Substitute / Responsibility Holder": _SUBSTITUTE,
    "Unit Head": _UNIT_HEAD,
    "Deputy Registrar (Estt.)": _ESTABLISHMENT,
    "Dean": _SANCTIONING_AUTHORITY,
    "Registrar": _SANCTIONING_AUTHORITY,
    "Director": _SANCTIONING_AUTHORITY,
    "Leave Administrator": _LEAVE_ADMIN,
}