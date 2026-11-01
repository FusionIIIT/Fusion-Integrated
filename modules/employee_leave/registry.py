"""ELM navigation and the permission vocabulary consumed by Fusion IAM."""

MODULE = {
    "code": "employee_leave",
    "label": "Employee Leave",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "People",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "employee_leave.my_requests",
        "label": "My Leave",
        "icon": "Calendar",
        "to": "/leave/mine",
        "required_permission": "employee_leave.request.create",
        "sort_order": 10,
    },
    {
        "code": "employee_leave.balances",
        "label": "Balances & History",
        "icon": "Wallet",
        "to": "/leave/balances",
        "required_permission": "employee_leave.balance.view_self",
        "sort_order": 20,
    },
    {
        "code": "employee_leave.tasks",
        "label": "Approval Queue",
        "icon": "ClipboardCheck",
        "to": "/leave/tasks",
        "required_permission": "employee_leave.request.work_queue",
        "sort_order": 30,
    },
    {
        "code": "employee_leave.admin",
        "label": "Leave Administration",
        "icon": "Settings",
        "to": "/leave/admin",
        "required_permission": "employee_leave.configuration.manage",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("employee_leave.request.create", "Submit and view own leave requests"),
    ("employee_leave.request.respond_substitute", "Respond to an assigned substitute task"),
    ("employee_leave.request.work_queue", "Open the role-scoped leave task queue"),
    ("employee_leave.request.view_all", "View all leave requests"),
    ("employee_leave.request.review_unit", "Review requests as Unit Head"),
    ("employee_leave.request.route", "Verify and route higher-sanction requests"),
    ("employee_leave.request.sanction", "Make final leave decisions"),
    ("employee_leave.balance.view_self", "View own leave balances and history"),
    ("employee_leave.balance.manage", "Maintain employee leave balances"),
    ("employee_leave.record.offline", "Record an already-sanctioned offline leave"),
    ("employee_leave.configuration.manage", "Manage leave policy and calendars"),
]

ROLE_GRANTS = {
    "employee": [
        "employee_leave.request.create",
        "employee_leave.balance.view_self",
        "employee_leave.request.respond_substitute",
        "employee_leave.request.work_queue",
    ],
    "unit_head": [
        "employee_leave.request.review_unit",
        "employee_leave.request.work_queue",
        "employee_leave.request.respond_substitute",
    ],
    "establishment": ["employee_leave.request.route", "employee_leave.request.work_queue"],
    "sanctioning_authority": [
        "employee_leave.request.sanction",
        "employee_leave.request.work_queue",
    ],
    "leave_administrator": [
        "employee_leave.request.view_all",
        "employee_leave.balance.manage",
        "employee_leave.record.offline",
        "employee_leave.configuration.manage",
    ],
}
