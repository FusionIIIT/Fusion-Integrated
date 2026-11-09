"""MMS owns its scheduled work; external policy cadence is never guessed."""

TASK_ROUTES = {
    "mms.process_deadlines": {"queue": "default"},
    "mms.deliver_notifications": {"queue": "notifications"},
    "mms.generate_ready_bills": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "mms.process-deadlines": {
        "task": "mms.process_deadlines",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "mms.deliver-notifications": {
        "task": "mms.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "mms.generate-ready-bills": {
        "task": "mms.generate_ready_bills",
        "schedule": 900.0,
        "options": {"expires": 890},
    },
}
