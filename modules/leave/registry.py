"""Employee Leave Management (ELM) module manifest.

This is the minimum production-ready module skeleton for the ELM workstream:
permission metadata, navigation and role grants are declared here so the IAM can
seed them and the sidebar can be rendered server-side.
"""

MODULE = {
    "code": "leave",
    "label": "Leave",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "People",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.dashboard",
        "label": "Leave Dashboard",
        "icon": "CalendarEvent",
        "to": "/leave",
        "required_permission": "leave.request.view_self",
        "sort_order": 10,
    },
    {
        "code": "leave.requests",
        "label": "My Leave Requests",
        "icon": "List",
        "to": "/leave/requests",
        "required_permission": "leave.request.view_self",
        "sort_order": 20,
    },
    {
        "code": "leave.review",
        "label": "Review Requests",
        "icon": "ClipboardCheck",
        "to": "/leave/review",
        "required_permission": "leave.request.approve",
        "sort_order": 30,
    },
    {
        "code": "leave.balances",
        "label": "Leave Balances",
        "icon": "Wallet",
        "to": "/leave/balances",
        "required_permission": "leave.balance.update",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests and balance"),
    ("leave.request.create", "Apply for leave"),
    ("leave.request.delete", "Cancel own pending request"),
    ("leave.request.view", "View leave requests, within scope"),
    ("leave.request.approve", "Approve or reject a leave request"),
    ("leave.balance.update", "Adjust a leave balance"),
    ("leave.type.manage", "Configure leave types and entitlement rules"),
]

SYSTEM_PERMISSIONS = []

_FACULTY = [
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.delete",
]

_STAFF = [
    *_FACULTY,
]

_HR_OFFICER = [
    "leave.request.view",
    "leave.request.approve",
    "leave.balance.update",
    "leave.type.manage",
]

ROLE_GRANTS = {
    "faculty": _FACULTY,
    "staff": _STAFF,
    "hr_officer": _HR_OFFICER,
}
