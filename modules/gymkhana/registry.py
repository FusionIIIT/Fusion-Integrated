"""Permissions and navigation exposed to the Fusion shell."""

MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "icon": "Users",
    "base_path": "/gymkhana",
    "nav_section": "Student Life",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "gymkhana.clubs",
        "label": "Clubs",
        "icon": "Users",
        "to": "/gymkhana/clubs",
        "required_permission": "gymkhana.club.view",
        "sort_order": 10,
    },
    {
        "code": "gymkhana.my_applications",
        "label": "My Membership Applications",
        "icon": "ClipboardList",
        "to": "/gymkhana/my-applications",
        "required_permission": "gymkhana.application.self",
        "sort_order": 20,
    },
    {
        "code": "gymkhana.reviews",
        "label": "Membership Reviews",
        "icon": "UserCheck",
        "to": "/gymkhana/reviews",
        "required_permission": "gymkhana.application.review",
        "sort_order": 30,
    },
]

PERMISSIONS = [
    ("gymkhana.club.view", "View active Gymkhana clubs"),
    ("gymkhana.application.self", "View own club membership applications"),
    ("gymkhana.application.create", "Apply for club membership"),
    ("gymkhana.application.review", "Review club membership applications"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "student": [
        "gymkhana.club.view",
        "gymkhana.application.self",
        "gymkhana.application.create",
    ],
    "club_head": ["gymkhana.application.review"],
    "co_coordinator": ["gymkhana.application.review"],
}
