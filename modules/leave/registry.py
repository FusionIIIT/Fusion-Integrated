MODULE = {
    "code": "leave_elm",
    "label": "Employee Leave",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "Employee Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.balance",
        "label": "My Leave",
        "icon": "Calendar",
        "to": "/leave",
        "required_permission": "leave_elm.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "leave.tasks",
        "label": "Leave Tasks",
        "icon": "Checklist",
        "to": "/leave/tasks",
        "required_permission": "leave_elm.workflow.review",
        "sort_order": 20,
    },
    {
        "code": "leave.admin",
        "label": "Leave Administration",
        "icon": "Settings",
        "to": "/leave/admin",
        "required_permission": "leave_elm.configuration.manage",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("leave_elm.application.view_self", "View own leave balances and history"),
    ("leave_elm.application.apply", "Apply for leave"),
    ("leave_elm.application.withdraw", "Withdraw pending leave"),
    ("leave_elm.application.cancel", "Request cancellation of approved leave"),
    ("leave_elm.application.extend", "Request extension of ongoing leave"),
    ("leave_elm.application.resume", "Submit resumption of duty"),
    ("leave_elm.workflow.substitute", "Respond to substitute requests"),
    ("leave_elm.workflow.review", "Review assigned leave tasks"),
    ("leave_elm.workflow.sanction", "Make final sanctioning decisions"),
    ("leave_elm.configuration.manage", "Maintain leave configuration"),
    ("leave_elm.records.manage", "Maintain authorized leave records"),
    ("leave_elm.year_end.process", "Process leave year end"),
]

_EMPLOYEE = [p for p, _ in PERMISSIONS[:6]]
ROLE_GRANTS = {
    "Employee": _EMPLOYEE,
    "Leave Approver": ["leave_elm.application.view_self", "leave_elm.workflow.review"],
    "Leave Administrator": [p for p, _ in PERMISSIONS],
    "Unit Head": ["leave_elm.application.view_self", "leave_elm.workflow.review"],
    "Deputy Registrar (Estt.)": ["leave_elm.application.view_self", "leave_elm.workflow.review"],
    "Dean": [
        "leave_elm.application.view_self",
        "leave_elm.workflow.review",
        "leave_elm.workflow.sanction",
    ],
    "Registrar": [
        "leave_elm.application.view_self",
        "leave_elm.workflow.review",
        "leave_elm.workflow.sanction",
    ],
    "Director": [
        "leave_elm.application.view_self",
        "leave_elm.application.apply",
        "leave_elm.workflow.sanction",
    ],
}
