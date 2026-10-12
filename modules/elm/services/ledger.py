"""The leave account. Append-only; corrections are new entries."""
from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, connection, transaction

from modules.elm.domain import categories as c
from modules.elm.domain.policy import Policy
from modules.elm.models import LeaveRequest, LedgerEntry


def lock_employee(user_id: int) -> None:
    """Serialises every balance-affecting write for one person."""
    with connection.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s, %s)", [7301, int(user_id)])


def ensure_annual_credits(user_id: int, kind: str, year: int, policy: Policy) -> None:
    for cat in c.ALL:
        n = policy.annual_credit_for(kind, cat)
        if n <= 0:
            continue
        if LedgerEntry.objects.filter(user_id=user_id, category=cat, year=year,
                                      entry_type=LedgerEntry.ANNUAL_CREDIT).exists():
            continue
        try:
            with transaction.atomic():
                LedgerEntry.objects.create(
                    user_id=user_id, category=cat, year=year, delta=n,
                    entry_type=LedgerEntry.ANNUAL_CREDIT, note=f"{year} annual credit")
        except IntegrityError:
            pass


def post(req: LeaveRequest, entry_type: str, delta: Decimal, note: str = "") -> None:
    if LedgerEntry.objects.filter(request=req, entry_type=entry_type).exists():
        return
    LedgerEntry.objects.create(
        user_id=req.user_id, category=req.category, year=req.start_date.year,
        delta=delta, entry_type=entry_type, request=req, note=note[:300])
