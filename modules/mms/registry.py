"""What the server tells the shell about the MMS module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "mms",
    "label": "Mess Management",
    "icon": "ForkKnife",
    "base_path": "/mms",
    "nav_section": "Services",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student navigation --
    {
        "code": "mms.student.registration",
        "label": "Mess Registration",
        "icon": "Checks",
        "to": "/mms/registration",
        "required_permission": "mms.registration.self",
        "sort_order": 10,
    },
    {
        "code": "mms.student.menu",
        "label": "Mess Menu",
        "icon": "CalendarBlank",
        "to": "/mms/menu",
        "required_permission": "mms.menu.view",
        "sort_order": 20,
    },
    {
        "code": "mms.student.rebate",
        "label": "Mess Rebate",
        "icon": "ClockCounterClockwise",
        "to": "/mms/rebates",
        "required_permission": "mms.rebate.self",
        "sort_order": 30,
    },
    {
        "code": "mms.student.special_food",
        "label": "Special Food",
        "icon": "BowlFood",
        "to": "/mms/special-food",
        "required_permission": "mms.special_food.self",
        "sort_order": 40,
    },
    {
        "code": "mms.student.bills",
        "label": "Mess Bills",
        "icon": "Receipt",
        "to": "/mms/bills",
        "required_permission": "mms.bill.view_self",
        "sort_order": 50,
    },
    {
        "code": "mms.student.feedback",
        "label": "Submit Feedback",
        "icon": "ChatText",
        "to": "/mms/feedback",
        "required_permission": "mms.feedback.submit",
        "sort_order": 60,
    },
    # -- Mess Caretaker navigation --
    {
        "code": "mms.caretaker.dashboard",
        "label": "Caretaker Operations",
        "icon": "Gauge",
        "to": "/mms/operations",
        "required_permission": "mms.registration.review",
        "sort_order": 110,
    },
    {
        "code": "mms.caretaker.windows",
        "label": "Registration Windows",
        "icon": "DoorOpen",
        "to": "/mms/windows",
        "required_permission": "mms.window.manage",
        "sort_order": 120,
    },
    {
        "code": "mms.caretaker.menu",
        "label": "Manage Menu",
        "icon": "PencilSimpleLine",
        "to": "/mms/manage-menu",
        "required_permission": "mms.menu.manage",
        "sort_order": 130,
    },
    {
        "code": "mms.caretaker.bills",
        "label": "Billing Management",
        "icon": "CurrencyInr",
        "to": "/mms/manage-bills",
        "required_permission": "mms.bill.manage",
        "sort_order": 140,
    },
    {
        "code": "mms.caretaker.reports",
        "label": "Operational Reports",
        "icon": "ChartBar",
        "to": "/mms/operational-reports",
        "required_permission": "mms.report.operational",
        "sort_order": 150,
    },
    # -- Mess Warden navigation --
    {
        "code": "mms.warden.oversight",
        "label": "Warden Oversight",
        "icon": "Eye",
        "to": "/mms/oversight",
        "required_permission": "mms.registration.view_oversight",
        "sort_order": 210,
    },
    {
        "code": "mms.warden.reports",
        "label": "Supervisory Reports",
        "icon": "FileText",
        "to": "/mms/supervisory-reports",
        "required_permission": "mms.report.supervisory",
        "sort_order": 220,
    },
    # -- Mess Admin navigation --
    {
        "code": "mms.admin.roles",
        "label": "MMS Role Assignment",
        "icon": "UserGear",
        "to": "/mms/roles",
        "required_permission": "mms.role.manage",
        "sort_order": 310,
    },
]

PERMISSIONS = [
    # Role management
    ("mms.role.manage", "Assign and reassign active Caretaker and Warden roles"),
    # Windows and registration
    ("mms.window.manage", "Open and close mess registration windows"),
    ("mms.registration.self", "Submit mess registration requests"),
    ("mms.registration.review", "Review and approve/reject registration requests"),
    ("mms.registration.view_oversight", "View registration and deregistration requests for oversight"),
    # Deregistration
    ("mms.deregistration.self", "Submit mess deregistration requests"),
    ("mms.deregistration.review", "Review and approve/reject deregistration requests"),
    # Menu
    ("mms.menu.view", "View weekly mess menu"),
    ("mms.menu.manage", "Publish and update weekly mess menu"),
    # Rebate
    ("mms.rebate.self", "Submit mess rebate requests and view status"),
    ("mms.rebate.review", "Review, modify dates, and decide rebate requests"),
    # Vacation food survey
    ("mms.vacation.manage", "Create vacation food continuity surveys and reminders"),
    ("mms.vacation.respond", "Respond to vacation food continuity survey"),
    # Special food
    ("mms.special_food.self", "Submit special food requests and view status"),
    ("mms.special_food.review", "Review and decide special food requests"),
    ("mms.special_food.fulfill", "Update special food fulfillment status to served or cancelled"),
    # Billing
    ("mms.bill.view_self", "View personal monthly mess bills and balances"),
    ("mms.bill.manage", "Review, finalize, and publish monthly mess bills"),
    # Announcements
    ("mms.announcement.publish", "Publish mess-related announcements"),
    ("mms.announcement.view", "View mess-related announcements"),
    # Feedback
    ("mms.feedback.submit", "Submit student mess feedback"),
    ("mms.feedback.view", "Review student mess feedback entries"),
    # Reports
    ("mms.report.operational", "Generate and view Caretaker operational reports"),
    ("mms.report.supervisory", "View and search Warden supervisory reports"),
]

_STUDENT = [
    "mms.registration.self",
    "mms.deregistration.self",
    "mms.menu.view",
    "mms.rebate.self",
    "mms.vacation.respond",
    "mms.special_food.self",
    "mms.bill.view_self",
    "mms.announcement.view",
    "mms.feedback.submit",
]

_CARETAKER = [
    "mms.window.manage",
    "mms.registration.review",
    "mms.deregistration.review",
    "mms.menu.view",
    "mms.menu.manage",
    "mms.rebate.review",
    "mms.vacation.manage",
    "mms.special_food.review",
    "mms.special_food.fulfill",
    "mms.bill.manage",
    "mms.announcement.publish",
    "mms.announcement.view",
    "mms.feedback.view",
    "mms.report.operational",
]

_WARDEN = [
    "mms.registration.view_oversight",
    "mms.menu.view",
    "mms.announcement.publish",
    "mms.announcement.view",
    "mms.feedback.view",
    "mms.report.supervisory",
]

_ADMIN = [
    "mms.role.manage",
    "mms.menu.view",
    "mms.announcement.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "mess_admin": _ADMIN,
    "mess_caretaker": _CARETAKER,
    "mess_warden": _WARDEN,
}
