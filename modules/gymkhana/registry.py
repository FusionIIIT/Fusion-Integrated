"""What the server tells the shell about this module (ADR-0010)."""
from __future__ import annotations

MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "icon": "Trophy",
    "base_path": "/gymkhana",
    "nav_section": "Gymkhana",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student views
    {
        "code": "gymkhana.student.clubs",
        "label": "Clubs",
        "icon": "UsersThree",
        "to": "/gymkhana/clubs",
        "required_permission": "gymkhana.club.view",
        "sort_order": 10,
    },
    {
        "code": "gymkhana.student.memberships",
        "label": "My Memberships",
        "icon": "IdentificationBadge",
        "to": "/gymkhana/my-memberships",
        "required_permission": "gymkhana.membership.view",
        "sort_order": 20,
    },
    {
        "code": "gymkhana.student.schedule",
        "label": "Schedule",
        "icon": "CalendarBlank",
        "to": "/gymkhana/schedule",
        "required_permission": "gymkhana.session.view",
        "sort_order": 30,
    },
    {
        "code": "gymkhana.student.polls",
        "label": "Voting Polls",
        "icon": "CheckSquareOffset",
        "to": "/gymkhana/polls",
        "required_permission": "gymkhana.poll.view",
        "sort_order": 40,
    },
    # -- Club Head views
    {
        "code": "gymkhana.head.manage",
        "label": "Club Management",
        "icon": "GearSix",
        "to": "/gymkhana/manage-club",
        "required_permission": "gymkhana.membership.view",
        "sort_order": 50,
    },
    {
        "code": "gymkhana.head.bookings",
        "label": "Book Venue",
        "icon": "CalendarPlus",
        "to": "/gymkhana/book-venue",
        "required_permission": "gymkhana.session.create",
        "sort_order": 60,
    },
    {
        "code": "gymkhana.head.budget",
        "label": "Budget Tracking",
        "icon": "Coins",
        "to": "/gymkhana/budget-requests",
        "required_permission": "gymkhana.budget.create",
        "sort_order": 70,
    },
    {
        "code": "gymkhana.head.reports",
        "label": "Event Reports",
        "icon": "FileText",
        "to": "/gymkhana/event-reports",
        "required_permission": "gymkhana.report.create",
        "sort_order": 80,
    },
    # -- Faculty Councillor view
    {
        "code": "gymkhana.faculty.review",
        "label": "Report Review",
        "icon": "FileSearch",
        "to": "/gymkhana/councillor-review",
        "required_permission": "gymkhana.report.review",
        "sort_order": 85,
    },
    # -- Student Admin view
    {
        "code": "gymkhana.admin.approvals",
        "label": "Club Approvals",
        "icon": "Checks",
        "to": "/gymkhana/club-approvals",
        "required_permission": "gymkhana.club.approve",
        "sort_order": 90,
    },
]

PERMISSIONS = [
    ("gymkhana.club.view", "Browse confirmed clubs"),
    ("gymkhana.club.create", "Create new club record"),
    ("gymkhana.club.approve", "Approve open club to confirmed"),
    ("gymkhana.leadership.update", "Replace club coordinator and co-coordinator"),
    ("gymkhana.session.view", "View public club sessions"),
    ("gymkhana.session.create", "Book club session"),
    ("gymkhana.event.view", "View public club events"),
    ("gymkhana.event.create", "Book club event"),
    ("gymkhana.membership.view", "View club membership applications"),
    ("gymkhana.membership.create", "Apply for club membership"),
    ("gymkhana.membership.approve", "Approve pending club membership"),
    ("gymkhana.poll.view", "View active eligible voting polls"),
    ("gymkhana.poll.create", "Create voting poll"),
    ("gymkhana.poll.update", "Cast vote in active poll"),
    ("gymkhana.budget.view", "View club budget requests"),
    ("gymkhana.budget.create", "Submit club budget request"),
    ("gymkhana.report.view", "View submitted club event reports"),
    ("gymkhana.report.create", "Submit club event report"),
    ("gymkhana.report.review", "Review event report as faculty councillor"),
]

SYSTEM_PERMISSIONS = []

SCOPE_PERMISSIONS = [
    "gymkhana.membership.approve",
    "gymkhana.session.create",
    "gymkhana.event.create",
    "gymkhana.poll.create",
    "gymkhana.leadership.update",
    "gymkhana.budget.create",
    "gymkhana.report.create",
    "gymkhana.report.review",
]

_STUDENT = [
    "gymkhana.club.view",
    "gymkhana.membership.view",
    "gymkhana.membership.create",
    "gymkhana.session.view",
    "gymkhana.event.view",
    "gymkhana.poll.view",
    "gymkhana.poll.update",
]

_CLUB_HEAD = [
    "gymkhana.club.view",
    "gymkhana.session.view",
    "gymkhana.session.create",
    "gymkhana.event.view",
    "gymkhana.event.create",
    "gymkhana.membership.view",
    "gymkhana.membership.approve",
    "gymkhana.poll.view",
    "gymkhana.poll.create",
    "gymkhana.leadership.update",
    "gymkhana.budget.view",
    "gymkhana.budget.create",
    "gymkhana.report.view",
    "gymkhana.report.create",
]

_FACULTY_COUNCILLOR = [
    "gymkhana.club.view",
    "gymkhana.session.view",
    "gymkhana.event.view",
    "gymkhana.report.view",
    "gymkhana.report.review",
]

_STUDENT_ADMIN = [
    "gymkhana.club.view",
    "gymkhana.club.create",
    "gymkhana.club.approve",
    "gymkhana.session.view",
    "gymkhana.event.view",
    "gymkhana.report.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "co-ordinator": _CLUB_HEAD,
    "co co-ordinator": _CLUB_HEAD,
    "faculty": _FACULTY_COUNCILLOR,
    "Dean_s": _STUDENT_ADMIN,
    "studentacadadmin": _STUDENT_ADMIN,
}
