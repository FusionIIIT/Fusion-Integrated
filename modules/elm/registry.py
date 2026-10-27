"""Module registry for Employee Leave Management (ELM).

Defines navigation items, module metadata, permission catalogue, and role grants
conforming to Fusion ERP architectural standards (ADR-0010).
"""

MODULE = {
    "code": "elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "HR & Admin",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.mine",
        "label": "My Leaves",
        "icon": "CalendarBlank",
        "to": "/elm/mine",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "CalendarPlus",
        "to": "/elm/apply",
        "required_permission": "elm.leave.apply",
        "sort_order": 20,
    },
    {
        "code": "elm.substitute",
        "label": "Substitute Requests",
        "icon": "UserCheck",
        "to": "/elm/substitute",
        "required_permission": "elm.substitute.respond",
        "sort_order": 30,
    },
    {
        "code": "elm.approvals",
        "label": "Leave Approvals",
        "icon": "ClipboardText",
        "to": "/elm/approvals",
        "required_permission": "elm.leave.approve",
        "sort_order": 40,
    },
    {
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "ChartBar",
        "to": "/elm/balances",
        "required_permission": "elm.balance.view",
        "sort_order": 50,
    },
    {
        "code": "elm.admin",
        "label": "Leave Admin",
        "icon": "Gear",
        "to": "/elm/admin",
        "required_permission": "elm.admin.manage",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave applications and balances"),
    ("elm.leave.apply", "Submit a leave application, withdrawal, or cancellation"),
    ("elm.substitute.respond", "Accept or decline a substitute assignment"),
    ("elm.leave.approve", "Review, recommend, or sanction leave requests"),
    ("elm.balance.view", "View employee leave balances"),
    ("elm.admin.manage", "Maintain leave policies, calendars, and offline records"),
]

SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []

ROLE_GRANTS = {
    "faculty": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.substitute.respond",
        "elm.balance.view",
    ],
    "staff": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.substitute.respond",
        "elm.balance.view",
    ],
    "hod": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.substitute.respond",
        "elm.leave.approve",
        "elm.balance.view",
    ],
    "dean": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.substitute.respond",
        "elm.leave.approve",
        "elm.balance.view",
    ],
    "director": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.substitute.respond",
        "elm.leave.approve",
        "elm.balance.view",
    ],
    "registrar": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.substitute.respond",
        "elm.leave.approve",
        "elm.balance.view",
    ],
    "deputy_registrar_estt": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.substitute.respond",
        "elm.leave.approve",
        "elm.balance.view",
    ],
    "leave_admin": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.substitute.respond",
        "elm.leave.approve",
        "elm.balance.view",
        "elm.admin.manage",
    ],
    "admin": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.substitute.respond",
        "elm.leave.approve",
        "elm.balance.view",
        "elm.admin.manage",
    ],
}
