"""ELM permission catalogue and designation grants.

Designation names must match the names configured in Fusion IAM.

These grants establish permission to attempt an action; they do not
establish authority over a particular leave application.
"""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Administration",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = []

PERMISSIONS = [
    (
        "elm.leave_application.create",
        "Submit a leave application",
    ),
    (
        "elm.leave_application.decide",
        "Approve or reject an assigned leave application",
    ),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "faculty": ["elm.leave_application.create"],
    "staff": ["elm.leave_application.create"],
    "ELM Final Sanction Authority": [
        "elm.leave_application.decide",
    ],
}
