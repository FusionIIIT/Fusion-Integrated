from celery import shared_task
from django.utils import timezone

from modules.elm.services.administration import process_sla, process_year_end


@shared_task
def sweep_sla():
    return process_sla()


@shared_task
def close_previous_year():
    return process_year_end(timezone.localdate().year - 1)
