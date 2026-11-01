"""Year-end processing (EL-UC-020, BR-EL-002..009).

Idempotent by reference: re-running a year that has already been settled finds
the `yearend:YYYY` movements and writes nothing further, so a retried task can
never lapse a balance twice.
"""
from __future__ import annotations

import logging

from django.utils import timezone

from modules.leave.services import accounts as account_service

log = logging.getLogger("fusion.leave.yearend")


def run(*, year: int, actor_user_id: int | None = None) -> dict:
    """Settle one year and report what happened, exceptions included."""
    report = account_service.settle_year(year=year, actor_user_id=actor_user_id)
    report["year"] = year
    report["ran_at"] = timezone.now().isoformat()
    log.info("leave.yearend.run year=%s accounts=%s exceptions=%s", year,
             report["accounts"], len(report["exceptions"]))
    return report


def years_to_settle(*, today=None) -> list[int]:
    """The years that have accounts and are already over."""
    from modules.leave.models import LeaveAccount

    today = today or timezone.localdate()
    open_years = (LeaveAccount.objects.filter(year__lt=today.year)
                  .values_list("year", flat=True).distinct().order_by("year"))
    return list(open_years)
