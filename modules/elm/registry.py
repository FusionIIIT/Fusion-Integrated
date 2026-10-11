"""Server-driven manifest for Employee Leave Management."""
MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Administration",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.leave_requests",
        "label": "Leave Requests",
        "icon": "Calendar",
        "to": "/elm/leave-requests",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.leave_approvals",
        "label": "Leave Approvals",
        "icon": "Checks",
        "to": "/elm/approvals",
        "required_permission": "elm.leave.view_all",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave requests"),
    ("elm.leave.view_all", "View all employee leave requests"),
    ("elm.leave.submit", "Submit a leave request"),
    ("elm.leave.approve", "Approve pending leave requests"),
    ("elm.leave.reject", "Reject pending leave requests"),
    ("elm.leave.cancel", "Cancel leave requests"),
]

# Deliberately no ROLE_GRANTS: the archive contains no ELM BR/UC/workflow
# specification or approved IAM role mapping. Grant these permissions only
# after the assignment owner confirms the real role names and responsibilities.
ROLE_GRANTS = {}
SYSTEM_PERMISSIONS = []
