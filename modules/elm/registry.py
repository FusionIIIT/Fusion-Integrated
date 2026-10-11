MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave_elm.apply",
        "label": "Apply Leave",
        "icon": "PencilSimple",
        "to": "/leave/apply",
        "required_permission": "leave_elm.application.apply",
        "sort_order": 10,
    },
    {
        "code": "leave_elm.mine",
        "label": "My Leaves",
        "icon": "ListChecks",
        "to": "/leave/mine",
        "required_permission": "leave_elm.application.view",
        "sort_order": 20,
    },
    {
        "code": "leave_elm.balance",
        "label": "Leave Balance",
        "icon": "Scales",
        "to": "/leave/balance",
        "required_permission": "leave_elm.balance.view",
        "sort_order": 30,
    },
    {
        "code": "leave_elm.approvals",
        "label": "Leave Approvals",
        "icon": "UserCheck",
        "to": "/leave/approvals",
        "required_permission": "leave_elm.application.approve",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("leave_elm.application.view", "See leave applications"),
    ("leave_elm.application.apply", "Submit a leave application"),
    ("leave_elm.application.approve", "Approve or reject a leave application"),
    ("leave_elm.balance.view", "View leave balances"),
]

SYSTEM_PERMISSIONS: list[str] = []

_EMPLOYEE = [
    "leave_elm.application.view",
    "leave_elm.application.apply",
    "leave_elm.balance.view",
]

_APPROVER = [
    "leave_elm.application.view",
    "leave_elm.application.approve",
    "leave_elm.balance.view",
]

ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Leave Approver": _APPROVER,
}
