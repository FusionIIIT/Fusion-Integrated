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
    ("elm.application.resume", "Report return to duty after approved leave"),
    ("elm.application.view", "View leave applications within scope"),
    ("elm.application.recommend", "Recommend or not recommend higher-sanction leave"),
    ("elm.application.decide", "Approve or reject a leave request"),
    ("elm.substitute.respond", "Accept or decline a substitute nomination"),
    ("elm.balance.view_self", "View one's own leave balances"),
    ("elm.admin.manage", "Maintain leave policy and holiday calendar"),
    ("elm.admin.offline", "Record authorized offline-sanctioned leave"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "elm.application.view_self",
    "elm.application.create",
    "elm.application.withdraw",
    "elm.application.cancel",
    "elm.application.resume",
    "elm.balance.view_self",
    "elm.substitute.respond",
]

_UNIT_HEAD = [
    "elm.application.view",
    "elm.application.recommend",
    "elm.application.decide",
]

_SANCTIONING = [
    "elm.application.view",
    "elm.application.decide",
]

_ADMIN = [
    "elm.application.view",
    "elm.admin.manage",
    "elm.admin.offline",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "student": _EMPLOYEE,
    "HOD (CSE)": [*_EMPLOYEE, *_UNIT_HEAD],
    "HOD (ECE)": [*_EMPLOYEE, *_UNIT_HEAD],
    "HOD (ME)": [*_EMPLOYEE, *_UNIT_HEAD],
    "HOD (NS)": [*_EMPLOYEE, *_UNIT_HEAD],
    "HOD (Design)": [*_EMPLOYEE, *_UNIT_HEAD],
    "HOD (Liberal Arts)": [*_EMPLOYEE, *_UNIT_HEAD],
    "Dean Academic": [*_EMPLOYEE, *_SANCTIONING, *_ADMIN],
    "Deputy Registrar": [*_EMPLOYEE, *_SANCTIONING, *_ADMIN],
    "Registrar": [*_EMPLOYEE, *_SANCTIONING, *_ADMIN],
    "Director": [*_EMPLOYEE, *_SANCTIONING],
}
