"""Server-side registry declaration for the Leave module (ADR-0010)."""

MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "FaCalendarCheck",
    "base_path": "/leave",
    "nav_section": "Administration",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.apply",
        "label": "Apply Leave",
        "icon": "FaPlusCircle",
        "to": "/leave/apply",
        "required_permission": "leave.request.create",
        "sort_order": 10,
    },
    {
        "code": "leave.mine",
        "label": "My Requests",
        "icon": "FaListAlt",
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
        "code": "leave.substitute",
        "label": "Substitute Tasks",
        "icon": "FaUserCheck",
        "to": "/leave/substitute",
        "required_permission": "leave.request.substitute",
        "sort_order": 40,
    },
    {
        "code": "leave.approvals",
        "label": "Leave Approvals",
        "icon": "FaTasks",
        "to": "/leave/approvals",
        "required_permission": "leave.request.approve",
        "sort_order": 50,
    },
    {
        "code": "leave.calendar",
        "label": "Holiday Calendar",
        "icon": "FaCalendarAlt",
        "to": "/leave/calendar",
        "required_permission": "leave.calendar.view",
        "sort_order": 60,
    },
    {
        "code": "leave.admin",
        "label": "Leave Admin",
        "icon": "FaCogs",
        "to": "/leave/admin",
        "required_permission": "leave.type.manage",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("leave.request.create", "Apply for leave"),
    ("leave.request.view_self", "View own leave requests and balance"),
    ("leave.request.delete", "Withdraw or cancel own leave request"),
    ("leave.request.substitute", "Respond to substitute responsibility requests"),
    ("leave.request.view", "View leave requests within scope"),
    ("leave.request.approve", "Review and approve leave requests"),
    ("leave.balance.update", "Adjust or seed employee leave balances"),
    ("leave.type.manage", "Configure leave policies, hierarchies and calendars"),
    ("leave.calendar.view", "View holiday and vacation calendar"),
    ("leave.offline.record", "Record already-sanctioned offline leave"),
]

SYSTEM_PERMISSIONS = [
    "leave.yearend.process",
    "leave.sla.process",
]

_EMPLOYEE = [
    "leave.request.create",
    "leave.request.view_self",
    "leave.request.delete",
    "leave.request.substitute",
    "leave.calendar.view",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "leave.request.view",
    "leave.request.approve",
]

_ESTABLISHMENT = [
    *_UNIT_HEAD,
    "leave.offline.record",
    "leave.balance.update",
]

_ADMIN = [
    *_ESTABLISHMENT,
    "leave.type.manage",
]

ROLE_GRANTS = {
    "student": [],
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "HOD": _UNIT_HEAD,
    "Dean Academic": _UNIT_HEAD,
    "Registrar": _UNIT_HEAD,
    "Director": _UNIT_HEAD,
    "dr_establishment": _ESTABLISHMENT,
    "establishment_officer": _ESTABLISHMENT,
    "hr_officer": _ESTABLISHMENT,
    "admin": _ADMIN,
    "leave_admin": _ADMIN,
}
