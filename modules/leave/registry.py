"""Registry declaration for the Leave module."""

MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "Calendar",
    "base_path": "/leave",
    "nav_section": "Services",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "leave.apply",
        "label": "Leave Applications",
        "icon": "Calendar",
        "to": "/leave",
        "required_permission": "",
        "sort_order": 10,
    },
]
