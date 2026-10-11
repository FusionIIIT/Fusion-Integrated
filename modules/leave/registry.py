"""What the server tells the shell about Employee Leave Management (ADR-0010)."""

MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- Employee items --
    {
        "code": "leave.apply",
        "label": "Apply for Leave",
        "icon": "CalendarPlus",
        "to": "/leave/apply",
        "required_permission": "leave.request.create",
        "sort_order": 10,
    },
    {
        "code": "leave.mine",
        "label": "My Leaves",
        "icon": "ClockCounterClockwise",
        "to": "/leave/mine",
        "required_permission": "leave.request.view_self",
        "sort_order": 20,
    },
    {
        "code": "leave.inbox",
        "label": "Action Inbox",
        "icon": "Tray",
        "to": "/leave/inbox",
        "required_permission": "leave.request.view_self",
        "sort_order": 30,
    },

    # -- Approver / Authority items --
    {
        "code": "leave.approvals",
        "label": "Leave Approvals",
        "icon": "CheckSquare",
        "to": "/leave/approvals",
        "required_permission": "leave.request.approve",
        "sort_order": 40,
    },
    {
        "code": "leave.resumptions",
        "label": "Resumption Reviews",
        "icon": "ArrowUUpLeft",
        "to": "/leave/resumptions",
        "required_permission": "leave.request.approve",
        "sort_order": 50,
    },

    # -- Administrator items --
    {
        "code": "leave.calendar",
        "label": "Holiday Calendar",
        "icon": "Calendar",
        "to": "/leave/calendar",
        "required_permission": "leave.type.manage",
        "sort_order": 60,
    },
    {
        "code": "leave.admin_records",
        "label": "Offline & Adjustments",
        "icon": "Notebook",
        "to": "/leave/offline-records",
        "required_permission": "leave.balance.update",
        "sort_order": 70,
    },
    {
        "code": "leave.policy",
        "label": "Policy & Quotas",
        "icon": "Gear",
        "to": "/leave/policy",
        "required_permission": "leave.type.manage",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests, balance and inbox"),
    ("leave.request.create", "Apply for leave, extension, cancellation, resumption"),
    ("leave.request.delete", "Withdraw own pending leave request"),
    ("leave.request.view", "View leave requests within administrative scope"),
    ("leave.request.approve", "Approve, recommend or reject leave requests"),
    ("leave.balance.update", "Adjust leave balances and record offline leave"),
    ("leave.type.manage", "Configure leave policies, calendars and SLA thresholds"),
    ("leave.system.yearend", "Execute year-end balance processing"),
    ("leave.system.sla", "Process SLA threshold reminders and escalations"),
]

SYSTEM_PERMISSIONS = [
    "leave.system.yearend",
    "leave.system.sla",
]

SCOPE_PERMISSIONS = [
    "leave.request.view",
]

_EMPLOYEE = [
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.delete",
]

_APPROVER = [
    *_EMPLOYEE,
    "leave.request.view",
    "leave.request.approve",
]

_ADMIN = [
    *_APPROVER,
    "leave.balance.update",
    "leave.type.manage",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "HOD": _APPROVER,
    "Leave Approver": _APPROVER,
    "Dean": _APPROVER,
    "Dean Academic": _APPROVER,
    "Registrar": _APPROVER,
    "Deputy Registrar (Estt.)": _APPROVER,
    "Director": _APPROVER,
    "hr_officer": _ADMIN,
    "Leave Administrator": _ADMIN,
}
