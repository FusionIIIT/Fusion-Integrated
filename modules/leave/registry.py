from __future__ import annotations

"""
What the server tells the shell about this module (EL-UC-NNN, BR-EL-NNN).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.mine",
        "label": "My Leave",
        "icon": "FaCalendarAlt",
        "to": "/leave/mine",
        "required_permission": "leave.request.view_self",
        "sort_order": 10,
    },
    {
        "code": "leave.approvals",
        "label": "Leave Approvals",
        "icon": "FaCheckDouble",
        "to": "/leave/approvals",
        "required_permission": "leave.request.view_self",
        "sort_order": 20,
    },
    {
        "code": "leave.holidays",
        "label": "Holiday Calendar",
        "icon": "FaClipboardList",
        "to": "/leave/holidays",
        "required_permission": "leave.request.view_self",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("leave.request.create", "Apply for leave"),
    ("leave.request.view_self", "View own leave requests and history"),
    ("leave.balance.view", "View own leave balances"),
    ("leave.substitute.respond", "Accept or decline substitute duty"),
    ("leave.request.review", "Review unit head leave requests"),
    ("leave.resumption.verify", "Verify resumption of leave"),
    ("leave.request.route", "Route higher-sanction leave requests"),
    ("leave.request.sanction", "Sanction leave requests"),
    ("leave.policy.manage", "Manage leave policies"),
    ("leave.calendar.manage", "Manage leave calendar"),
    ("leave.offline.record", "Record offline-sanctioned leave"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave.request.create",
    "leave.request.view_self",
    "leave.balance.view",
    "leave.substitute.respond",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "leave.request.review",
    "leave.resumption.verify",
]

_DEPUTY_REGISTRAR = [
    *_EMPLOYEE,
    "leave.request.route",
]

_SANCTIONING = [
    *_EMPLOYEE,
    "leave.request.sanction",
]

_LEAVE_ADMIN = [
    "leave.policy.manage",
    "leave.calendar.manage",
    "leave.offline.record",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": _UNIT_HEAD,
    "Deputy Registrar": _DEPUTY_REGISTRAR,
    "Registrar": _SANCTIONING,
    "Director": _SANCTIONING,
    "leave_admin": _LEAVE_ADMIN,
}
