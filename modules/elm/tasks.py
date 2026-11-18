import logging
from celery import shared_task

log = logging.getLogger("fusion.elm.tasks")

@shared_task(name="elm.process_year_end", acks_late=True, reject_on_worker_lost=True)
def process_year_end(year: int | None = None) -> dict:
    from modules.elm.services.year_end import process
    report = process(year=year)
    log.info("elm.year_end.completed %s", report)
    return report

@shared_task(name="elm.process_sla", acks_late=True, reject_on_worker_lost=True)
def process_sla() -> dict:
    from modules.elm.services.sla import process
    report = process()
    log.info("elm.sla.processed %s", report)
    return report
