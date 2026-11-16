"""Server-side registry and navigation specification for Leave Management (ELM).

Conforms to ADR-0010 and the permission manifest requirement.
"""
from __future__ import annotations

MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/leave",
    "nav_section": "Campus",
    "sort_order": 20,
    "status": "active",
}

PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests and balance"),
    ("leave.request.create", "Apply for leave"),
    ("leave.request.delete", "Cancel own pending request"),
    ("leave.request.view", "View leave requests, within scope"),
    ("leave.request.approve", "Approve or reject a leave request"),
    ("leave.balance.update", "Adjust a leave balance"),
    ("leave.type.manage", "Configure leave types and entitlement rules"),
]

SYSTEM_PERMISSIONS = []

SCOPE_PERMISSIONS = [
    "leave.request.view",
]

_APPLICANT = [
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.delete",
]

_AUTHORITY = [
    *_APPLICANT,
    "leave.request.view",
    "leave.request.approve",
]

_ADMIN = [
    *_AUTHORITY,
    "leave.balance.update",
    "leave.type.manage",
]

ROLE_GRANTS = {
    "student": _APPLICANT,
    "faculty": _APPLICANT,
    "staff": _APPLICANT,
    "HOD": _AUTHORITY,
    "Dean Academic": _AUTHORITY,
    "Registrar": _ADMIN,
    "Director": _ADMIN,
    "acadadmin": _ADMIN,
}

NAV_ITEMS = [
    {
        "code": "leave.apply",
        "label": "Apply for Leave",
        "icon": "FaCalendarPlus",
        "to": "/leave/apply",
        "required_permission": "leave.request.create",
        "sort_order": 10,
    },
    {
        "code": "leave.mine",
        "label": "My Leaves",
        "icon": "FaCalendarCheck",
        "to": "/leave/mine",
        "required_permission": "leave.request.view_self",
        "sort_order": 20,
    },
    {
        "code": "leave.balances",
        "label": "Leave Balances",
        "icon": "FaChartPie",
        "to": "/leave/balances",
        "required_permission": "leave.request.view_self",
        "sort_order": 30,
    },
    {
        "code": "leave.review",
        "label": "Pending Approvals",
        "icon": "FaInbox",
        "to": "/leave/review",
        "required_permission": "leave.request.approve",
        "sort_order": 40,
    },
]
