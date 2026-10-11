"""Navigation and module registry for Employee Leave Management (ELM).
"""

MODULE = {
    "code": "leave_module",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "HR & Administration",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # Employee self-service
    {
        "code": "leave.apply",
        "label": "Apply Leave",
        "icon": "CalendarPlus",
        "to": "/leave/apply",
        "required_permission": "leave.application.apply",
        "sort_order": 10,
    },
    {
        "code": "leave.history",
        "label": "Leave History & Balance",
        "icon": "ClockCounterClockwise",
        "to": "/leave/history",
        "required_permission": "leave.application.view_self",
        "sort_order": 20,
    },
    {
        "code": "leave.substitute_requests",
        "label": "Substitute Requests",
        "icon": "UserSwitch",
        "to": "/leave/substitute-requests",
        "required_permission": "leave.substitute.respond",
        "sort_order": 30,
    },
    # Authority / Sanctioning queues
    {
        "code": "leave.unit_head_reviews",
        "label": "Unit Head Approvals",
        "icon": "CheckSquare",
        "to": "/leave/unit-head-reviews",
        "required_permission": "leave.application.unit_head_review",
        "sort_order": 40,
    },
    {
        "code": "leave.establishment_routing",
        "label": "Establishment Verification",
        "icon": "FileSearch",
        "to": "/leave/establishment-routing",
        "required_permission": "leave.application.establishment_route",
        "sort_order": 50,
    },
    {
        "code": "leave.sanctioning_queue",
        "label": "Sanctioning Authority Queue",
        "icon": "Stamp",
        "to": "/leave/sanction-queue",
        "required_permission": "leave.application.sanction",
        "sort_order": 60,
    },
    # Admin
    {
        "code": "leave.admin_config",
        "label": "Leave Policy & Calendar",
        "icon": "GearSix",
        "to": "/leave/admin",
        "required_permission": "leave.policy.manage",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("leave.application.apply", "Apply for leave and extension"),
    ("leave.application.view_self", "View own leave balance and history"),
    ("leave.application.withdraw", "Withdraw pending leave application"),
    ("leave.application.cancel", "Cancel approved leave before start"),
    ("leave.application.resume", "Submit resumption of duty"),
    ("leave.substitute.respond", "Accept or decline substitute requests"),
    ("leave.application.unit_head_review", "Review and approve/recommend as Unit Head"),
    ("leave.application.establishment_route", "Verify and route leave in Establishment"),
    ("leave.application.sanction", "Sanction or reject routed leave applications"),
    ("leave.policy.manage", "Maintain policy, calendars, and SLA configuration"),
    ("leave.records.manage", "Maintain authorized leave records and sync offline leave"),
]

_EMPLOYEE = [
    "leave.application.apply",
    "leave.application.view_self",
    "leave.application.withdraw",
    "leave.application.cancel",
    "leave.application.resume",
    "leave.substitute.respond",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "leave.application.unit_head_review",
]

_ESTABLISHMENT = [
    *_EMPLOYEE,
    "leave.application.establishment_route",
    "leave.records.manage",
]

_SANCTIONING_AUTH = [
    *_EMPLOYEE,
    "leave.application.sanction",
]

_ADMIN = [
    *_EMPLOYEE,
    *_UNIT_HEAD,
    *_ESTABLISHMENT,
    *_SANCTIONING_AUTH,
    "leave.policy.manage",
    "leave.records.manage",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "student": [],
    "unit_head": _UNIT_HEAD,
    "hod": _UNIT_HEAD,
    "deputy_registrar": _ESTABLISHMENT,
    "dean": _SANCTIONING_AUTH,
    "registrar": _SANCTIONING_AUTH,
    "director": _SANCTIONING_AUTH,
    "leave_administrator": _ADMIN,
}
