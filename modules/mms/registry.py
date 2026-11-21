"""MMS module registry declaration conforming to ADR-0010."""

from typing import Any, Dict, List

MODULE: Dict[str, Any] = {
    "code": "mess_module",
    "label": "Mess Management",
    "icon": "ForkKnife",
    "base_path": "/mms",
    "nav_section": "Campus Life",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS: List[Dict[str, Any]] = [
    {
        "code": "mms.dashboard",
        "label": "Mess Dashboard",
        "icon": "House",
        "to": "/mms",
        "required_permission": "mess_module.menu.view",
        "sort_order": 10,
    },
    {
        "code": "mms.menu",
        "label": "Weekly Menu",
        "icon": "ForkKnife",
        "to": "/mms/menu",
        "required_permission": "mess_module.menu.view",
        "sort_order": 20,
    },
    {
        "code": "mms.registration",
        "label": "Registration",
        "icon": "Checks",
        "to": "/mms/registration",
        "required_permission": "mess_module.registration.submit",
        "sort_order": 30,
    },
    {
        "code": "mms.rebates",
        "label": "Rebates",
        "icon": "CalendarBlank",
        "to": "/mms/rebates",
        "required_permission": "mess_module.rebate.submit",
        "sort_order": 40,
    },
]

PERMISSIONS = [
    ("mess_module.menu.view", "See mess menu schedule"),
    ("mess_module.menu.manage", "Update mess menu"),
    ("mess_module.registration.submit", "Submit mess registration"),
    ("mess_module.registration.review", "Review student registrations"),
    ("mess_module.rebate.submit", "Submit meal rebate"),
    ("mess_module.rebate.review", "Approve or reject rebates"),
    ("mess_module.feedback.submit", "Submit mess feedback"),
    ("mess_module.role.assign", "Assign caretaker or warden roles"),
]

ROLE_GRANTS = {
    "student": [
        "mess_module.menu.view",
        "mess_module.registration.submit",
        "mess_module.rebate.submit",
        "mess_module.feedback.submit",
    ],
    "caretaker": [
        "mess_module.menu.view",
        "mess_module.menu.manage",
        "mess_module.registration.review",
        "mess_module.rebate.review",
    ],
    "warden": [
        "mess_module.menu.view",
        "mess_module.rebate.review",
        "mess_module.role.assign",
    ],
}
