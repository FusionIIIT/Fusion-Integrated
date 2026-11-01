"""What the server tells the shell about this module (ADR-0010)."""
MODULE = {
    "code": "quizzes", "label": "Quizzes", "icon": "FaQuestionCircle",
    "base_path": "/quizzes", "nav_section": "Academics", "sort_order": 30,
    "status": "planned",
}

#: Empty until the client has the routes; nav_matches_routes enforces that.
NAV_ITEMS = []

PERMISSIONS = [
    ("quizzes.quiz.view", "See available quizzes and one's own attempts"),
    ("quizzes.quiz.manage", "Create and publish quizzes, release results"),
    ("quizzes.attempt.create", "Attempt a quiz"),
]

#: Opening, closing and auto-submitting run on time boundaries, not permissions.
SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {                                                   # BR-QZ-001
    "student": ["quizzes.quiz.view", "quizzes.attempt.create"],
    "faculty": ["quizzes.quiz.manage"],
}
