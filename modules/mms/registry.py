"""MMS permissions and server-driven navigation."""

MODULE = {
    "code": "mms",
    "label": "Mess Management",
    "icon": "ForkKnife",
    "base_path": "/mess",
    "nav_section": "Campus",
    "sort_order": 30,
    "status": "active",
}

PERMISSIONS = [
    ("mms.announcement.publish", "Publish mess announcements"),
    ("mms.announcement.view", "View mess announcements"),
    ("mms.feedback.self", "Submit feedback"),
    ("mms.feedback.view", "Review feedback"),
    ("mms.menu.manage", "Maintain the weekly menu"),
    ("mms.menu.view", "View the weekly menu"),
    ("mms.rebate.decide", "Decide rebate requests"),
    ("mms.rebate.self", "Submit and track own rebates"),
    ("mms.rebate.view", "View rebate requests"),
    ("mms.registration.decide", "Decide mess registration requests"),
    ("mms.registration.self", "Submit own mess registration requests"),
    ("mms.registration.view", "View mess registration requests"),
    ("mms.report.view", "View MMS operational reports"),
    ("mms.role.assign", "Assign Caretaker and Warden roles"),
    ("mms.special_food.decide", "Decide and record special food fulfillment"),
    ("mms.special_food.self", "Submit and track own special food requests"),
    ("mms.special_food.view", "View special food requests"),
    ("mms.vacation.manage", "Create vacation surveys"),
    ("mms.vacation.self", "Respond to own vacation surveys"),
    ("mms.vacation.view", "View vacation survey summaries"),
]

SYSTEM_PERMISSIONS = []

_STUDENT = [
    "mms.registration.self",
    "mms.menu.view",
    "mms.rebate.self",
    "mms.vacation.self",
    "mms.special_food.self",
    "mms.feedback.self",
    "mms.announcement.view",
]
_CARETAKER = [
    "mms.registration.view",
    "mms.registration.decide",
    "mms.menu.view",
    "mms.menu.manage",
    "mms.rebate.view",
    "mms.rebate.decide",
    "mms.vacation.view",
    "mms.vacation.manage",
    "mms.special_food.view",
    "mms.special_food.decide",
    "mms.feedback.view",
    "mms.announcement.view",
    "mms.announcement.publish",
    "mms.report.view",
]
_WARDEN = [
    "mms.registration.view",
    "mms.menu.view",
    "mms.rebate.view",
    "mms.vacation.view",
    "mms.special_food.view",
    "mms.feedback.view",
    "mms.announcement.view",
    "mms.announcement.publish",
    "mms.report.view",
]
ROLE_GRANTS = {
    "student": _STUDENT,
    "mess_caretaker": _CARETAKER,
    "mess_warden": _WARDEN,
    "mess_admin": ["mms.role.assign"],
}

NAV_ITEMS = [
    {
        "code": "mms.student",
        "label": "My Mess",
        "icon": "ForkKnife",
        "to": "/mess",
        "required_permission": "mms.registration.self",
        "sort_order": 10,
    },
    {
        "code": "mms.operations",
        "label": "Mess Operations",
        "icon": "ClipboardText",
        "to": "/mess/operations",
        "required_permission": "mms.registration.view",
        "sort_order": 20,
    },
    {
        "code": "mms.roles",
        "label": "Mess Roles",
        "icon": "Users",
        "to": "/mess/roles",
        "required_permission": "mms.role.assign",
        "sort_order": 30,
    },
]
