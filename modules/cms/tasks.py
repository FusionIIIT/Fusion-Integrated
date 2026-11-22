from celery import shared_task

from modules.cms.services import process_sla


@shared_task(name="modules.cms.tasks.process_sla")
def process_sla_task():
    return process_sla()
