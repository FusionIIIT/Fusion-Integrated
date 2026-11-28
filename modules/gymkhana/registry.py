"""What the server tells the shell about this module (ADR-0010)."""
MODULE = {
    "code": "gymkhana", "label": "Gymkhana", "icon": "UsersThree",
    "base_path": "/gymkhana", "nav_section": "Gymkhana", "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "gymkhana.clubs", "label": "Clubs", "icon": "UsersThree",
     "to": "/gymkhana/clubs",
     "required_permission": "gymkhana.membership.create", "sort_order": 10},
    {"code": "gymkhana.polls", "label": "Polls", "icon": "ListChecks",
     "to": "/gymkhana/polls",
     "required_permission": "gymkhana.vote.create", "sort_order": 20},
    {"code": "gymkhana.schedule", "label": "Club Schedule", "icon": "CalendarBlank",
     "to": "/gymkhana/schedule",
     "required_permission": "gymkhana.booking.view", "sort_order": 30},
    {"code": "gymkhana.my_clubs", "label": "My Clubs", "icon": "Flag",
     "to": "/gymkhana/my-clubs",
     "required_permission": "gymkhana.leadership.assign", "sort_order": 40},
    {"code": "gymkhana.administration", "label": "Club Administration",
     "icon": "ShieldCheck", "to": "/gymkhana/administration",
     "required_permission": "gymkhana.club.approve", "sort_order": 60},
    {"code": "gymkhana.reports", "label": "Club Reports", "icon": "FileText",
     "to": "/gymkhana/reports",
     "required_permission": "gymkhana.event_report.review", "sort_order": 70},
]

PERMISSIONS = [
    ("gymkhana.club.view", "See clubs"),
    ("gymkhana.club.create", "Create a club"),
    ("gymkhana.club.approve", "Confirm an open club"),
    ("gymkhana.leadership.assign", "Change a club's coordinator and co-coordinator"),
    ("gymkhana.membership.view", "See membership applications"),
    ("gymkhana.membership.create", "Apply to join a club"),
    ("gymkhana.membership.approve", "Approve membership applications"),
    ("gymkhana.booking.view", "See club sessions and events"),
    ("gymkhana.booking.create", "Book a club session or event"),
    ("gymkhana.poll.view", "See polls"),
    ("gymkhana.poll.create", "Create a voting poll"),
    ("gymkhana.vote.create", "Vote in a poll"),
    ("gymkhana.budget_request.view", "See club budget requests"),
    ("gymkhana.budget_request.create", "Submit a club budget request"),
    ("gymkhana.event_report.view", "See the club's own event reports"),
    ("gymkhana.event_report.create", "Submit a club event report"),
    ("gymkhana.event_report.review", "Review event reports of an assigned club"),
]

# The notification drain authorises nothing, so no system permission exists.
SYSTEM_PERMISSIONS: list[str] = []
# Every scope here comes from club data, not from a permission code.
SCOPE_PERMISSIONS: list[str] = []

_STUDENT = [
    "gymkhana.club.view",
    "gymkhana.membership.view", "gymkhana.membership.create",
    "gymkhana.poll.view", "gymkhana.vote.create",
    "gymkhana.booking.view",
    # Club Head: held by every student, effective only for clubs they lead (BR-GYM-010).
    "gymkhana.leadership.assign", "gymkhana.membership.approve",
    "gymkhana.booking.create", "gymkhana.poll.create",
    "gymkhana.budget_request.view", "gymkhana.budget_request.create",
    "gymkhana.event_report.view", "gymkhana.event_report.create",
]

_STUDENT_ADMIN = ["gymkhana.club.view", "gymkhana.club.create", "gymkhana.club.approve"]

_FACULTY = ["gymkhana.event_report.review"]

ROLE_GRANTS = {
    "student": _STUDENT,
    "Student Admin": _STUDENT_ADMIN,
    "faculty": _FACULTY,
}


def readiness() -> list[str]:
    """Unmet prerequisites, each a sentence saying what to do."""
    from modules.gymkhana.selectors.venues import current_venue_names

    unmet = []
    if not current_venue_names():
        unmet.append(
            "No Gymkhana venue list is in effect. Run `manage.py "
            "seed_gymkhana_venues --venue \"<name>\" ...` with the institute's "
            "venues; until then no session or event can be booked.")
    return unmet
