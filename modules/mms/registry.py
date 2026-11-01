"""What the server tells the shell about the Mess Management System module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending.
"""

MODULE = {
    "code": "mess_module",
    "label": "Mess Management",
    "icon": "ForkKnife",
    "base_path": "/mms",
    "nav_section": "Services",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "mms.dashboard",
        "label": "Mess Dashboard",
        "icon": "House",
        "to": "/mms/dashboard",
        "required_permission": "mess_module.menu.view",
        "sort_order": 10,
    },
    {
        "code": "mms.menu",
        "label": "Daily Menu",
        "icon": "ForkKnife",
        "to": "/mms/menu",
        "required_permission": "mess_module.menu.view",
        "sort_order": 20,
    },
    {
        "code": "mms.registration",
        "label": "Registration",
        "icon": "UserPlus",
        "to": "/mms/registration",
        "required_permission": "mess_module.registration.submit",
        "sort_order": 30,
    },
    {
        "code": "mms.rebates",
        "label": "Rebate Requests",
        "icon": "Receipt",
        "to": "/mms/rebates",
        "required_permission": "mess_module.rebate.apply",
        "sort_order": 40,
    },
    {
        "code": "mms.caretaker",
        "label": "Caretaker Panel",
        "icon": "ClipboardText",
        "to": "/mms/caretaker",
        "required_permission": "mess_module.registration.review",
        "sort_order": 50,
    },
    {
        "code": "mms.admin",
        "label": "Mess Administration",
        "icon": "Gear",
        "to": "/mms/admin",
        "required_permission": "mess_module.role.manage",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("mess_module.role.manage", "Assign and reassign Mess Caretaker and Mess Warden roles"),
    ("mess_module.registration.submit", "Submit mess registration and deregistration requests"),
    ("mess_module.registration.review", "Review student mess registrations & deregistrations"),
    ("mess_module.menu.manage", "Publish and update daily/weekly mess menus"),
    ("mess_module.menu.view", "View active mess menus and meal schedules"),
    ("mess_module.rebate.apply", "Submit mess rebate applications"),
    ("mess_module.rebate.review", "Review and approve/reject mess rebate applications"),
    ("mess_module.feedback.submit", "Submit feedback and suggestions regarding mess services"),
    ("mess_module.feedback.view", "View student mess feedback and ratings"),
    ("mess_module.oversight.view", "Supervisory oversight of operational requests and reports"),
]

SYSTEM_PERMISSIONS = []

_STUDENT = [
    "mess_module.registration.submit",
    "mess_module.menu.view",
    "mess_module.rebate.apply",
    "mess_module.feedback.submit",
]

_CARETAKER = [
    "mess_module.menu.view",
    "mess_module.menu.manage",
    "mess_module.registration.review",
    "mess_module.rebate.review",
    "mess_module.feedback.view",
]

_WARDEN = [
    "mess_module.menu.view",
    "mess_module.oversight.view",
    "mess_module.feedback.view",
]

_ADMIN = [
    "mess_module.role.manage",
    "mess_module.oversight.view",
    "mess_module.menu.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "mess_caretaker": _CARETAKER,
    "mess_warden": _WARDEN,
    "dean_students": _ADMIN,
    "admin": [*_ADMIN, *_CARETAKER, *_WARDEN],
    "Mess Admin": _ADMIN,
    "Mess Caretaker": _CARETAKER,
    "Mess Warden": _WARDEN,
    "Caretaker": _CARETAKER,
    "Warden": _WARDEN,
}
