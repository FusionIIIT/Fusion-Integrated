from celery.schedules import crontab

BEAT_SCHEDULE = {
    "quiz-process-availability-boundaries": {
        "task": "modules.quiz.tasks.process_quiz_availability_boundaries",
        "schedule": crontab(minute="*"),
    },
    "quiz-auto-submit-expired-attempts": {
        "task": "modules.quiz.tasks.auto_submit_expired_attempts_task",
        "schedule": crontab(minute="*"),
    },
}

TASK_ROUTES = {
    "modules.quiz.tasks.*": {"queue": "default"},
}
