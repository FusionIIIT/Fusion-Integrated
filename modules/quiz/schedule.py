"""Quiz-owned Celery routes and periodic lifecycle scans."""

TASK_ROUTES = {
    "quiz.tasks.auto_submit_expired_attempts": {"queue": "default"},
    "quiz.tasks.process_quiz_boundaries": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "quiz-process-boundaries": {
        "task": "quiz.tasks.process_quiz_boundaries",
        "schedule": 15.0,
        "options": {"queue": "default", "expires": 14},
    },
    "quiz-auto-submit-expired": {
        "task": "quiz.tasks.auto_submit_expired_attempts",
        "schedule": 15.0,
        "options": {"queue": "default", "expires": 14},
    },
}
