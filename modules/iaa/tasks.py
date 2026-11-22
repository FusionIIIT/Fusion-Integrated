from celery import shared_task
from modules.iaa.services.iaa import escalate_overdue_approvals

@shared_task(name="modules.iaa.tasks.run_approval_escalation")
def run_approval_escalation():
    return escalate_overdue_approvals()
