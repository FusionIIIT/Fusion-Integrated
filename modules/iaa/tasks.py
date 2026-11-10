from celery import shared_task

from modules.iaa.services import escalate_overdue


@shared_task(name="iaa.escalate_approvals")
def escalate_approvals():
    return escalate_overdue()
