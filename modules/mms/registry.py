"""MMS permissions and server-filtered navigation metadata."""

MODULE = {
    "code": "mms", "label": "Mess Management", "icon": "FaLayerGroup",
    "base_path": "/mms", "nav_section": "Mess Management", "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "mms.student", "label": "My Mess", "icon": "FaUserCheck",
     "to": "/mms/student", "required_permission": "mms.student.use",
     "sort_order": 10},
    {"code": "mms.operations", "label": "Operations", "icon": "FaClipboardList",
     "to": "/mms/operations", "required_permission": "mms.operations.view",
     "sort_order": 20},
    {"code": "mms.roles", "label": "Role Management", "icon": "FaUsers",
     "to": "/mms/roles", "required_permission": "mms.roles.manage",
     "sort_order": 30},
]

PERMISSIONS = [
    ("mms.student.use", "Use student mess services"),
    ("mms.operations.view", "View mess operational services"),
    ("mms.operations.manage", "Manage mess operational services"),
    ("mms.requests.review", "Decide student mess requests"),
    ("mms.menu.manage", "Maintain weekly menu"),
    ("mms.billing.manage", "Generate, finalize and publish bills"),
    ("mms.feedback.view", "Review student feedback"),
    ("mms.surveys.manage", "Manage vacation surveys"),
    ("mms.announcements.publish", "Publish mess announcements"),
    ("mms.reports.warden", "View supervisory reports"),
    ("mms.reports.caretaker", "Generate operational reports"),
    ("mms.roles.manage", "Assign mess roles"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "student": ["mms.student.use"],
    "mess_admin": ["mms.roles.manage"],
    "mess_caretaker": [
        "mms.operations.view", "mms.operations.manage",
        "mms.requests.review", "mms.menu.manage",
        "mms.billing.manage", "mms.feedback.view",
        "mms.surveys.manage",
        "mms.announcements.publish",
        "mms.reports.caretaker",
    ],
    "mess_warden": [
        "mms.operations.view", "mms.feedback.view",
        "mms.announcements.publish",
        "mms.reports.warden",
    ],
}
