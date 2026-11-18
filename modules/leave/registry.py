"""What the server tells the shell about ELM, and every permission it knows.

Nav items carry `required_permission` and the server filters before sending,
so a link a role cannot use never reaches the browser.
"""
MODULE = {
    "code": "leave", "label": "Leave", "icon": "CalendarCheck",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "FilePlus",
     "to": "/leave/apply", "required_permission": "leave.application.create",
     "sort_order": 10},
    {"code": "leave.mine", "label": "My Leave", "icon": "CalendarCheck",
     "to": "/leave/mine", "required_permission": "leave.application.view_self",
     "sort_order": 20},
    {"code": "leave.substitutions", "label": "Substitute Requests",
     "icon": "UserSwitch", "to": "/leave/substitutions",
     "required_permission": "leave.substitute.respond", "sort_order": 30},
    {"code": "leave.requests", "label": "Leave Requests", "icon": "ClipboardText",
     "to": "/leave/requests", "required_permission": "leave.request.review",
     "sort_order": 40},
    {"code": "leave.sanctions", "label": "Sanction Queue", "icon": "Stamp",
     "to": "/leave/sanctions", "required_permission": "leave.request.sanction",
     "sort_order": 50},
    {"code": "leave.holidays", "label": "Holiday Calendar", "icon": "CalendarBlank",
     "to": "/leave/holidays", "required_permission": "leave.policy.manage",
     "sort_order": 60},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave.application.create", "Apply for leave"),
    ("leave.application.view_self", "See one's own leave balances and history"),
    ("leave.application.withdraw",
     "Withdraw a pending request or ask to cancel an approved leave"),
    ("leave.substitute.respond", "Accept or decline a substitute nomination"),
    ("leave.request.review", "Review as Unit Head: decide CL/RH, recommend the rest"),
    ("leave.request.sanction", "Take the final sanctioning decision"),
    ("leave.policy.manage", "Maintain the holiday/RH calendar and leave records"),
]

#: Performed by a scheduled job, so no designation holds them.
SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave.application.create",
    "leave.application.view_self",
    "leave.application.withdraw",
    "leave.substitute.respond",
]

_UNIT_HEAD = [*_EMPLOYEE, "leave.request.review"]

_AUTHORITY = [*_EMPLOYEE, "leave.request.sanction"]

_ESTABLISHMENT = [*_AUTHORITY, "leave.request.review", "leave.policy.manage"]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "HOD": _UNIT_HEAD,
    "Dean Academic": [*_AUTHORITY, "leave.request.review"],
    "Registrar": _AUTHORITY,
    "Director": _AUTHORITY,
    "Deputy Registrar": _ESTABLISHMENT,
}
