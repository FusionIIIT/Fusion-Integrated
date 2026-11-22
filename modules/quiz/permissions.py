"""Quiz module permissions and role grants."""

PERMISSIONS = [
    ("quiz.quiz.view",         "View available quizzes"),
    ("quiz.quiz.manage",       "Create and manage quizzes"),
    ("quiz.quiz.publish",      "Publish and schedule quizzes"),
    ("quiz.attempt.start",     "Start a quiz attempt"),
    ("quiz.attempt.view_own",  "View own attempts and results"),
    ("quiz.evaluation.manage", "Evaluate and release quiz results"),
    ("quiz.report.view",       "View quiz performance reports"),
]

SYSTEM_PERMISSIONS: list[str] = []

_STUDENT = [
    "quiz.quiz.view",
    "quiz.attempt.start",
    "quiz.attempt.view_own",
]

_PROFESSOR = [
    "quiz.quiz.view",
    "quiz.quiz.manage",
    "quiz.quiz.publish",
    "quiz.evaluation.manage",
    "quiz.report.view",
]

ROLE_GRANTS: dict[str, list[str]] = {
    "student": _STUDENT,
    "faculty": _PROFESSOR,
    "professor": _PROFESSOR,
}
