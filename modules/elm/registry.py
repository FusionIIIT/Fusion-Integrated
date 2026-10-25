
"""Permissions recognised by Employee Leave Management."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Employee Services",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.my_leaves",
        "label": "My Leave Requests",
        "icon": "Calendar",
        "to": "/elm/requests",
        "required_permission": "elm.application.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.approvals",
        "label": "Office Leave Approvals",
        "icon": "ClipboardCheck",
        "to": "/elm/approvals",
        "required_permission": "elm.application.approve",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("elm.application.view_self", "View own leave requests"),
    ("elm.application.apply", "Apply for leave"),
    ("elm.application.approve", "Approve office leave requests"),
    ("elm.application.reject", "Reject office leave requests"),
]

SYSTEM_PERMISSIONS = []

# These permissions are enforced by office-scoped querysets.
SCOPE_PERMISSIONS = [
    "elm.application.approve",
    "elm.application.reject",
]

# These names are provisional. Verify them against IAM designations
# before using this registry to publish grants.
_ROLE_EMPLOYEE = [
    "elm.application.view_self",
    "elm.application.apply",
]

_ROLE_OFFICE_APPROVER = [
    "elm.application.view_self",
    "elm.application.approve",
    "elm.application.reject",
]

ROLE_GRANTS = {
    "student": _ROLE_EMPLOYEE,
    "employee": _ROLE_EMPLOYEE,
    "office_approver": _ROLE_OFFICE_APPROVER,
}
