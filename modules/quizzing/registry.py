"""Quizzing Navigation and Permission Registry (ADR-0010)."""

MODULE = {
    "code": "quizzing",
    "label": "Quizzing",
    "icon": "Exam",
    "base_path": "/quizzing",
    "nav_section": "Academics",
    "sort_order": 45,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "quizzing.list", "label": "Quizzes", "icon": "ListBullets", "to": "/quizzing", "required_permission": "quizzing.quiz.view", "sort_order": 10},
    {"code": "quizzing.create", "label": "Create Quiz", "icon": "PlusCircle", "to": "/quizzing/create", "required_permission": "quizzing.quiz.author", "sort_order": 20},
]

PERMISSIONS = [
    ("quizzing.quiz.view", "View assigned quizzes and scores"),
    ("quizzing.quiz.attempt", "Take and submit quiz attempts"),
    ("quizzing.quiz.author", "Author quizzes and manage questions"),
    ("quizzing.quiz.grade", "Evaluate submissions and release results"),
]

SYSTEM_PERMISSIONS = ["quizzing.quiz.autosubmit"]

ROLE_GRANTS = {
    "student": ["quizzing.quiz.view", "quizzing.quiz.attempt"],
    "faculty": ["quizzing.quiz.view", "quizzing.quiz.author", "quizzing.quiz.grade"],
}
