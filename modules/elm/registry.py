
"""Registry metadata for the Employee Leave Management module."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Employee Services",
    "sort_order": 40,
    "status": "planned",
}

NAV_ITEMS = [
    {
        "code": "elm.my_leaves",
        "label": "My Leave Applications",
        "icon": "Calendar",
        "to": "/elm/my-leaves",
        "required_permission": "elm.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "Plus",
        "to": "/elm/apply",
        "required_permission": "elm.application.create",
        "sort_order": 20,
    },
    {
        "code": "elm.approvals",
        "label": "Leave Approvals",
        "icon": "ClipboardCheck",
        "to": "/elm/approvals",
        "required_permission": "elm.application.approve",
        "sort_order": 30,
    },
    {
        "code": "elm.leave_calendar",
        "label": "Leave Calendar",
        "icon": "CalendarDays",
        "to": "/elm/calendar",
        "required_permission": "elm.calendar.view",
        "sort_order": 40,
    },
    {
        "code": "elm.administration",
        "label": "Leave Administration",
        "icon": "Settings",
        "to": "/elm/admin",
        "required_permission": "elm.leave_type.manage",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("elm.application.view_self", "View own leave applications"),
    ("elm.application.create", "Submit leave applications"),
    ("elm.application.withdraw", "Withdraw eligible leave applications"),
    ("elm.application.view", "View leave applications for approval"),
    ("elm.application.approve", "Approve or reject leave applications"),
    ("elm.application.forward", "Forward leave applications"),
    ("elm.application.cancel", "Cancel approved leave"),
    ("elm.application.extend", "Request leave extension"),
    ("elm.application.resume", "Record return from leave"),
    ("elm.calendar.view", "View the leave calendar"),
    ("elm.calendar.manage", "Manage leave calendar entries"),
    ("elm.leave_type.manage", "Manage leave types and entitlements"),
    ("elm.report.view", "View leave reports"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "Employee": [
        "elm.application.view_self",
        "elm.application.create",
        "elm.application.withdraw",
        "elm.application.cancel",
        "elm.application.extend",
        "elm.application.resume",
        "elm.calendar.view",
    ],
    "Leave Approver": [
        "elm.application.view",
        "elm.application.approve",
        "elm.application.forward",
        "elm.calendar.view",
    ],
    "Leave Administrator": [
        "elm.application.view",
        "elm.application.approve",
        "elm.application.forward",
        "elm.application.cancel",
        "elm.application.extend",
        "elm.application.resume",
        "elm.calendar.view",
        "elm.calendar.manage",
        "elm.leave_type.manage",
        "elm.report.view",
    ],
}
