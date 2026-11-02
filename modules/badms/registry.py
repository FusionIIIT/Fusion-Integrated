MODULE = {
    "code": "badms",
    "label": "Backup & Archive",
    "icon": "FaDatabase",
    "base_path": "/badms",
    "nav_section": "BADMS",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "badms.archival",
        "label": "Secure Archival",
        "icon": "FaDatabase",
        "to": "/badms/archival",
        "required_permission": "badms.archival.submit",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("badms.archival.submit", "Submit and track secure archival requests"),
    ("badms.archival.review", "Review archival requests for own department"),
]

ROLE_GRANTS = {
    "student": ["badms.archival.submit"],
    "faculty": ["badms.archival.submit"],
    "staff": ["badms.archival.submit"],
    "HoD": ["badms.archival.submit", "badms.archival.review"],
}
