"""Celery background tasks for leave module."""

from celery import shared_task

from modules.leave.services.sla import process_sla_clocks


@shared_task
def process_sla():
    return process_sla_clocks()


@shared_task
def process_year_end(year: int | None = None):
    import datetime

    from modules.directory import contracts as directory
    from modules.leave.services.yearend import run_year_end_processing

    target_year = year or datetime.date.today().year
    employees = directory.get_employees()
    all_uids = [e.user_id for e in employees]
    fac_uids = [e.user_id for e in employees if e.kind == "faculty"]
    return run_year_end_processing(target_year, all_uids, fac_uids)
