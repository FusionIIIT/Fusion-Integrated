"""What the server tells the shell about Gymkhana (ADR-0010)."""

MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "icon": "Trophy",
    "base_path": "/gymkhana",
    "nav_section": "Campus Life",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student Nav Items ---
    {
        "code": "gymkhana.clubs",
        "label": "Clubs",
        "icon": "UsersThree",
        "to": "/gymkhana/clubs",
        "required_permission": "gymkhana.club.view",
        "sort_order": 10,
    },
    {
        "code": "gymkhana.my_memberships",
        "label": "My Memberships",
        "icon": "UserCheck",
        "to": "/gymkhana/memberships",
        "required_permission": "gymkhana.membership.view",
        "sort_order": 20,
    },
    {
        "code": "gymkhana.polls",
        "label": "Voting Polls",
        "icon": "CheckSquare",
        "to": "/gymkhana/polls",
        "required_permission": "gymkhana.poll.view",
        "sort_order": 30,
    },
    {
        "code": "gymkhana.calendar",
        "label": "Events & Sessions",
        "icon": "CalendarBlank",
        "to": "/gymkhana/calendar",
        "required_permission": "gymkhana.booking.view",
        "sort_order": 40,
    },
    # -- Club Head / Leadership Nav Items ---
    {
        "code": "gymkhana.club_management",
        "label": "Club Management",
        "icon": "GearSix",
        "to": "/gymkhana/manage",
        "required_permission": "gymkhana.club.manage",
        "sort_order": 50,
    },
    # -- Student Admin Nav Items ---
    {
        "code": "gymkhana.admin_clubs",
        "label": "Club Approvals",
        "icon": "ShieldCheck",
        "to": "/gymkhana/admin",
        "required_permission": "gymkhana.club.approve",
        "sort_order": 60,
    },
    # -- Faculty Councillor Nav Items ---
    {
        "code": "gymkhana.faculty_reports",
        "label": "Club Reports",
        "icon": "FileText",
        "to": "/gymkhana/reports",
        "required_permission": "gymkhana.report.view",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("gymkhana.club.view", "View active and confirmed clubs"),
    ("gymkhana.club.create", "Create a new club proposal"),
    ("gymkhana.club.approve", "Confirm and approve open clubs"),
    ("gymkhana.club.manage", "Manage club operations, members, and bookings"),
    ("gymkhana.booking.view", "View venue bookings and schedules"),
    ("gymkhana.booking.create", "Book club sessions and events"),
    ("gymkhana.membership.view", "View club membership applications"),
    ("gymkhana.membership.create", "Apply for club membership"),
    ("gymkhana.membership.approve", "Approve club membership applications"),
    ("gymkhana.poll.view", "View active targeted polls"),
    ("gymkhana.poll.create", "Create targeted voting polls"),
    ("gymkhana.poll.vote", "Cast vote in targeted polls"),
    ("gymkhana.budget.view", "View club budget tracking requests"),
    ("gymkhana.budget.create", "Submit club budget tracking requests"),
    ("gymkhana.report.view", "View submitted club event reports"),
    ("gymkhana.report.create", "Submit club event reports"),
]

SYSTEM_PERMISSIONS = [
    "gymkhana.poll.expire",
]

SCOPE_PERMISSIONS = {
    "gymkhana.club.manage": "club_id",
    "gymkhana.membership.approve": "club_id",
    "gymkhana.report.view": "club_id",
}

ROLE_GRANTS = {
    "student": [
        "gymkhana.club.view",
        "gymkhana.booking.view",
        "gymkhana.membership.view",
        "gymkhana.membership.create",
        "gymkhana.poll.view",
        "gymkhana.poll.vote",
        "gymkhana.club.manage",
        "gymkhana.booking.create",
        "gymkhana.membership.approve",
        "gymkhana.poll.create",
        "gymkhana.budget.view",
        "gymkhana.budget.create",
        "gymkhana.report.create",
    ],
    "faculty": [
        "gymkhana.club.view",
        "gymkhana.booking.view",
        "gymkhana.report.view",
    ],
    "student_admin": [
        "gymkhana.club.view",
        "gymkhana.club.create",
        "gymkhana.club.approve",
        "gymkhana.booking.view",
        "gymkhana.budget.view",
        "gymkhana.report.view",
    ],
}
