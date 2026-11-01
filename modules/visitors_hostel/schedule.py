from datetime import timedelta

BEAT_SCHEDULE = {
    "vhms-stay-alerts": {
        "task": "visitors_hostel.generate_stay_alerts",
        "schedule": timedelta(hours=1),
    },
    "vhms-email-notifications": {
        "task": "visitors_hostel.deliver_notifications",
        "schedule": timedelta(minutes=2),
    },
}

TASK_ROUTES = {
    "visitors_hostel.*": {"queue": "default"},
}
