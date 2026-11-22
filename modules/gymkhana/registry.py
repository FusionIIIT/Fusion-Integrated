MODULE = {
    "code": "gymkhana",
    "label": "Gymkhana",
    "icon": "Users",
    "base_path": "/gymkhana",
    "nav_section": "Student Life",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "gymkhana.home",
        "label": "Gymkhana",
        "icon": "Users",
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


def readiness() -> list[str]:
    """Return a list of unmet prerequisites for this module.

    Empty list means the module is ready to serve traffic.
    """
    from pathlib import Path

    from django.conf import settings

    unmet = []
    root = Path(settings.GYMKHANA_UPLOAD_ROOT).expanduser()
    if not root.exists():
        unmet.append(
            f"Upload directory {root} does not exist. Create it and ensure application "
            "write access."
        )
    if not getattr(settings, "GYMKHANA_VENUES", None):
        unmet.append("No Gymkhana venues configured in settings.GYMKHANA_VENUES.")
    return unmet

