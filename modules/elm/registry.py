"""Server-driven navigation and IAM permission registry for ELM.

Role keys must match the designation values configured in the IAM directory.
The role names below mirror the ELM actor/authority registry and must be
reconciled with live globals_designation names before publishing to production.
"""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "FaCalendarAlt",
    "base_path": "/elm",
    "nav_section": "Human Resources",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.my_requests",
        "label": "My Leave Requests",
        "icon": "FaCalendarAlt",
        "to": "/elm/my-requests",
        "required_permission": "elm.leave.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "FaCalendarAlt",
        "to": "/elm/apply",
        "required_permission": "elm.leave.create",
        "sort_order": 20,
    },
    {
        "code": "elm.review",
        "label": "Leave Review Queue",
        "icon": "FaClipboardCheck",
        "to": "/elm/review",
        "required_permission": "elm.leave.review",
        "sort_order": 30,
    },
    {
        "code": "elm.sanction",
        "label": "Leave Sanction Queue",
        "icon": "FaClipboardCheck",
        "to": "/elm/review",
        "required_permission": "elm.leave.sanction",
        "sort_order": 40,
    },
    {
        "code": "elm.substitute",
        "label": "Substitute Responses",
        "icon": "FaClipboardCheck",
        "to": "/elm/review",
        "required_permission": "elm.leave.substitute",
        "sort_order": 50,
    },
    {
        "code": "elm.admin",
        "label": "ELM Administration",
        "icon": "FaCog",
        "to": "/elm/admin",
        "required_permission": "elm.leave.manage",
        "sort_order": 90,
    },
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave requests, balance, and history"),
    ("elm.leave.view_all", "View leave requests assigned for processing or administration"),
    ("elm.leave.create", "Create and submit leave requests"),
    ("elm.leave.substitute", "Respond to substitute/responsibility requests"),
    ("elm.leave.review", "Review and route leave requests as Unit Head or Establishment"),
    ("elm.leave.sanction", "Make final leave sanction and resumption decisions"),
    ("elm.leave.manage", "Maintain ELM policy, calendar, hierarchy, and authorized records"),
    ("elm.leave.export", "Export an accessible leave application"),
]

SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []

_EMPLOYEE = ["elm.leave.view_self", "elm.leave.create", "elm.leave.substitute", "elm.leave.export"]
_PROCESSOR = ["elm.leave.view_all", "elm.leave.review"]
_SANCTIONER = ["elm.leave.view_all", "elm.leave.sanction"]
_ADMIN = ["elm.leave.view_all", "elm.leave.manage", "elm.leave.export"]

ROLE_GRANTS = {
    # Verify these exact designation keys against IAM before seeding deployment.
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "Unit Head": [
        *_PROCESSOR,
        "elm.leave.view_self",
        "elm.leave.create",
        "elm.leave.substitute",
        "elm.leave.export",
    ],
    "Deputy Registrar (Estt.)": [*_PROCESSOR, *_SANCTIONER],
    "Dean": _SANCTIONER,
    "Registrar": _SANCTIONER,
    "Director": [
        *_SANCTIONER,
        "elm.leave.view_self",
        "elm.leave.create",
        "elm.leave.substitute",
        "elm.leave.export",
    ],
    "Leave Administrator": _ADMIN,
}
