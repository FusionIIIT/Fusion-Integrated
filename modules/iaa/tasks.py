"""Task entry points; add escalation to the deployment's Celery beat schedule."""

from celery import shared_task

from modules.iaa.services import escalate_overdue_approvals


@shared_task(name="iaa.escalate_overdue_approvals")
def escalate_overdue_approval_steps():
    return escalate_overdue_approvals()
