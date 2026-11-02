MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "icon": "FaUsers",
    "base_path": "/gymkhana",
    "nav_section": "Student Life",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "gymkhana.home",
        "label": "Gymkhana",
        "icon": "FaUsers",
        "to": "/gymkhana",
        "required_permission": "gymkhana.module.view",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("gymkhana.module.view", "Access the Gymkhana module"),
    ("gymkhana.people.search", "Find student and faculty records for Gymkhana"),
    ("gymkhana.club.manage", "Create and confirm clubs"),
    ("gymkhana.club.leadership", "Change club leadership"),
    ("gymkhana.activity.manage", "Book club sessions and events"),
    ("gymkhana.membership.apply", "Apply for club membership"),
    ("gymkhana.membership.review", "Review club membership applications"),
    ("gymkhana.poll.view", "View eligible voting polls"),
    ("gymkhana.poll.manage", "Create club polls"),
    ("gymkhana.poll.vote", "Vote in eligible polls"),
    ("gymkhana.budget.manage", "Submit and view club budget requests"),
    ("gymkhana.report.submit", "Submit club event reports"),
    ("gymkhana.report.view", "Review assigned club event reports"),
    ("gymkhana.file.view", "Download Gymkhana attachments"),
]

SYSTEM_PERMISSIONS = []

_STUDENT = [
    "gymkhana.module.view",
    "gymkhana.people.search",
    "gymkhana.club.leadership",
    "gymkhana.activity.manage",
    "gymkhana.membership.apply",
    "gymkhana.membership.review",
    "gymkhana.poll.view",
    "gymkhana.poll.manage",
    "gymkhana.poll.vote",
    "gymkhana.budget.manage",
    "gymkhana.report.submit",
    "gymkhana.file.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": [
        "gymkhana.module.view",
        "gymkhana.people.search",
        "gymkhana.report.view",
        "gymkhana.file.view",
    ],
    "Student Admin": [
        "gymkhana.module.view",
        "gymkhana.people.search",
        "gymkhana.club.manage",
    ],
}
