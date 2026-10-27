"""Fusion role and navigation manifest for the ELM laboratory pilot."""

MODULE = {
    "code": "leave_elm",
    "label": "Employee Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 25,
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
        "code": "leave.approvals",
        "label": "Approvals",
        "icon": "UserCheck",
        "to": "/leave/approvals",
        "required_permission": "leave_elm.application.approve",
        "sort_order": 40,
    },
    {
        "code": "leave.admin",
        "label": "Leave Admin",
        "icon": "Gear",
        "to": "/leave/admin",
        "required_permission": "leave_elm.policy.manage",
        "sort_order": 50,
    },
]
PERMISSIONS = [
    ("leave_elm.application.view", "View own leave applications"),
    ("leave_elm.application.apply", "Apply for or withdraw leave"),
    ("leave_elm.application.approve", "Review assigned leave applications"),
    ("leave_elm.balance.view", "View own leave balances"),
    ("leave_elm.policy.manage", "Configure ELM employee profiles and balances"),
]
SYSTEM_PERMISSIONS = []
ROLE_GRANTS = {
    "Employee": [
        "leave_elm.application.view",
        "leave_elm.application.apply",
        "leave_elm.balance.view",
    ],
    "Leave Approver": [
        "leave_elm.application.view",
        "leave_elm.application.approve",
        "leave_elm.balance.view",
    ],
    "Leave Admin": [
        "leave_elm.application.view",
        "leave_elm.balance.view",
        "leave_elm.policy.manage",
    ],
}
