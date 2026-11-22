"""This module's timers; task names are strings so config imports nothing else from here."""

TASK_ROUTES = {
    "department.deliver_notifications": {"queue": "notifications"},
    "department.apply_role_transitions": {"queue": "default"},
}

BEAT_SCHEDULE = {
    # AFR-DEPT-041..046: every notice waits in the outbox until this drains it.
    "department.deliver-notifications": {
        "task": "department.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # UC-DEPT-022: records each tenure that has taken effect; access itself never waits for it.
    "department.apply-role-transitions": {
        "task": "department.apply_role_transitions",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
