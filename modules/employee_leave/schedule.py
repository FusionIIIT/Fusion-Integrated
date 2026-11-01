BEAT_SCHEDULE = {
    "employee-leave.process-sla": {
        "task": "employee_leave.process_sla",
        "schedule": 900.0,
        "options": {"expires": 890},
    },
}

TASK_ROUTES = {
    "employee_leave.process_sla": {"queue": "default"},
}
