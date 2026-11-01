"""What the server tells the shell about this module (ADR-0010)."""
MODULE = {
    "code": "quizzes", "label": "Quizzes", "icon": "FaQuestionCircle",
    "base_path": "/quizzes", "nav_section": "Academics", "sort_order": 30,
    "status": "planned",
}

#: Empty until the client has the routes; nav_matches_routes enforces that.
NAV_ITEMS = []

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("quizzes.quiz.view", "See available quizzes and one's own attempts"),
    ("quizzes.quiz.manage", "Create, edit, publish and archive quizzes"),
    ("quizzes.attempt.create", "Attempt a quiz"),
    ("quizzes.attempt.evaluate", "Grade attempts and release results"),
]

#: Opening, closing and auto-submitting run on time boundaries, not permissions.
SYSTEM_PERMISSIONS = []

_STUDENT = ["quizzes.quiz.view", "quizzes.attempt.create"]
_FACULTY = ["quizzes.quiz.manage", "quizzes.attempt.evaluate"]   # BR-QZ-001

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
}
