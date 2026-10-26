"""ELM Module Navigation and Permission Registry (ADR-0010)."""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Administration",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "FilePlus",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 10,
    },
    {
        "code": "elm.mine",
        "label": "My Leaves",
        "icon": "ClockCounterClockwise",
        "to": "/elm/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 20,
    },
    {
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "ChartPie",
        "to": "/elm/balances",
        "required_permission": "elm.leave.view_self",
        "sort_order": 30,
    },
    {
        "code": "elm.substitute",
        "label": "Substitute Requests",
        "icon": "UserSwitch",
        "to": "/elm/substitute",
        "required_permission": "elm.leave.substitute",
        "sort_order": 40,
    },
    {
        "code": "elm.approvals",
        "label": "Leave Approvals",
        "icon": "CheckSquareOffset",
        "to": "/elm/approvals",
        "required_permission": "elm.leave.approve",
        "sort_order": 50,
    },
    {
        "code": "elm.authority",
        "label": "Final Sanctioning",
        "icon": "SealCheck",
        "to": "/elm/authority",
        "required_permission": "elm.leave.sanction",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("elm.leave.apply", "Apply for leave and station departure"),
    ("elm.leave.view_self", "View own leave applications and balance ledger"),
    ("elm.leave.substitute", "Review and respond to substitute nominations"),
    ("elm.leave.approve", "Review and sanction subordinate leave requests"),
    ("elm.leave.sanction", "Make final higher-sanction leave decisions"),
    ("elm.leave.admin", "Manage leave quotas, calendar cycles and adjustments"),
]

SYSTEM_PERMISSIONS = [
    "elm.leave.auto_lapse",
    "elm.leave.annual_credit",
]

_EMPLOYEE = [
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.substitute",
]

_UNIT_HEAD = [*_EMPLOYEE, "elm.leave.approve"]

_ADMIN = [
    *_UNIT_HEAD,
    "elm.leave.admin",
    "elm.leave.sanction",
]

_SANCTIONING_AUTHORITY = [*_EMPLOYEE, "elm.leave.sanction"]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": _UNIT_HEAD,
    "dean": [*_UNIT_HEAD, "elm.leave.sanction"],
    "registrar": [*_UNIT_HEAD, "elm.leave.sanction"],
    "director": _SANCTIONING_AUTHORITY,
    "leave_admin": _ADMIN,
}
