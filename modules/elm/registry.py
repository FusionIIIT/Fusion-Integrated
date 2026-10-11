"""Server-side navigation and the IAM permission catalogue for ELM."""
MODULE = {
    "code": "elm", "label": "Employee Leave Management", "icon": "FaCalendarAlt",
    "base_path": "/elm", "nav_section": "Human Resources", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "elm.my-leave", "label": "My Leave", "icon": "FaUmbrellaBeach",
     "to": "/elm", "required_permission": "elm.leave.view_self",
     "sort_order": 10},
    {"code": "elm.inbox", "label": "Review Queue", "icon": "FaTasks",
     "to": "/elm/inbox", "required_permission": "elm.leave.review",
     "sort_order": 20},
    {"code": "elm.accounts", "label": "Leave Accounts", "icon": "FaBalanceScale",
     "to": "/elm/accounts", "required_permission": "elm.leave.view_all",
     "sort_order": 30},
    {"code": "elm.configuration", "label": "ELM Configuration",
     "icon": "FaCog", "to": "/elm/configuration",
     "required_permission": "elm.config.manage", "sort_order": 40},
]

PERMISSIONS = [
    ("elm.leave.view_self", "View own leave balances and history"),
    ("elm.leave.apply", "Apply for leave and related actions"),
    ("elm.leave.withdraw", "Withdraw a pending leave request"),
    ("elm.leave.substitute_respond", "Respond to substitute requests"),
    ("elm.leave.review", "Review leave requests as Unit Head"),
    ("elm.leave.process", "Process and route higher-sanction requests"),
    ("elm.leave.sanction", "Make final leave sanction decisions"),
    ("elm.leave.view_all", "View employee leave accounts and requests"),
    ("elm.config.manage", "Maintain leave policy and routing"),
    ("elm.calendar.manage", "Maintain and publish leave calendars"),
    ("elm.record.manage", "Maintain authorized leave records"),
    ("elm.leave.year_end", "Run year-end leave-account processing"),
]

SYSTEM_PERMISSIONS = ["elm.leave.year_end"]

ROLE_GRANTS = {
    "Employee": [
        "elm.leave.view_self", "elm.leave.apply", "elm.leave.withdraw",
        "elm.leave.substitute_respond",
    ],
    "Faculty": [
        "elm.leave.view_self", "elm.leave.apply", "elm.leave.withdraw",
        "elm.leave.substitute_respond",
    ],
    "Staff": [
        "elm.leave.view_self", "elm.leave.apply", "elm.leave.withdraw",
        "elm.leave.substitute_respond",
    ],
    "Unit Head": [
        "elm.leave.view_self", "elm.leave.apply", "elm.leave.withdraw",
        "elm.leave.substitute_respond", "elm.leave.review",
    ],
    "Deputy Registrar (Estt.)": [
        "elm.leave.view_self", "elm.leave.apply", "elm.leave.withdraw",
        "elm.leave.substitute_respond", "elm.leave.process", "elm.leave.sanction",
        "elm.leave.view_all",
    ],
    "Establishment": [
        "elm.leave.view_self", "elm.leave.apply", "elm.leave.withdraw",
        "elm.leave.substitute_respond", "elm.leave.process", "elm.leave.view_all",
    ],
    "Dean": [
        "elm.leave.view_self", "elm.leave.apply", "elm.leave.withdraw",
        "elm.leave.substitute_respond", "elm.leave.sanction", "elm.leave.view_all",
    ],
    "Registrar": [
        "elm.leave.view_self", "elm.leave.apply", "elm.leave.withdraw",
        "elm.leave.substitute_respond", "elm.leave.sanction", "elm.leave.view_all",
    ],
    "Director": [
        "elm.leave.view_self", "elm.leave.apply", "elm.leave.withdraw",
        "elm.leave.substitute_respond", "elm.leave.sanction", "elm.leave.view_all",
    ],
    "ELM Administrator": [
        "elm.leave.view_self", "elm.leave.view_all", "elm.config.manage",
        "elm.calendar.manage", "elm.record.manage",
    ],
}
