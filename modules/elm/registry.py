"""Fusion module registration for Employee Leave Management."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "Campus",
    "sort_order": 300,
    "status": "planned",
}

# Keep navigation empty until the frontend routes are implemented.
NAV_ITEMS = []

PERMISSIONS = [
    ("elm.leave.apply", "Apply for leave"),
    ("elm.leave.withdraw", "Withdraw one's own eligible leave request"),
    ("elm.leave.approve", "Approve or reject leave requests"),
]

SYSTEM_PERMISSIONS = []

# Basic actor kinds documented by the Fusion architecture.
# Approval grants remain unresolved until institutional designations
# are confirmed against the ELM actor inventory.
ROLE_GRANTS = {
    "faculty": [
        "elm.leave.apply",
        "elm.leave.withdraw",
    ],
    "staff": [
        "elm.leave.apply",
        "elm.leave.withdraw",
    ],
}
