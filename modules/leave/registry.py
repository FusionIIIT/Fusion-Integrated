# Leave module registration with the Fusion base platform
MODULE = {
    "code": "leave_elm",
    "label": "Leave Management",
    "icon": "FaCalendarCheck",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS: list[dict] = [
    {
        "code": "leave.applications",
        "label": "My Leave",
        "icon": "FaCalendarAlt",
        "to": "/leave/applications",
        "required_permission": "leave_elm.application.view",
        "sort_order": 10,
    },
    {
        "code": "leave.approvals",
        "label": "Approvals",
        "icon": "FaCheckCircle",
        "to": "/leave/approvals",
        "required_permission": "leave_elm.application.approve",
        "sort_order": 20,
    },
]

PERMISSIONS: list[tuple[str, str]] = [
    ("leave_elm.application.view", "See leave applications and balances"),
    ("leave_elm.application.apply", "Submit a leave application"),
    ("leave_elm.application.approve", "Approve or reject a leave application"),
    ("leave_elm.application.withdraw", "Withdraw a pending leave application"),
    ("leave_elm.application.cancel", "Cancel an approved leave application"),
]

ROLE_GRANTS: dict[str, list[str]] = {
    "Employee": [
        "leave_elm.application.view",
        "leave_elm.application.apply",
        "leave_elm.application.withdraw",
        "leave_elm.application.cancel",
    ],
    "faculty": [
        "leave_elm.application.view",
        "leave_elm.application.apply",
        "leave_elm.application.withdraw",
        "leave_elm.application.cancel",
    ],
    "staff": [
        "leave_elm.application.view",
        "leave_elm.application.apply",
        "leave_elm.application.withdraw",
        "leave_elm.application.cancel",
    ],
    "Leave Approver": [
        "leave_elm.application.view",
        "leave_elm.application.approve",
        "leave_elm.application.cancel",
    ],
    "HOD": [
        "leave_elm.application.view",
        "leave_elm.application.approve",
        "leave_elm.application.cancel",
    ],
}
