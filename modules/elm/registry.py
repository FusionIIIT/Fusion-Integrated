"""ELM's module and own-request permissions."""

from modules.elm.apps import ElmConfig


def register():
    """Preserve the original module registration hook."""
    return ElmConfig.name


MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "FaCalendarCheck",
    "base_path": "/elm",
    "nav_section": "Employee Services",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.requests",
        "label": "My Leave Requests",
        "icon": "FaCalendarCheck",
        "to": "/elm/requests",
        "required_permission": "elm.request.view_self",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("elm.request.create", "Submit a leave request for yourself"),
    ("elm.request.view_self", "View your own leave requests"),
    ("elm.request.withdraw", "Withdraw your own pending leave request"),
]

ROLE_GRANTS = {
    "faculty": [
        "elm.request.create",
        "elm.request.view_self",
        "elm.request.withdraw",
    ],
    "staff": [
        "elm.request.create",
        "elm.request.view_self",
        "elm.request.withdraw",
    ],
}
