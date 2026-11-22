"""IAA-owned scheduled tasks."""
TASK_ROUTES={"modules.iaa.tasks.run_approval_escalation":{"queue":"default"}}
BEAT_SCHEDULE={"iaa.escalate-overdue-approvals":{
    "task":"modules.iaa.tasks.run_approval_escalation","schedule":60.0,"options":{"expires":55}}}
