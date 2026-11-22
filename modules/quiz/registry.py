MODULE = {
    "code": "quiz",
    "label": "Quiz Management",
    "icon": "ClipboardCheck",
    "base_path": "/quiz",
    "nav_section": "Academic",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "quiz.manage",
        "label": "Quizzes",
        "icon": "ClipboardCheck",
        "to": "/quiz",
        "required_permission": "quiz.manage",
        "sort_order": 10,
    },
    {
        "code": "quiz.attempt",
        "label": "My Quizzes",
        "icon": "Pencil",
        "to": "/quiz/my",
        "required_permission": "quiz.attempt",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("quiz.manage", "Create and manage quizzes"),
    ("quiz.question_bank.manage", "Manage the question bank"),
    ("quiz.evaluate", "Evaluate quiz submissions"),
    ("quiz.release", "Release quiz results"),
    ("quiz.report.view", "View quiz reports"),
    ("quiz.attempt", "Attempt eligible quizzes"),
    ("quiz.result.view_own", "View own released results"),
    ("quiz.history.view_own", "View own quiz history"),
]

ROLE_GRANTS = {
    "professor": [
        "quiz.manage",
        "quiz.question_bank.manage",
        "quiz.evaluate",
        "quiz.release",
        "quiz.report.view",
    ],
    "student": ["quiz.attempt", "quiz.result.view_own", "quiz.history.view_own"],
}
