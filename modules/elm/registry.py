"""Fusion module registration for Employee Leave Management."""

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
        "code": "elm.leave",
        "label": "Leave Management",
        "icon": "Calendar",
        "to": "/elm",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave applications and balances"),
    ("elm.leave.apply", "Apply for leave"),
    ("elm.leave.withdraw_self", "Withdraw own eligible leave applications"),
    ("elm.leave.substitute_respond", "Accept or decline substitute requests"),
]

SYSTEM_PERMISSIONS = [
    # Add narrowly scoped permissions for scheduled processing only
    # when the corresponding workflows have been implemented.
]

# Exact designation names must be verified against the ELM specifications
# and this deployment's IAM designations before granting permissions.
# Built-in employee kinds documented by Fusion.
# Substitute-response access is further restricted to the nominated substitute.
ROLE_GRANTS = {
    "faculty": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.leave.withdraw_self",
        "elm.leave.substitute_respond",
    ],
    "staff": [
        "elm.leave.view_self",
        "elm.leave.apply",
        "elm.leave.withdraw_self",
        "elm.leave.substitute_respond",
    ],
}
