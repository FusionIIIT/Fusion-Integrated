"""What the server tells the shell about ELM (ADR-0010)."""

MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Employee Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave_elm.my_leaves",
        "label": "My Leaves",
        "icon": "CalendarBlank",
        "to": "/elm/my-leaves",
        "required_permission": "leave_elm.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "leave_elm.apply",
        "label": "Apply Leave",
        "icon": "ClipboardText",
        "to": "/elm/apply",
        "required_permission": "leave_elm.application.apply",
        "sort_order": 20,
    },
    {
        "code": "leave_elm.substitutions",
        "label": "Substitute Requests",
        "icon": "UserCheck",
        "to": "/elm/substitutions",
        "required_permission": "leave_elm.substitute.respond",
        "sort_order": 30,
    },
    {
        "code": "leave_elm.approvals",
        "label": "Leave Approvals",
        "icon": "Checks",
        "to": "/elm/approvals",
        "required_permission": "leave_elm.application.approve",
        "sort_order": 40,
    },
    {
        "code": "leave_elm.admin",
        "label": "Leave Admin",
        "icon": "Buildings",
        "to": "/elm/admin",
        "required_permission": "leave_elm.admin.manage",
        "sort_order": 50,
    },
    {
        "code": "leave_elm.calendars",
        "label": "Holiday Calendar",
        "icon": "CalendarBlank",
        "to": "/elm/calendars",
        "required_permission": "leave_elm.application.view_self",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("leave_elm.application.view_self", "See one's own leave applications and balances"),
    ("leave_elm.application.apply", "Submit a leave application"),
    ("leave_elm.application.withdraw", "Withdraw a pending leave application"),
    ("leave_elm.application.cancel", "Request cancellation of an approved leave"),
    ("leave_elm.application.extend", "Request extension of an ongoing leave"),
    ("leave_elm.application.resume", "Submit a return to duty resumption report"),
    ("leave_elm.application.view", "View employee leave applications"),
    ("leave_elm.substitute.respond", "Accept or decline nominated substitute responsibilities"),
    ("leave_elm.application.review", "Review and record Unit Head recommendation"),
    ("leave_elm.application.approve", "Approve or reject leave, cancellation, and extension"),
    ("leave_elm.admin.manage", "Manage ELM policy configuration, calendars, and offline records"),
    ("leave_elm.report.view", "View employee leave summary reports"),
]

SYSTEM_PERMISSIONS = []

SCOPE_PERMISSIONS = [
    "leave_elm.application.view",
    "leave_elm.report.view",
]

_EMPLOYEE = [
    "leave_elm.application.view_self",
    "leave_elm.application.apply",
    "leave_elm.application.withdraw",
    "leave_elm.application.cancel",
    "leave_elm.application.extend",
    "leave_elm.application.resume",
    "leave_elm.substitute.respond",
]

_APPROVER = [
    "leave_elm.application.view_self",
    "leave_elm.application.view",
    "leave_elm.application.review",
    "leave_elm.application.approve",
    "leave_elm.report.view",
]

_ADMIN = [
    "leave_elm.application.view_self",
    "leave_elm.application.view",
    "leave_elm.admin.manage",
    "leave_elm.application.review",
    "leave_elm.application.approve",
    "leave_elm.report.view",
]

ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "HOD": [
        *_EMPLOYEE,
        "leave_elm.application.view",
        "leave_elm.application.review",
        "leave_elm.application.approve",
        "leave_elm.report.view",
    ],
    "Leave Approver": _APPROVER,
    "Leave Administrator": _ADMIN,
    "Dean": _APPROVER,
    "Registrar": _APPROVER,
    "Director": [
        *_EMPLOYEE,
        "leave_elm.application.view",
        "leave_elm.application.review",
        "leave_elm.application.approve",
        "leave_elm.report.view",
    ],
}
