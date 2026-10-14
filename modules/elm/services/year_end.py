"""Year-end leave processing service (SF-EL-001, BR-EL-002..009)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.elm.domain import categories as c
from modules.elm.domain.year_end import vl_to_el
from modules.elm.models import LedgerEntry, YearEndRun
from modules.elm.selectors.config import effective_policy


@transaction.atomic
def run(year: int) -> YearEndRun:
    existing = YearEndRun.objects.filter(year=year).first()
    if existing:
        return existing

    run_rec = YearEndRun.objects.create(year=year)
    _, policy = effective_policy(date(year, 12, 31))
    ratio = policy.vl_to_el_ratio if policy else Decimal("2")

    user_ids = sorted(
        set(LedgerEntry.objects.filter(year__lte=year).values_list("user_id", flat=True))
    )
    for uid in user_ids:
        for cat in c.LAPSING:
            bal = _balance(uid, cat, year)
            if bal > 0:
                LedgerEntry.objects.get_or_create(
                    user_id=uid,
                    category=cat,
                    year=year,
                    entry_type=LedgerEntry.LAPSE,
                    defaults={"delta": -bal, "note": f"{year} year-end lapse"},
                )
        vl_bal = _balance(uid, c.VL, year)
        if vl_bal > 0:
            converted = vl_to_el(vl_bal, ratio)
            LedgerEntry.objects.get_or_create(
                user_id=uid,
                category=c.VL,
                year=year,
                entry_type=LedgerEntry.CONVERSION_OUT,
                defaults={"delta": -vl_bal, "note": f"{year} VL conversion"},
            )
            if converted > 0:
                LedgerEntry.objects.get_or_create(
                    user_id=uid,
                    category=c.EL,
                    year=year,
                    entry_type=LedgerEntry.CONVERSION_IN,
                    defaults={"delta": converted, "note": f"{year} VL->EL conversion"},
                )

    run_rec.employees = len(user_ids)
    run_rec.finished_at = timezone.now()
    run_rec.save(update_fields=["employees", "finished_at"])
    return run_rec


def _balance(user_id: int, category: str, up_to_year: int) -> Decimal:
    from django.db.models import Sum

    total = (
        LedgerEntry.objects.filter(user_id=user_id, category=category, year__lte=up_to_year)
        .aggregate(s=Sum("delta"))["s"]
    )
    return total or Decimal("0")
