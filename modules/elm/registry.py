"""What the server tells the shell about the ELM module (ADR-0010).

Nav items carry `required_permission`; the server filters before sending, so a
link a role cannot use never reaches the browser.
"""
MODULE = {
    "code": "elm", "label": "Leave", "icon": "CalendarHeart",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.mine", "label": "My Leave", "icon": "ListChecks",
     "to": "/leave/mine",
     "required_permission": "elm.application.view_self", "sort_order": 5},
    {"code": "elm.balances", "label": "Balances", "icon": "Scale",
     "to": "/leave/balances",
     "required_permission": "elm.balance.view_self", "sort_order": 10},
    {"code": "elm.inbox", "label": "Leave Inbox", "icon": "Inbox",
     "to": "/leave/inbox",
     "required_permission": "elm.application.decide", "sort_order": 50},
    {"code": "elm.admin", "label": "Leave Setup", "icon": "Settings",
     "to": "/leave/admin",
     "required_permission": "elm.admin.manage", "sort_order": 60},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("elm.application.view_self", "View one's own leave applications"),
    ("elm.application.create", "Apply for leave"),
    ("elm.application.withdraw", "Withdraw a pending leave request"),
    ("elm.application.cancel", "Cancel an approved leave before it begins"),
    ("elm.application.view", "View leave applications within scope"),
    ("elm.application.decide", "Approve or reject a leave request"),
    ("elm.substitute.respond", "Accept or decline a substitute nomination"),
    ("elm.balance.view_self", "View one's own leave balances"),
    ("elm.admin.manage", "Maintain leave policy and holiday calendar"),
]

#: Performed by a service or scheduled task, so no designation holds them.
#: (Year-end processing is deferred in this pilot, so nothing is listed yet.)
SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "elm.application.view_self",
    "elm.application.create",
    "elm.application.withdraw",
    "elm.application.cancel",
    "elm.balance.view_self",
    "elm.substitute.respond",
]

_AUTHORITY = [
    "elm.application.view",
    "elm.application.decide",
]

_ADMIN = [
    "elm.application.view",
    "elm.admin.manage",
]

#: Keyed by the designation name as it exists in globals_designation. The basic
#: roles faculty/staff hold the self-service surface; heads and officers hold the
#: decision surface. `student` is a pilot convenience so the seeded demo account
#: can exercise the module — the baseline limits ELM to faculty and staff.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "student": _EMPLOYEE,
    "HOD (CSE)": _AUTHORITY,
    "HOD (ECE)": _AUTHORITY,
    "HOD (ME)": _AUTHORITY,
    "HOD (NS)": _AUTHORITY,
    "HOD (Design)": _AUTHORITY,
    "HOD (Liberal Arts)": _AUTHORITY,
    "Dean Academic": [*_AUTHORITY, *_ADMIN],
    "Deputy Registrar": [*_AUTHORITY, *_ADMIN],
    "Registrar": [*_AUTHORITY, *_ADMIN],
    "Director": _AUTHORITY,
}
