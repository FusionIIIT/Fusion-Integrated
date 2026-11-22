"""Leave module registry (ADR-0010).

Defines navigation items, module metadata, permissions, and role mappings.
"""
from __future__ import annotations

MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # -- Employee self-service --
    {
        "code": "leave.apply",
        "label": "Apply for Leave",
        "icon": "CalendarPlus",
        "to": "/leave/apply",
        "required_permission": "leave.application.create",
        "sort_order": 10,
    },
    {
        "code": "leave.mine",
        "label": "My Leaves",
        "icon": "CalendarCheck",
        "to": "/leave/mine",
        "required_permission": "leave.application.view_self",
        "sort_order": 20,
    },
    {
        "code": "leave.balances",
        "label": "Balances & History",
        "icon": "Wallet",
        "to": "/leave/balances",
        "required_permission": "leave.application.view_self",
        "sort_order": 30,
    },
    {
        "code": "leave.substitutes",
        "label": "Substitute Requests",
        "icon": "UserSwitch",
        "to": "/leave/substitutes",
        "required_permission": "leave.substitute.respond",
        "sort_order": 40,
    },
    {
        "code": "leave.calendar",
        "label": "Holidays & RH",
        "icon": "Calendar",
        "to": "/leave/calendar",
        "required_permission": "leave.calendar.view",
        "sort_order": 50,
    },

    # -- Reviewers & Sanctioning Authorities --
    {
        "code": "leave.approvals",
        "label": "Leave Approvals",
        "icon": "CheckSquareOffset",
        "to": "/leave/approvals",
        "required_permission": "leave.application.review",
        "sort_order": 60,
    },

    # -- Administration --
    {
        "code": "leave.admin",
        "label": "Leave Administration",
        "icon": "GearSix",
        "to": "/leave/admin",
        "required_permission": "leave.admin.manage",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("leave.application.create", "Apply for leave"),
    ("leave.application.view_self", "View own applications and balance history"),
    ("leave.application.withdraw", "Withdraw own pending application"),
    ("leave.application.cancel", "Request cancellation of approved leave"),
    ("leave.application.extend", "Request leave extension"),
    ("leave.application.resume", "Submit return to duty resumption"),
    ("leave.substitute.respond", "Accept or decline nominated responsibility"),
    ("leave.application.review", "Review and recommend leave requests"),
    ("leave.application.sanction", "Sanction or reject leave requests"),
    ("leave.calendar.view", "View published holiday and RH calendars"),
    ("leave.calendar.manage", "Publish and edit holiday and RH calendars"),
    ("leave.calendar.vacation_sync", "Synchronize vacation periods from Academic Calendar"),
    ("leave.admin.manage", "Manage leave policies, records, and offline entries"),
]

SYSTEM_PERMISSIONS = [
    "leave.sla.process",
    "leave.year_end.process",
]

_EMPLOYEE = [
    "leave.application.create",
    "leave.application.view_self",
    "leave.application.withdraw",
    "leave.application.cancel",
    "leave.application.extend",
    "leave.application.resume",
    "leave.substitute.respond",
    "leave.calendar.view",
]

_REVIEWER = [
    *_EMPLOYEE,
    "leave.application.review",
]

_SANCTIONER = [
    *_REVIEWER,
    "leave.application.sanction",
]

_ADMIN = [
    *_SANCTIONER,
    "leave.calendar.manage",
    "leave.calendar.vacation_sync",
    "leave.admin.manage",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "HOD": _REVIEWER,
    "unit_head": _REVIEWER,
    "deputy_registrar": _REVIEWER,
    "Dean Academic": _SANCTIONER,
    "Dean Faculty": _SANCTIONER,
    "dean": _SANCTIONER,
    "registrar": _SANCTIONER,
    "director": _SANCTIONER,
    "leave_admin": _ADMIN,
    "admin": _ADMIN,
    "academic_calendar": ["leave.calendar.vacation_sync"],
}
