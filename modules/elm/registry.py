MODULE = {
    "code": "leave",
    "label": "Employee Leave Management",
    "icon": "Clock",
    "base_path": "/leave",
    "nav_section": "HR & Leave",
    "sort_order": 5,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.submit",
        "label": "Request Leave",
        "icon": "Plus",
        "to": "/leave/submit",
        "required_permission": "leave.request.create",
        "sort_order": 1,
    },
    {
        "code": "leave.my_requests",
        "label": "My Leave Requests",
        "icon": "Clock",
        "to": "/leave/my",
        "required_permission": "leave.request.view_self",
        "sort_order": 5,
    },
    {
        "code": "leave.balances",
        "label": "Leave Balances",
        "icon": "Clock",
        "to": "/leave/balances",
        "required_permission": "leave.request.view_self",
        "sort_order": 7,
    },
    {
        "code": "leave.substitutions",
        "label": "Substitute Requests",
        "icon": "CheckCircle",
        "to": "/leave/substitutions",
        "required_permission": "leave.substitute.respond",
        "sort_order": 8,
    },
    {
        "code": "leave.approvals",
        "label": "Leave Approvals",
        "icon": "CheckCircle",
        "to": "/leave/approvals",
        "required_permission": "leave.request.approve",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests and balance"),
    ("leave.request.create", "Apply for leave"),
    ("leave.request.delete", "Withdraw own pending leave request"),
    ("leave.substitute.respond", "Accept or decline a nominated substitute task"),
    ("leave.request.approve", "Approve or reject a leave request"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave.request.view_self",
    "leave.request.create",
    "leave.request.delete",
    "leave.substitute.respond",
]

_APPROVER = _EMPLOYEE + ["leave.request.approve"]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": _APPROVER,
    "establishment_officer": _APPROVER,
    "deputy_registrar_estt": _APPROVER,
    "dean_academic": _APPROVER,
    "registrar": _APPROVER,
    "director": _APPROVER,
    "hr_officer": _APPROVER,
}
