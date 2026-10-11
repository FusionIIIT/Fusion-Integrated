"""Scheduled work for elm. Idempotent per (person, type, year) by constraint."""
import logging

from celery import shared_task
from django.utils import timezone

log = logging.getLogger("fusion.elm.tasks")


@shared_task(name="modules.elm.tasks.grant_annual_leave")
def grant_annual_leave(year: int | None = None) -> dict:
    """Record every employee's annual entitlement for `year`."""
    from modules.elm.services import balances as balance_service

    target = year or timezone.localdate().year
    granted, already = balance_service.grant_annual_leave(year=target)
    log.info("elm annual grant %s: %s recorded, %s already present",
             target, granted, already)
    return {"year": target, "granted": granted, "already_present": already}
