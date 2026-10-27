"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

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
    # -- Employee-facing actions -------------------------------------------
    {
        "code": "leave.apply",
        "label": "Apply for Leave",
        "icon": "PlusCircle",
        "to": "/leave/apply",
        "required_permission": "leave.application.apply",
        "sort_order": 5,
    },
    {
        "code": "leave.mine",
        "label": "My Leaves",
        "icon": "ListChecks",
        "to": "/leave/mine",
        "required_permission": "leave.application.view_own",
        "sort_order": 10,
    },
    {
        "code": "leave.substitute",
        "label": "Substitute Requests",
        "icon": "Users",
        "to": "/leave/substitute",
        "required_permission": "leave.substitute.respond",
        "sort_order": 15,
    },
    # -- Unit Head / Sanctioning Authority actions ------------------------
    {
        "code": "leave.approvals",
        "label": "Leave Approvals",
        "icon": "CheckCircle",
        "to": "/leave/approvals",
        "required_permission": "leave.application.review",
        "sort_order": 20,
    },
    {
        "code": "leave.admin",
        "label": "Reporting Lines",
        "icon": "Gear",
        "to": "/leave/admin",
        "required_permission": "leave.admin.manage",
        "sort_order": 30,
    },
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("leave.application.apply", "Apply for leave and withdraw or cancel one's own requests"),
    ("leave.application.view_own", "See one's own requests and balances"),
    ("leave.substitute.respond", "Accept or decline being nominated as a substitute"),
    ("leave.application.review", "Decide requests assigned to oneself at the Unit Head stage"),
    ("leave.application.verify", "Verify requests at the Establishment stage"),
    (
        "leave.application.sanction",
        "Sanction or refuse requests at the Sanctioning Authority stage",
    ),
    ("leave.admin.manage", "Maintain reporting lines"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

# Role-based permission grants based on Appendix A actors.
# Key: Actor name (as used in the registry/role mapping), Value: List of permission codes.
ROLE_GRANTS = {
    "Employee": [
        "leave.application.apply",
        "leave.application.view_own",
        "leave.substitute.respond",
    ],
    "Unit Head": [
        "leave.application.review",
    ],
    "Deputy Registrar (Estt.)": [
        "leave.application.review",
        "leave.application.verify",
    ],
    "Dean": [
        "leave.application.review",
        "leave.application.sanction",
    ],
    "Registrar": [
        "leave.application.review",
        "leave.application.sanction",
    ],
    "Director": [
        "leave.application.review",
        "leave.application.sanction",
    ],
    "Leave Administrator": [
        "leave.admin.manage",
    ],
}
