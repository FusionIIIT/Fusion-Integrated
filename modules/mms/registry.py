"""MMS permissions and server-filtered navigation metadata."""

MODULE = {
    "code": "mess_management", "label": "Mess Management", "icon": "FaLayerGroup",
    "base_path": "/mms", "nav_section": "Mess Management", "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "mms.student", "label": "My Mess", "icon": "FaUserCheck",
     "to": "/mms/student", "required_permission": "mess_management.student.use",
     "sort_order": 10},
    {"code": "mms.operations", "label": "Operations", "icon": "FaClipboardList",
     "to": "/mms/operations", "required_permission": "mess_management.operations.view",
     "sort_order": 20},
    {"code": "mms.roles", "label": "Role Management", "icon": "FaUsers",
     "to": "/mms/roles", "required_permission": "mess_management.roles.manage",
     "sort_order": 30},
]

# TODO ISS-MMS-012: Mess Admin menu visibility conflicts with the operational
# data boundary. No menu permission is granted to Mess Admin until clarified.
# TODO ISS-MMS-013/019: decision timeout and vacation reminder cadence are
# institution-defined; no default interval is declared here.
# TODO ISS-MMS-014/015: fulfillment actor and cancellation billing treatment
# remain unspecified by the frozen Problem Statement.
PERMISSIONS = [
    ("mess_management.student.use", "Use student mess services"),
    ("mess_management.operations.view", "View mess operational services"),
    ("mess_management.operations.manage", "Manage mess operational services"),
    ("mess_management.requests.review", "Decide student mess requests"),
    ("mess_management.menu.manage", "Maintain weekly menu"),
    ("mess_management.billing.manage", "Generate, finalize and publish bills"),
    ("mess_management.feedback.view", "Review student feedback"),
    ("mess_management.surveys.manage", "Manage vacation surveys"),
    ("mess_management.announcements.publish", "Publish mess announcements"),
    ("mess_management.reports.warden", "View supervisory reports"),
    ("mess_management.reports.caretaker", "Generate operational reports"),
    ("mess_management.roles.manage", "Assign mess roles"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "student": ["mess_management.student.use"],
    "mess_admin": ["mess_management.roles.manage"],
    "mess_caretaker": [
        "mess_management.operations.view", "mess_management.operations.manage",
        "mess_management.requests.review", "mess_management.menu.manage",
        "mess_management.billing.manage", "mess_management.feedback.view",
        "mess_management.surveys.manage",
        "mess_management.announcements.publish",
        "mess_management.reports.caretaker",
    ],
    "mess_warden": [
        "mess_management.operations.view", "mess_management.feedback.view",
        "mess_management.announcements.publish",
        "mess_management.reports.warden",
    ],
}
