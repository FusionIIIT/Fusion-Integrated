
PERMISSIONS = [
    ("leave_elm.application.view", "View applications"),
    ("leave_elm.application.apply", "Apply for leave"),
    ("leave_elm.application.approve", "Approve leave"),
    ("leave_elm.application.manage", "Manage leaves"),
]

ROLE_GRANTS = {
    "Employee": [
        "leave_elm.application.view",
        "leave_elm.application.apply",
    ],
    "Leave Approver": [
        "leave_elm.application.view",
        "leave_elm.application.approve",
    ],
    "Unit Head": [
        "leave_elm.application.view",
        "leave_elm.application.approve",
        "leave_elm.application.manage",
    ],
    "Leave Administrator": [
        "leave_elm.application.view",
        "leave_elm.application.apply",
        "leave_elm.application.approve",
        "leave_elm.application.manage",
    ],
}

NAV_ITEMS = [
    {"title": "Leave Management", "url": "/leave_elm/", "required_permission": "leave_elm.application.view"},
]
