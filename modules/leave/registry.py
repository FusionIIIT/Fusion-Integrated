"""What the server tells the shell about ELM (ADR-0010).

`code` is the module grant; the client manifest's `code` must equal it, and a
CI check asserts the two sets match.
"""
MODULE = {
    "code": "leave_management", "label": "Leave Management", "icon": "FaUmbrellaBeach",
    "base_path": "/leave", "nav_section": "Administration", "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    # -- employee -----------------------------------------------------------
    {"code": "leave.my_leave", "label": "My Leave", "icon": "FaListUl",
     "to": "/leave/my-leave",
     "required_permission": "leave_management.leave.view_self", "sort_order": 10},
    {"code": "leave.balances", "label": "My Balances", "icon": "FaBalanceScale",
     "to": "/leave/balances",
     "required_permission": "leave_management.leave.view_self", "sort_order": 20},
    {"code": "leave.substitute", "label": "Cover Requests", "icon": "FaUserFriends",
     "to": "/leave/substitute",
     "required_permission": "leave_management.substitute.respond", "sort_order": 30},

    # -- sanctioning / administrative --------------------------------------
    {"code": "leave.queue", "label": "Approval Queue", "icon": "FaInbox",
     "to": "/leave/queue",
     "required_permission": "leave_management.leave.review", "sort_order": 50},
    {"code": "leave.calendar", "label": "Calendar", "icon": "FaCalendarAlt",
     "to": "/leave/calendar",
     "required_permission": "leave_management.calendar.manage", "sort_order": 60},
    {"code": "leave.policy", "label": "Policy", "icon": "FaSlidersH",
     "to": "/leave/policy",
     "required_permission": "leave_management.policy.manage", "sort_order": 70},
    {"code": "leave.reports", "label": "Reports", "icon": "FaChartBar",
     "to": "/leave/reports",
     "required_permission": "leave_management.report.view", "sort_order": 80},
]

PERMISSIONS = [
    ("leave_management.leave.view_self", "See one's own leave and balances"),
    ("leave_management.leave.apply", "Apply for leave"),
    ("leave_management.leave.withdraw", "Withdraw a pending request"),
    ("leave_management.leave.cancel", "Request cancellation of approved leave"),
    ("leave_management.leave.extension", "Request an extension of ongoing leave"),
    ("leave_management.leave.resumption", "Report resumption of duty"),
    ("leave_management.substitute.respond", "Accept or decline a cover request"),
    ("leave_management.leave.view", "See leave requests within scope"),
    ("leave_management.leave.review", "Record Recommended / Not Recommended"),
    ("leave_management.leave.sanction", "Give the final sanction decision"),
    ("leave_management.leave.record_offline",
     "Record already-sanctioned offline leave"),
    ("leave_management.calendar.manage", "Maintain the holiday / RH calendar"),
    ("leave_management.policy.manage", "Maintain leave-policy parameters"),
    ("leave_management.report.view", "See leave reports and statistics"),
]

#: Only a service or a scheduled task performs these.
SYSTEM_PERMISSIONS = [
    "leave_management.yearend.process",
    "leave_management.sla.escalate",
]

_EMPLOYEE = [
    "leave_management.leave.view_self",
    "leave_management.leave.apply",
    "leave_management.leave.withdraw",
    "leave_management.leave.cancel",
    "leave_management.leave.extension",
    "leave_management.leave.resumption",
    "leave_management.substitute.respond",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "leave_management.leave.view",
    "leave_management.leave.review",
    "leave_management.leave.sanction",
    "leave_management.report.view",
]

_ADMIN = [
    "leave_management.leave.view",
    "leave_management.leave.sanction",
    "leave_management.leave.record_offline",
    "leave_management.calendar.manage",
    "leave_management.policy.manage",
    "leave_management.report.view",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "Faculty": _EMPLOYEE,
    "Staff": _EMPLOYEE,
    "HOD": _UNIT_HEAD,
    "Deputy Registrar (Estt.)": _ADMIN,
    "Dean": [*_ADMIN],
    "Registrar": _ADMIN,
    "Director": [
        "leave_management.leave.view",
        "leave_management.leave.sanction",
        "leave_management.report.view",
    ],
    "Leave Administrator": _ADMIN,
}
