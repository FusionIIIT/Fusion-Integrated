"""Quiz module registry — navigation and module declaration (ADR-0010)."""

MODULE = {
    "code": "quiz",
    "label": "Quiz",
    "icon": "FaQuestionCircle",
    "base_path": "/quiz",
    "nav_section": "Academic",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "quiz.my_quizzes",
        "label": "My Quizzes",
        "icon": "FaListAlt",
        "to": "/quiz/my-quizzes",
        "required_permission": "quiz.quiz.view",
        "sort_order": 10,
    },
    {
        "code": "quiz.results",
        "label": "My Results",
        "icon": "FaChartBar",
        "to": "/quiz/results",
        "required_permission": "quiz.attempt.view_own",
        "sort_order": 20,
    },
    {
        "code": "quiz.manage",
        "label": "Manage Quizzes",
        "icon": "FaClipboardList",
        "to": "/quiz/manage",
        "required_permission": "quiz.quiz.manage",
        "sort_order": 30,
    },
    {
        "code": "quiz.evaluate",
        "label": "Evaluate",
        "icon": "FaEdit",
        "to": "/quiz/evaluate",
        "required_permission": "quiz.evaluation.manage",
        "sort_order": 40,
    },
    {
        "code": "quiz.reports",
        "label": "Reports",
        "icon": "FaChartPie",
        "to": "/quiz/reports",
        "required_permission": "quiz.report.view",
        "sort_order": 50,
    },
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("quiz.quiz.view", "View available quizzes"),
    ("quiz.quiz.manage", "Create and manage quizzes"),
    ("quiz.quiz.publish", "Publish and schedule quizzes"),
    ("quiz.attempt.start", "Start a quiz attempt"),
    ("quiz.attempt.view_own", "View own attempts and results"),
    ("quiz.evaluation.manage", "Evaluate and release quiz results"),
    ("quiz.report.view", "View quiz performance reports"),
]

SYSTEM_PERMISSIONS: list[str] = []

_STUDENT = [
    "quiz.quiz.view",
    "quiz.attempt.start",
    "quiz.attempt.view_own",
]

_FACULTY = [
    "quiz.quiz.view",
    "quiz.quiz.manage",
    "quiz.quiz.publish",
    "quiz.evaluation.manage",
    "quiz.report.view",
]

ROLE_GRANTS: dict[str, list[str]] = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "Professor": _FACULTY,
    "Associate Professor": _FACULTY,
    "Dean Academic": _FACULTY,
}
