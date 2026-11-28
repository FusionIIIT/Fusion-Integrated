"""The only ELM surface for the Academic Calendar integration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from django.db import transaction

from modules.elm.models import VacationPeriod


@dataclass(frozen=True)
class VacationWindow:
    source_reference: str
    starts_on: date
    ends_on: date
    academic_year: str


@transaction.atomic
def sync_vacation_periods(periods: Iterable[VacationWindow]) -> int:
    """Replace ELM's read model with the vacation windows from Academic Calendar."""
    supplied = list(periods)
    for period in supplied:
        if period.ends_on < period.starts_on:
            raise ValueError("Vacation period end must be on or after its start.")
        if not period.source_reference or not period.academic_year:
            raise ValueError("Vacation periods require a source reference and academic year.")
    refs = {p.source_reference for p in supplied}
    if len(refs) != len(supplied):
        raise ValueError("Vacation period source references must be unique.")
    for period in supplied:
        VacationPeriod.objects.update_or_create(
            source_reference=period.source_reference,
            defaults={
                "starts_on": period.starts_on,
                "ends_on": period.ends_on,
                "academic_year": period.academic_year,
            },
        )
    VacationPeriod.objects.exclude(source_reference__in=refs).delete()
    return len(supplied)
