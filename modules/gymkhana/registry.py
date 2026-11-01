"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "icon": "Trophy",
    "base_path": "/gymkhana",
    "nav_section": "Campus",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # -- student: general access first, because rules 1 gates everything below ---
    {"code": "gymkhana.browse_clubs", "label": "Browse Clubs",
     "icon": "Users", "to": "/gymkhana", "required_permission": "gymkhana.club.view", "sort_order": 10},
    {"code": "gymkhana.my_memberships", "label": "My Memberships",
     "icon": "UserCheck", "to": "/gymkhana/memberships", "required_permission": "gymkhana.membership.apply", "sort_order": 20},
    {"code": "gymkhana.voting_polls", "label": "Voting Polls",
     "icon": "Checks", "to": "/gymkhana/polls", "required_permission": "gymkhana.poll.vote", "sort_order": 30},
    {"code": "gymkhana.manage_club", "label": "Manage Club",
     "icon": "Gear", "to": "/gymkhana/manage", "required_permission": "gymkhana.club.manage", "sort_order": 40},
    {"code": "gymkhana.venue_bookings", "label": "Venue Bookings",
     "icon": "CalendarBlank", "to": "/gymkhana/bookings", "required_permission": "gymkhana.booking.manage", "sort_order": 50},
    {"code": "gymkhana.budget_requests", "label": "Budget Requests",
     "icon": "CurrencyDollar", "to": "/gymkhana/budget", "required_permission": "gymkhana.budget.submit", "sort_order": 60},
    {"code": "gymkhana.event_reports", "label": "Event Reports",
     "icon": "ClipboardText", "to": "/gymkhana/reports", "required_permission": "gymkhana.report.submit", "sort_order": 70},
    {"code": "gymkhana.club_approvals", "label": "Club Approvals",
     "icon": "ShieldCheck", "to": "/gymkhana/admin/clubs", "required_permission": "gymkhana.club.admin", "sort_order": 80},
    {"code": "gymkhana.review_reports", "label": "Review Reports",
     "icon": "FileSearch", "to": "/gymkhana/faculty/reports", "required_permission": "gymkhana.report.review", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("gymkhana.club.view", "See available clubs"),
    ("gymkhana.membership.apply", "Apply for club memberships"),
    ("gymkhana.poll.vote", "Vote in active polls"),
    ("gymkhana.club.manage", "Manage club details and activities"),
    ("gymkhana.booking.manage", "Book venues for events"),
    ("gymkhana.budget.submit", "Submit budget requests"),
    ("gymkhana.report.submit", "Submit event reports"),
    ("gymkhana.club.admin", "Approve club memberships and budgets"),
    ("gymkhana.report.review", "Review submitted event reports"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

_STUDENT = [
    "gymkhana.club.view",
    "gymkhana.membership.apply",
    "gymkhana.poll.vote",
]

_COORDINATOR = [
    *_STUDENT,
    "gymkhana.club.manage",
    "gymkhana.booking.manage",
    "gymkhana.budget.submit",
    "gymkhana.report.submit",
]

_ADMIN = [
    *_COORDINATOR,
    "gymkhana.club.admin",
]

_FACULTY = [
    *_STUDENT,
    "gymkhana.report.review",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "club_coordinator": _COORDINATOR,
    "student_admin": _ADMIN,
    "faculty": _FACULTY,
}
