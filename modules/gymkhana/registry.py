"""What the server tells the shell about Gymkhana (ADR-0010).
First slice: clubs (BW-GYM-03) and membership (BW-GYM-01). Stays `planned`
until the client pages exist.
"""
MODULE = {
    "code": "gymkhana", "label": "Gymkhana", "icon": "Trophy",
    "base_path": "/gymkhana", "nav_section": "Campus", "sort_order": 15,
    "status": "planned",
}

NAV_ITEMS = [
    {"code": "gymkhana.clubs", "label": "Clubs", "icon": "Users",
     "to": "/gymkhana", "required_permission": "gymkhana.club.view",
     "sort_order": 10},
]

PERMISSIONS = [
    ("gymkhana.club.view", "See clubs"),
    ("gymkhana.club.create", "Create a club (Student Admin)"),
    ("gymkhana.club.approve", "Confirm an open club (Student Admin)"),
    ("gymkhana.membership.create", "Apply for club membership"),
    ("gymkhana.membership.approve", "Approve membership applications (Club Head)"),
]

SYSTEM_PERMISSIONS: list[str] = []

_STUDENT = ["gymkhana.club.view", "gymkhana.membership.create"]
#: The designation alone is not enough: services also check the user heads THAT club.
_CLUB_HEAD = [*_STUDENT, "gymkhana.membership.approve"]
_STUDENT_ADMIN = ["gymkhana.club.view", "gymkhana.club.create", "gymkhana.club.approve"]

#: Keyed by designation names the IAM knows (iam/rbac.py CATALOGUE).
ROLE_GRANTS = {
    "student": _STUDENT,
    "co-ordinator": _CLUB_HEAD,
    "co": _CLUB_HEAD,
    "Dean_s": _STUDENT_ADMIN,
}
