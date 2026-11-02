"""Registry and role permissions for Module 20 (Quiz Management)."""

MODULE = {
    "code": "quizzes",
    "label": "Quiz Management",
    "icon": "Exam",
    "base_path": "/quizzes",
    "nav_section": "Academics",
    "sort_order": 45,
    "status": "active",
}

NAV_ITEMS = [
    # --- Student Self-Service ---
    {
        "code": "quizzes.assigned",
        "label": "My Quizzes",
        "icon": "BookOpen",
        "to": "/quizzes/my-quizzes",
        "required_permission": "quiz.attempt.start",
        "sort_order": 10,
    },
    {
        "code": "quizzes.results",
        "label": "Quiz Results & History",
        "icon": "ChartLine",
        "to": "/quizzes/results",
        "required_permission": "quiz.result.view",
        "sort_order": 20,
    },

    # --- Professor Quiz Management ---
    {
        "code": "quizzes.manage",
        "label": "Manage Quizzes",
        "icon": "FolderSimplePlus",
        "to": "/quizzes/manage",
        "required_permission": "quiz.quiz.create",
        "sort_order": 30,
    },
    {
        "code": "quizzes.question_bank",
        "label": "Question Bank",
        "icon": "Database",
        "to": "/quizzes/questions",
        "required_permission": "quiz.quiz.manage_questions",
        "sort_order": 40,
    },
    {
        "code": "quizzes.evaluations",
        "label": "Submissions & Evaluation",
        "icon": "CheckSquareOffset",
        "to": "/quizzes/evaluations",
        "required_permission": "quiz.evaluation.evaluate_subjective",
        "sort_order": 50,
    },
    {
        "code": "quizzes.analytics",
        "label": "Performance Reports",
        "icon": "PresentationChart",
        "to": "/quizzes/reports",
        "required_permission": "quiz.quiz.create",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    # Professor permissions
    ("quiz.quiz.create", "Create and edit quiz definitions (drafts)"),
    ("quiz.quiz.manage_questions", "Add, edit, remove questions from quiz or question bank"),
    ("quiz.quiz.configure", "Configure quiz rules, timing, attempts, and visibility"),
    ("quiz.quiz.publish", "Publish or schedule quiz for student availability"),
    ("quiz.quiz.archive", "Archive closed quizzes"),
    ("quiz.evaluation.evaluate_subjective", "Grade subjective student responses and finalize marks"),
    ("quiz.result.release", "Release evaluated quiz results to students"),

    # Student permissions
    ("quiz.attempt.start", "Start an eligible quiz attempt within availability window"),
    ("quiz.attempt.record_response", "Record or update responses during an active attempt"),
    ("quiz.attempt.submit", "Manually submit a completed quiz attempt"),
    ("quiz.result.view", "View released quiz results and performance history"),

    # System permissions
    ("quiz.system.process_boundary", "Automated availability boundary transitions (Scheduled -> Available, Available -> Closed)"),
    ("quiz.system.auto_submit", "Automated time-expiry attempt submission"),
    ("quiz.system.evaluate_objective", "Automated objective response scoring and aggregation"),
]

SYSTEM_PERMISSIONS = [
    "quiz.system.process_boundary",
    "quiz.system.auto_submit",
    "quiz.system.evaluate_objective",
]

_STUDENT = [
    "quiz.attempt.start",
    "quiz.attempt.record_response",
    "quiz.attempt.submit",
    "quiz.result.view",
]

_PROFESSOR = [
    "quiz.quiz.create",
    "quiz.quiz.manage_questions",
    "quiz.quiz.configure",
    "quiz.quiz.publish",
    "quiz.quiz.archive",
    "quiz.evaluation.evaluate_subjective",
    "quiz.result.release",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _PROFESSOR,
    "professor": _PROFESSOR,
    "HOD (CSE)": _PROFESSOR,
    "HOD (ECE)": _PROFESSOR,
    "HOD (ME)": _PROFESSOR,
    "HOD (NS)": _PROFESSOR,
    "HOD (Design)": _PROFESSOR,
    "Dean Academic": _PROFESSOR,
}
