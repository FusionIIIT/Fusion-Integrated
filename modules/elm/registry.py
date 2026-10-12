"""Registry for the Employee Leave Management module."""

MODULE = {
    "code": "leave_elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "HR",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.dashboard",
        "label": "My Leave",
        "icon": "CalendarBlank",
        "to": "/leave",
        "required_permission": "leave_elm.application.view",
        "sort_order": 10,
    },
    {
        "code": "leave.balance",
        "label": "Leave Balance",
        "icon": "ChartBar",
        "to": "/leave/balance",
        "required_permission": "leave_elm.balance.view",
        "sort_order": 20,
    },
    {
        "code": "leave.approvals",
        "label": "Approvals",
        "icon": "CheckCircle",
        "to": "/leave/approvals",
        "required_permission": "leave_elm.application.approve",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("leave_elm.application.view", "View leave applications"),
    ("leave_elm.application.apply", "Submit a leave application"),
    ("leave_elm.application.approve", "Approve or reject leave applications"),
    ("leave_elm.application.cancel", "Cancel a leave application"),
    ("leave_elm.balance.view", "View leave balances"),
    ("leave_elm.report.view", "View leave reports"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave_elm.application.view",
    "leave_elm.application.apply",
    "leave_elm.application.cancel",
    "leave_elm.balance.view",
]

_APPROVER = [
    *_EMPLOYEE,
    "leave_elm.application.approve",
    "leave_elm.report.view",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "employee": _EMPLOYEE,
    "hod": _APPROVER,
    "dean": _APPROVER,
    "registrar": _APPROVER,
}


def readiness():
    return []
