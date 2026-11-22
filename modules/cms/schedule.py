BEAT_SCHEDULE = {
    "cms-process-sla": {
        "task": "modules.cms.tasks.process_sla",
        "schedule": 300.0,
    },
}
TASK_ROUTES = {"modules.cms.tasks.process_sla": {"queue": "cms"}}
