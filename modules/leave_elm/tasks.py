from celery import shared_task
from .services.events import year_end_rollover, process_task_sla

@shared_task(queue='default')
def elm_year_end_rollover():
    year_end_rollover()

@shared_task(queue='default')
def elm_task_sla():
    process_task_sla()