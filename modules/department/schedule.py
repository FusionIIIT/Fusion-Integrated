"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.

Nothing scheduled these before, which meant `deliver_notifications` never ran:
pending notifications stayed pending forever without a mechanism to process them.
"""

#: Which worker pool each task lands on; without it everything queues on default.
TASK_ROUTES = {
    "department.deliver_notifications": {"queue": "notifications"},
    "department.apply_role_transitions": {"queue": "default"},
}

BEAT_SCHEDULE = {
    # Drains often; each pass is capped by NOTIFY_MAX_PER_RUN.
    "department.deliver-notifications": {
        "task": "department.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # Applies role transitions when assignments become effective.
    "department.apply-role-transitions": {
        "task": "department.apply_role_transitions",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
