"""The published holiday and vacation calendar that date rules read (BR-EL-030/031)."""
from __future__ import annotations

from typing import Any

from django.db import transaction

from modules.elm.models import ClosedHoliday, RestrictedHoliday, VacationPeriod
from modules.elm.services.common import require_permission

P_ADMINISTER = "elm.leave.administer"


@transaction.atomic
def add_entry(principal, data: dict[str, Any]):
    require_permission(principal, P_ADMINISTER)
    kind = data["kind"]
    if kind == "restricted":
        entry, _ = RestrictedHoliday.objects.update_or_create(
            date=data["date"], defaults={"name": data["name"], "year": data["date"].year,
                                         "is_published": True})
    elif kind == "closed":
        entry, _ = ClosedHoliday.objects.update_or_create(
            date=data["date"], defaults={"name": data["name"], "is_published": True})
    else:
        entry = VacationPeriod.objects.create(
            name=data["name"], start_date=data["start_date"], end_date=data["end_date"])
    return entry
