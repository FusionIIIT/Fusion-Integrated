# Scheduled beat configuration and task routing for vh module.
from celery.schedules import crontab

TASK_ROUTES = {
    "vh.evaluate_no_shows": {"queue": "default"},
    "vh.evaluate_overstays": {"queue": "default"},
    "vh.send_stay_reminders": {"queue": "default"},
    "vh.check_inventory_thresholds": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "vh.evaluate-no-shows": {
        "task": "vh.evaluate_no_shows",
        "schedule": 3600.0,
        "options": {"expires": 3500},
    },
    "vh.evaluate-overstays": {
        "task": "vh.evaluate_overstays",
        "schedule": 3600.0,
        "options": {"expires": 3500},
    },
    "vh.send-stay-reminders": {
        "task": "vh.send_stay_reminders",
        "schedule": crontab(hour=8, minute=0),
        "options": {"expires": 3600},
    },
    "vh.check-inventory-thresholds": {
        "task": "vh.check_inventory_thresholds",
        "schedule": 1800.0,
        "options": {"expires": 1700},
    },
}
