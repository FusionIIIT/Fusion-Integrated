"""What ELM needs run on a timer.

Tasks are named by string, not imported, so config
assembles the schedule without importing anything out
of the module.
"""

#: Which worker pool each task lands on; without it
#: everything queues on default.
TASK_ROUTES = {
    "elm.deliver_notifications": {"queue": "notifications"},
    # The sweep is tiny (a few UPDATEs); it stays on
    # default so it never queues behind a report.
    "elm.sla_sweep": {"queue": "default"},
}

BEAT_SCHEDULE = {
    # Drains often; each pass is capped by NOTIFY_MAX_PER_RUN.
    "elm.deliver-notifications": {
        "task": "elm.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # EL-UC-021: reminder/escalation thresholds are in
    # hours, so a five-minute pass is comfortably inside
    # them.
    "elm.sla-sweep": {
        "task": "elm.sla_sweep",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
}
