"""Fusion module metadata. Permission grants must be configured in IAM."""
MODULE = {
    "code": "elm", "label": "Employee Leave Management", "icon": "Calendar",
    "base_path": "/elm", "nav_section": "Employee Services", "sort_order": 30,
    "status": "active",
}
NAV_ITEMS = [
    {"code": "elm.requests", "label": "My Leave Requests", "icon": "Calendar",
     "to": "/elm/requests", "required_permission": "elm.request.self",
     "sort_order": 10},
]
PERMISSIONS = [
    ("elm.request.self", "View and submit own leave requests"),
    ("elm.request.review", "Review assigned leave requests"),
    ("elm.request.sanction", "Make final leave decisions"),
]
SYSTEM_PERMISSIONS = []
ROLE_GRANTS = {}
