"""Permissions for Employee Leave Management."""

MODULE = {
    "code": "elm",
    "status": "active",
    "label": "Employee Leave Management",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Administration",
    "sort_order": 40,
}

NAV_ITEMS = []

PERMISSIONS = [
    ("elm.approve.unit_head", "Approve leave at unit-head stage"),
    ("elm.approve.hierarchy", "Approve leave at higher-authority stage"),
    ("elm.approve.director", "Approve leave at director stage"),
]

ROLE_GRANTS = {
    "HOD (CSE)": ["elm.approve.unit_head"],
    "Registrar": ["elm.approve.hierarchy"],
    "Director": ["elm.approve.director"],
}
SYSTEM_PERMISSIONS = []
