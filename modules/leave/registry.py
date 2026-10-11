"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "CalendarAlt",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 5,
    "status": "active",
}

NAV_ITEMS = [
    # -- Employee-facing actions -------------------------------------------
    {"code": "leave.apply", "label": "Apply for Leave",
     "icon": "PlusCircle",
     "to": "/leave/apply",
     "required_permission": "leave.application.create",
     "sort_order": 5},
    {"code": "leave.mine", "label": "My Leave",
     "icon": "UserCheck",
     "to": "/leave/mine",
     "required_permission": "leave.balance.view_self",
     "sort_order": 10},
    {"code": "leave.substitute", "label": "Nominated Substitute",
     "icon": "Users",
     "to": "/leave/substitute",
     "required_permission": "leave.application.view_self",
     "sort_order": 15},

    # -- Unit Head / Sanctioning Authority actions ------------------------
    {"code": "leave.approvals", "label": "Leave Approvals",
     "icon": "CheckCircle",
     "to": "/leave/approvals",
     "required_permission": "leave.application.review",
     "sort_order": 20},

    # -- Administrative actions --------------------------------------------
    {"code": "leave.admin", "label": "Leave Administration",
     "icon": "Cog",
     "to": "/leave/admin",
     "required_permission": "leave.admin.manage",
     "sort_order": 30},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave.application.create", "Create a leave application"),
    ("leave.application.view", "View all applications"),
    ("leave.application.view_self", "View one's own applications"),
    ("leave.application.review", "Review and recommend applications"),
    ("leave.application.approve", "Approve or reject applications"),
    ("leave.balance.view", "View leave balances"),
    ("leave.balance.view_self", "View one's own leave balance"),
    ("leave.admin.manage", "Manage leave records and policies"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "leave.application.auto_withdraw",
    "leave.balance.calculate",
]

# Role-based permission grants based on Appendix A actors.
# Key: Actor name (as used in the registry/role mapping), Value: List of permission codes.
ROLE_GRANTS = {
    "Employee": [
        "leave.application.create",
        "leave.application.view_self",
        "leave.balance.view_self",
    ],
    "Unit Head": [
        "leave.application.view",
        "leave.application.review",
        "leave.application.approve",
        "leave.balance.view",
    ],
    "Deputy Registrar (Estt.)": [
        "leave.application.view",
        "leave.application.review",
        "leave.application.approve",
        "leave.admin.manage",
    ],
    "Dean": [
        "leave.application.view",
        "leave.application.review",
        "leave.application.approve",
        "leave.balance.view",
    ],
    "Registrar": [
        "leave.application.view",
        "leave.application.review",
        "leave.application.approve",
        "leave.balance.view",
    ],
    "Director": [
        "leave.application.view",
        "leave.application.review",
        "leave.application.approve",
        "leave.admin.manage",
    ],
    "Leave Administrator": [
        "leave.application.view",
        "leave.application.review",
        "leave.application.approve",
        "leave.balance.view",
        "leave.admin.manage",
    ],
}
