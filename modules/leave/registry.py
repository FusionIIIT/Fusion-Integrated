"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending, so
a link a role cannot use never reaches the browser.
"""
MODULE = {
    "code": "leave", "label": "Leave", "icon": "FaRegCalendarCheck",
    "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
    "status": "active",
}

PERMISSIONS = [
    ("leave.request.create", "Apply for leave"),
    ("leave.request.view_self", "See your own leave"),
    ("leave.request.withdraw", "Withdraw your pending request"),
    ("leave.substitute.respond", "Accept or decline standing in for someone"),
    ("leave.request.review", "Review as unit head and record a recommendation"),
    ("leave.request.route", "Route a recommended request to the competent authority"),
    ("leave.request.sanction", "Take the final decision on a leave request"),
    ("leave.resumption.verify", "Verify a reported resumption of duty"),
    ("leave.balance.view", "See leave balances across employees"),
    ("leave.policy.manage", "Maintain leave policy and entitlement"),
    ("leave.calendar.manage", "Maintain the holiday and restricted-holiday calendar"),
    ("leave.offline.record", "Record leave sanctioned outside the system"),
]

SYSTEM_PERMISSIONS = [
    ("leave.yearend.run", "Run the year-end lapse, carry-forward and conversion"),
]

#: Enforced by narrowing the queryset rather than by refusing the request.
SCOPE_PERMISSIONS = ["leave.request.view_self"]

_EMPLOYEE = [
    "leave.request.create",
    "leave.request.view_self",
    "leave.request.withdraw",
    "leave.substitute.respond",
]
_UNIT_HEAD = [*_EMPLOYEE, "leave.request.review", "leave.balance.view"]
_ESTABLISHMENT = [
    *_EMPLOYEE,
    "leave.request.route",
    "leave.resumption.verify",
    "leave.balance.view",
]
_AUTHORITY = [*_UNIT_HEAD, "leave.request.sanction", "leave.request.route"]
_ADMIN = [
    *_ESTABLISHMENT,
    "leave.policy.manage",
    "leave.calendar.manage",
    "leave.offline.record",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "Professor": _UNIT_HEAD,
    "Associate Professor": _EMPLOYEE,
    "Assistant Professor": _EMPLOYEE,
    "Junior Assistant": _EMPLOYEE,
    "Senior Assistant": _EMPLOYEE,
    "Upper Division Clerk": _EMPLOYEE,
    "HOD (CSE)": _UNIT_HEAD,
    "HOD (ECE)": _UNIT_HEAD,
    "HOD (ME)": _UNIT_HEAD,
    "HOD (Design)": _UNIT_HEAD,
    "HOD (NS)": _UNIT_HEAD,
    "HOD (Liberal Arts)": _UNIT_HEAD,
    "Deputy Registrar": _ESTABLISHMENT,
    "dracad": _ESTABLISHMENT,
    "Registrar": _AUTHORITY,
    "Dean Academic": _AUTHORITY,
    "Dean (R&D)": _AUTHORITY,
    "Dean (P&D)": _AUTHORITY,
    "Dean_s": _AUTHORITY,
    "Director": _AUTHORITY,
    "acadadmin": _ADMIN,
}

NAV_ITEMS = [
    # -- employee ---------------------------------------------------------
    {"code": "leave.mine", "label": "My Leave", "icon": "FaRegCalendarCheck",
     "to": "/leave", "required_permission": "leave.request.view_self",
     "sort_order": 10},
    {"code": "leave.apply", "label": "Apply", "icon": "FaPlusCircle",
     "to": "/leave/apply", "required_permission": "leave.request.create",
     "sort_order": 20},
    {"code": "leave.substitute", "label": "Standing In", "icon": "FaUserFriends",
     "to": "/leave/substitute", "required_permission": "leave.substitute.respond",
     "sort_order": 30},

    # -- unit head and above ----------------------------------------------
    {"code": "leave.review", "label": "Review Queue", "icon": "FaClipboardCheck",
     "to": "/leave/review", "required_permission": "leave.request.review",
     "sort_order": 40},
    {"code": "leave.route", "label": "Routing Queue", "icon": "FaShareSquare",
     "to": "/leave/routing", "required_permission": "leave.request.route",
     "sort_order": 50},
    {"code": "leave.sanction", "label": "Sanction Queue", "icon": "FaStamp",
     "to": "/leave/sanction", "required_permission": "leave.request.sanction",
     "sort_order": 60},
    {"code": "leave.resumption", "label": "Resumptions", "icon": "FaUndo",
     "to": "/leave/resumptions", "required_permission": "leave.resumption.verify",
     "sort_order": 70},

    # -- administration ----------------------------------------------------
    {"code": "leave.balances", "label": "Balances", "icon": "FaBalanceScale",
     "to": "/leave/balances", "required_permission": "leave.balance.view",
     "sort_order": 80},
    {"code": "leave.policy", "label": "Policy & Calendar", "icon": "FaCog",
     "to": "/leave/policy", "required_permission": "leave.policy.manage",
     "sort_order": 90},
]
