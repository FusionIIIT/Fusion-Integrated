BEAT_SCHEDULE = {
    "dept-notification-email": {
        "task": "modules.dept.tasks.deliver_notification_email",
        "schedule": 60.0,
        "options": {"queue": "notifications", "expires": 55},
    },
}
TASK_ROUTES = {"modules.dept.tasks.*": {"queue": "notifications"}}
