"""What the server tells the shell about Employee Leave Management."""

MODULE = {
    "code": "leave",
    "label": "Leave",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.mine",
        "label": "My Leave",
        "icon": "CalendarBlank",
        "to": "/leave/mine",
        "required_permission": "leave.request.view_self",
        "sort_order": 10,
    },
    {
        "code": "leave.apply",
        "label": "Apply",
        "icon": "PlusCircle",
        "to": "/leave/apply",
        "required_permission": "leave.request.create",
        "sort_order": 20,
    },
    {
        "code": "leave.substitute",
        "label": "Standing In",
        "icon": "UsersThree",
        "to": "/leave/substitute",
        "required_permission": "leave.substitute.respond",
        "sort_order": 30,
    },
    {
        "code": "leave.review",
        "label": "Review Queue",
        "icon": "Checks",
        "to": "/leave/review",
        "required_permission": "leave.request.review",
        "sort_order": 40,
    },
    {
        "code": "leave.route",
        "label": "Routing Queue",
        "icon": "Export",
        "to": "/leave/routing",
        "required_permission": "leave.request.route",
        "sort_order": 50,
    },
    {
        "code": "leave.sanction",
        "label": "Sanction Queue",
        "icon": "Stamp",
        "to": "/leave/sanction",
        "required_permission": "leave.request.sanction",
        "sort_order": 60,
    },
    {
        "code": "leave.resumption",
        "label": "Resumptions",
        "icon": "ArrowsClockwise",
        "to": "/leave/resumptions",
        "required_permission": "leave.resumption.verify",
        "sort_order": 70,
    },
    {
        "code": "leave.balances",
        "label": "Balances",
        "icon": "Gavel",
        "to": "/leave/balances",
        "required_permission": "leave.balance.view",
        "sort_order": 80,
    },
    {
        "code": "leave.policy",
        "label": "Policy & Calendar",
        "icon": "Wrench",
        "to": "/leave/policy",
        "required_permission": "leave.policy.manage",
        "sort_order": 90,
    },
]

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
    "leave.lifecycle.advance",
    "leave.sla.process",
    "leave.yearend.run",
]

SCOPE_PERMISSIONS = [
    "leave.request.view_self",
]

_EMPLOYEE = [
    "leave.request.create",
    "leave.request.view_self",
    "leave.request.withdraw",
    "leave.substitute.respond",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "leave.balance.view",
    "leave.request.review",
]

_ESTABLISHMENT = [
    *_EMPLOYEE,
    "leave.balance.view",
    "leave.request.route",
    "leave.resumption.verify",
]

_SANCTIONER = [
    *_EMPLOYEE,
    "leave.balance.view",
    "leave.request.review",
    "leave.request.route",
    "leave.request.sanction",
]

_ADMIN = [
    *_ESTABLISHMENT,
    "leave.calendar.manage",
    "leave.offline.record",
    "leave.policy.manage",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Assistant Professor": _EMPLOYEE,
    "Associate Professor": _EMPLOYEE,
    "Professor": _EMPLOYEE,
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
    "Dean Academic": _SANCTIONER,
    "Dean (P&D)": _SANCTIONER,
    "Dean (R&D)": _SANCTIONER,
    "Dean_s": _SANCTIONER,
    "Registrar": _SANCTIONER,
    "Director": _SANCTIONER,
    "acadadmin": _ADMIN,
}
