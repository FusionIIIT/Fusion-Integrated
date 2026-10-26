"""Module registry for Employee Leave Management (ELM).

Defines navigation items, declared permissions, and default role grants.
Seeded by `manage.py seed_modules`.
"""

MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.apply",
        "label": "Apply for Leave",
        "icon": "PencilSimple",
        "to": "/leave/apply",
        "required_permission": "leave_elm.application.apply",
        "sort_order": 10,
    },
    {
        "code": "leave.mine",
        "label": "My Applications",
        "icon": "ListChecks",
        "to": "/leave/mine",
        "required_permission": "leave_elm.application.view",
        "sort_order": 20,
    },
    {
        "code": "leave.balance",
        "label": "Leave Balance",
        "icon": "Scales",
        "to": "/leave/balance",
        "required_permission": "leave_elm.balance.view",
        "sort_order": 30,
    },
    {
        "code": "leave.substitute",
        "label": "Substitute Requests",
        "icon": "UserSwitch",
        "to": "/leave/substitute",
        "required_permission": "leave_elm.substitute.respond",
        "sort_order": 40,
    },
    {
        "code": "leave.approvals",
        "label": "Approvals",
        "icon": "UserCheck",
        "to": "/leave/approvals",
        "required_permission": "leave_elm.unit_head.review",
        "sort_order": 50,
    },
    {
        "code": "leave.calendar",
        "label": "Holiday Calendar",
        "icon": "CalendarCheck",
        "to": "/leave/calendar",
        "required_permission": "leave_elm.calendar.view",
        "sort_order": 60,
    },
    {
        "code": "leave.types",
        "label": "Leave Policies",
        "icon": "Gear",
        "to": "/leave/types",
        "required_permission": "leave_elm.policy.manage",
        "sort_order": 70,
    },
    {
        "code": "leave.offline_entry",
        "label": "Offline Sanctions",
        "icon": "FileText",
        "to": "/leave/offline-entry",
        "required_permission": "leave_elm.admin.sync_offline",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("leave_elm.application.view", "View leave applications and history"),
    ("leave_elm.application.apply", "Apply for leave"),
    ("leave_elm.application.withdraw", "Withdraw pending leave applications"),
    ("leave_elm.application.cancel", "Request cancellation of approved leave"),
    ("leave_elm.substitute.respond", "Accept or decline substitute responsibility"),
    ("leave_elm.unit_head.review", "Review and recommend or decide leave requests at Unit Head"),
    ("leave_elm.establishment.route", "Verify and route higher-sanction leave requests"),
    ("leave_elm.sanction.decide", "Make final sanctioning decision on routed leave requests"),
    ("leave_elm.director.self_sanction", "Perform Director self-sanction decision"),
    ("leave_elm.balance.view", "View personal or department leave balances"),
    ("leave_elm.calendar.view", "View published institute holidays and restricted holidays"),
    ("leave_elm.calendar.manage", "Manage and publish holiday and RH calendar"),
    ("leave_elm.policy.manage", "Manage leave categories, entitlements and parameters"),
    ("leave_elm.admin.sync_offline", "Record offline/paper sanctioned leave"),
    ("leave_elm.admin.year_end", "Execute year-end rollover, lapse, and conversion"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave_elm.application.view",
    "leave_elm.application.apply",
    "leave_elm.application.withdraw",
    "leave_elm.application.cancel",
    "leave_elm.substitute.respond",
    "leave_elm.balance.view",
    "leave_elm.calendar.view",
]

_UNIT_HEAD = _EMPLOYEE + [
    "leave_elm.unit_head.review",
]

_ESTABLISHMENT = _EMPLOYEE + [
    "leave_elm.establishment.route",
]

_SANCTIONING_AUTHORITY = _UNIT_HEAD + [
    "leave_elm.sanction.decide",
]

_DIRECTOR = _SANCTIONING_AUTHORITY + [
    "leave_elm.director.self_sanction",
]

_LEAVE_ADMIN = [
    "leave_elm.application.view",
    "leave_elm.balance.view",
    "leave_elm.calendar.view",
    "leave_elm.calendar.manage",
    "leave_elm.policy.manage",
    "leave_elm.admin.sync_offline",
    "leave_elm.admin.year_end",
]

ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Unit Head": _UNIT_HEAD,
    "Deputy Registrar (Estt.)": _ESTABLISHMENT,
    "Dean": _SANCTIONING_AUTHORITY,
    "Registrar": _SANCTIONING_AUTHORITY,
    "Director": _DIRECTOR,
    "Leave Admin": _LEAVE_ADMIN,
}
