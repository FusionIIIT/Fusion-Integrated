"""ELM module metadata and permission declarations."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/elm",
    "nav_section": "Administration",
    "sort_order": 30,
    "status": "planned",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("elm.leave_application.submit", "Submit a leave application"),
    ("elm.leave_application.withdraw", "Withdraw a leave application"),
    ("elm.substitute_consent.respond", "Respond to a substitute request"),
    ("elm.leave_application.review", "Review leave requests at Unit Head"),
    ("elm.leave_application.route", "Route a higher-sanction request"),
    ("elm.leave_application.finalize", "Record a final sanction decision"),
    ("elm.leave_application.self_sanction", "Director self-sanction"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "faculty": [
        "elm.leave_application.submit",
        "elm.leave_application.withdraw",
        "elm.substitute_consent.respond",
    ],
    "staff": [
        "elm.leave_application.submit",
        "elm.leave_application.withdraw",
        "elm.substitute_consent.respond",
    ],
    "unit_head": ["elm.leave_application.review"],
    "establishment": ["elm.leave_application.route"],
    "deputy_registrar": ["elm.leave_application.route"],
    "dean": ["elm.leave_application.route"],
    "registrar": ["elm.leave_application.route"],
    "director": [
        "elm.leave_application.finalize",
        "elm.leave_application.self_sanction",
    ],
}
