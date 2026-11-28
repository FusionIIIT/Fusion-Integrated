"""Celery tasks for ELM (SF-EL-001, SF-EL-002)."""
from celery import shared_task
from django.utils import timezone

from modules.elm.services import sla, year_end


@shared_task(name="elm.year_end")
def run_year_end(year: int | None = None) -> int:
    target = year or (timezone.localdate().year - 1)
    return year_end.run(target).employees


@shared_task(name="elm.sla")
def run_sla() -> dict:
    return sla.process()
