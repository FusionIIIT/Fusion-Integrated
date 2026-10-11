"""Module registry for Employee Leave Management (ELM)."""

MODULE = {
    "code": "leave_elm",
    "label": "Employee Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Administration",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave_elm.dashboard",
        "label": "Leave Dashboard",
        "icon": "ClipboardText",
        "to": "/elm/dashboard",
        "required_permission": "leave_elm.application.view",
        "sort_order": 10,
    },
    {
        "code": "leave_elm.apply",
        "label": "Apply for Leave",
        "icon": "Checks",
        "to": "/elm/apply",
        "required_permission": "leave_elm.application.apply",
        "sort_order": 20,
    },
    {
        "code": "leave_elm.approvals",
        "label": "Leave Approvals",
        "icon": "UserCheck",
        "to": "/elm/approvals",
        "required_permission": "leave_elm.application.approve",
        "sort_order": 30,
    },
    {
        "code": "leave_elm.calendar",
        "label": "Holiday Calendar",
        "icon": "CalendarBlank",
        "to": "/elm/calendar",
        "required_permission": "leave_elm.calendar.view",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("leave_elm.application.view", "See leave applications"),
    ("leave_elm.application.apply", "Submit a leave application"),
    ("leave_elm.application.withdraw", "Withdraw a pending leave application"),
    ("leave_elm.application.approve", "Approve or reject a leave application"),
    ("leave_elm.substitute.respond", "Respond to a substitute request"),
    ("leave_elm.balance.view", "View leave balances"),
    ("leave_elm.calendar.view", "View the holiday calendar"),
]

SYSTEM_PERMISSIONS: list[str] = []

_EMPLOYEE = [
    "leave_elm.application.view",
    "leave_elm.application.apply",
    "leave_elm.application.withdraw",
    "leave_elm.substitute.respond",
    "leave_elm.balance.view",
    "leave_elm.calendar.view",
]

_APPROVER = [
    "leave_elm.application.view",
    "leave_elm.application.approve",
    "leave_elm.balance.view",
    "leave_elm.calendar.view",
]

_ADMIN = [code for code, _ in PERMISSIONS]

ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Leave Approver": _APPROVER,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": _APPROVER,
    "establishment": _APPROVER,
    "acadadmin": _ADMIN,
}
