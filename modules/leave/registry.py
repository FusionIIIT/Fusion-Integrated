"""What the server tells the shell about leave (ADR-0010).

Every nav item carries `required_permission` and the server filters before
sending, so a link a role cannot use never reaches the browser.

Designation names come from the specification and are keys into
`globals_designation`, so a role that exists there already works here.
"""
MODULE = {
    "code": "leave", "label": "Employee Leave Management", "icon": "CalendarCheck",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- every employee ------------------------------------------------------
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "CalendarPlus",
     "to": "/leave/apply",
     "required_permission": "leave.request.create", "sort_order": 5},
    {"code": "leave.mine", "label": "My Requests", "icon": "ClipboardList",
     "to": "/leave/requests",
     "required_permission": "leave.request.view_self", "sort_order": 10},
    {"code": "leave.balances", "label": "My Balances", "icon": "Scale",
     "to": "/leave/balances",
     "required_permission": "leave.request.view_self", "sort_order": 15},
    {"code": "leave.substitutions", "label": "Substitute Requests",
     "icon": "UserRoundCheck",
     "to": "/leave/substitutions",
     "required_permission": "leave.substitute.respond", "sort_order": 20},

    # -- deciding authorities ------------------------------------------------
    {"code": "leave.approvals", "label": "Approvals", "icon": "Gavel",
     "to": "/leave/approvals",
     "required_permission": "leave.request.approve", "sort_order": 40},
    {"code": "leave.exceptions", "label": "Leave Exceptions",
     "icon": "TriangleAlert",
     "to": "/leave/exceptions",
     "required_permission": "leave.record.maintain", "sort_order": 50},

    # -- leave administration ------------------------------------------------
    {"code": "leave.admin", "label": "Leave Administration", "icon": "Settings2",
     "to": "/leave/admin",
     "required_permission": "leave.record.maintain", "sort_order": 60},
    {"code": "leave.accounts", "label": "Leave Accounts", "icon": "BookOpen",
     "to": "/leave/accounts",
     "required_permission": "leave.balance.update", "sort_order": 70},
    {"code": "leave.calendar", "label": "Holiday Calendar", "icon": "CalendarDays",
     "to": "/leave/admin/calendar",
     "required_permission": "leave.record.maintain", "sort_order": 80},
    {"code": "leave.year_end", "label": "Year-End Close", "icon": "CalendarSync",
     "to": "/leave/admin/year-end",
     "required_permission": "leave.record.maintain", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
#: The seven `leave.request.*`/`leave.balance.update`/`leave.type.manage` codes
#: are the ones the surviving IAM catalogue already issues, so they are unchanged.
PERMISSIONS = [
    ("leave.request.view_self", "See one's own leave requests"),
    ("leave.request.create", "Apply for leave, and withdraw one's own request"),
    ("leave.request.delete", "Delete a draft leave request"),
    ("leave.request.view", "See leave requests within scope"),
    ("leave.request.approve", "Decide a leave request one has been asked to decide"),
    ("leave.balance.update", "Adjust a leave account"),
    ("leave.type.manage", "Manage leave types and entitlements"),
    ("leave.substitute.respond", "Answer a substitute nomination"),
    ("leave.record.maintain",
     "Maintain leave records, hierarchy, calendar and thresholds"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "leave.year_end.process",
    "leave.sla.remind",
    "leave.sla.escalate",
]

_EMPLOYEE = [
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.delete",
]

_SUBSTITUTE = _EMPLOYEE + [
    "leave.substitute.respond",
]

# ACT-03 decides and reviews; it is not an administrator.
_UNIT_HEAD = [
    *_SUBSTITUTE,
    "leave.request.view",
    "leave.request.approve",
]

# ACT-04 routes and records; it does not decide.
_ESTABLISHMENT = [
    *_UNIT_HEAD,
]

# ACT-05/06: the final sanctioning authority.
_SANCTIONING_AUTHORITY = [
    *_UNIT_HEAD,
]

_DIRECTOR = [
    *_UNIT_HEAD,
]

# ACT-08: maintenance and accounts, deliberately without `leave.request.approve`.
# BR-EL-037: record maintenance is not sanctioning.
_LEAVE_ADMIN = [
    "leave.request.view",
    "leave.request.view_self",
    "leave.record.maintain",
    "leave.balance.update",
    "leave.type.manage",
]

#: Keyed by the designation name as it exists in globals_designation. A name that
#: is not there simply gets no grants; nothing is invented for it here.
ROLE_GRANTS = {
    "employee": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "substitute": _SUBSTITUTE,
    "unit_head": _UNIT_HEAD,
    "deputy_registrar_establishment": _ESTABLISHMENT,
    "dean": _SANCTIONING_AUTHORITY,
    "registrar": _SANCTIONING_AUTHORITY,
    "director": _DIRECTOR,
    "leave_administrator": _LEAVE_ADMIN,
}
