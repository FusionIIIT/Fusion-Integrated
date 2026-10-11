MODULE = {
    "code": "leave",
    "label": "Employee Leave Management",
    "icon": "Clock",
    "base_path": "/leave",
    "nav_section": "HR & Leave",
    "sort_order": 5,
    "status": "planned",
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
    ("leave.request.approve", "Approve or reject a leave request"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "leave.request.view_self",
    "leave.request.create",
]

_HR_OFFICER = [
    "leave.request.approve",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "hr_officer": _HR_OFFICER,
}
