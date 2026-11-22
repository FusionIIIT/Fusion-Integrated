from celery.schedules import crontab

SCHEDULE = {
    "eis-daily-reminders": {
        "task": "modules.hr_eis.tasks.send_pending_action_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
    "eis-deadline-check": {
        "task": "modules.hr_eis.tasks.check_policy_deadlines",
        "schedule": crontab(hour=0, minute=0),
    },
}
