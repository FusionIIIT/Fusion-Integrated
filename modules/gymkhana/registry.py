"""What the server tells the shell about this module (ADR-0010).

Nav items carry required_permission and the server filters before sending.
"""

MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "icon": "Award",
    "base_path": "/gymkhana",
    "nav_section": "Campus Life",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "gymkhana.clubs",
        "label": "Clubs Directory",
        "icon": "UsersThree",
        "to": "/gymkhana/clubs",
        "required_permission": "gymkhana.club.view",
        "sort_order": 10,
    },
    {
        "code": "gymkhana.polls",
        "label": "Voting Polls",
        "icon": "ChartBar",
        "to": "/gymkhana/polls",
        "required_permission": "gymkhana.poll.vote",
        "sort_order": 20,
    },
    {
        "code": "gymkhana.manage",
        "label": "Club Management",
        "icon": "Gear",
        "to": "/gymkhana/manage",
        "required_permission": "gymkhana.club.approve",
        "sort_order": 30,
    },
    {
        "code": "gymkhana.activities",
        "label": "Club Activities",
        "icon": "Calendar",
        "to": "/gymkhana/activities",
        "required_permission": "gymkhana.session.book",
        "sort_order": 40,
    },
    {
        "code": "gymkhana.memberships",
        "label": "Memberships",
        "icon": "Users",
        "to": "/gymkhana/memberships",
        "required_permission": "gymkhana.membership.approve",
        "sort_order": 50,
    },
    {
        "code": "gymkhana.budgets",
        "label": "Budget Requests",
        "icon": "Wallet",
        "to": "/gymkhana/budgets",
        "required_permission": "gymkhana.budget.request",
        "sort_order": 60,
    },
    {
        "code": "gymkhana.reports",
        "label": "Event Reports",
        "icon": "FileText",
        "to": "/gymkhana/reports",
        "required_permission": "gymkhana.report.submit",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("gymkhana.club.create", "Create new Gymkhana club"),
    ("gymkhana.club.approve", "Approve and confirm Gymkhana club"),
    ("gymkhana.club.view", "View Gymkhana clubs and details"),
    ("gymkhana.leadership.update", "Change club coordinator and co-coordinator"),
    ("gymkhana.session.book", "Book club session"),
    ("gymkhana.event.book", "Book club event"),
    ("gymkhana.membership.apply", "Apply for club membership"),
    ("gymkhana.membership.approve", "Approve club membership application"),
    ("gymkhana.poll.create", "Create voting poll"),
    ("gymkhana.poll.vote", "Vote in club poll"),
    ("gymkhana.budget.request", "Submit club budget request"),
    ("gymkhana.report.submit", "Submit club event report"),
    ("gymkhana.report.review", "Review assigned club event reports"),
]

SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []

ROLE_GRANTS = {
    "Dean_s": [
        "gymkhana.club.create",
        "gymkhana.club.approve",
        "gymkhana.club.view",
    ],
    "studentacadadmin": [
        "gymkhana.club.create",
        "gymkhana.club.approve",
        "gymkhana.club.view",
    ],
    "co-ordinator": [
        "gymkhana.club.view",
        "gymkhana.leadership.update",
        "gymkhana.session.book",
        "gymkhana.event.book",
        "gymkhana.membership.approve",
        "gymkhana.poll.create",
        "gymkhana.budget.request",
        "gymkhana.report.submit",
    ],
    "co": [
        "gymkhana.club.view",
        "gymkhana.leadership.update",
        "gymkhana.session.book",
        "gymkhana.event.book",
        "gymkhana.membership.approve",
        "gymkhana.poll.create",
        "gymkhana.budget.request",
        "gymkhana.report.submit",
    ],
    "Convenor": [
        "gymkhana.club.view",
        "gymkhana.leadership.update",
        "gymkhana.session.book",
        "gymkhana.event.book",
        "gymkhana.membership.approve",
        "gymkhana.poll.create",
        "gymkhana.budget.request",
        "gymkhana.report.submit",
    ],
    "Convener": [
        "gymkhana.club.view",
        "gymkhana.leadership.update",
        "gymkhana.session.book",
        "gymkhana.event.book",
        "gymkhana.membership.approve",
        "gymkhana.poll.create",
        "gymkhana.budget.request",
        "gymkhana.report.submit",
    ],
    "student": [
        "gymkhana.club.view",
        "gymkhana.membership.apply",
        "gymkhana.poll.vote",
    ],
    "ug_student": [
        "gymkhana.club.view",
        "gymkhana.membership.apply",
        "gymkhana.poll.vote",
    ],
    "pg_student": [
        "gymkhana.club.view",
        "gymkhana.membership.apply",
        "gymkhana.poll.vote",
    ],
    "phd_student": [
        "gymkhana.club.view",
        "gymkhana.membership.apply",
        "gymkhana.poll.vote",
    ],
    "Counsellor": [
        "gymkhana.club.view",
        "gymkhana.report.review",
    ],
    "Professor": [
        "gymkhana.club.view",
        "gymkhana.report.review",
    ],
    "Associate Professor": [
        "gymkhana.club.view",
        "gymkhana.report.review",
    ],
    "Assistant Professor": [
        "gymkhana.club.view",
        "gymkhana.report.review",
    ],
}
