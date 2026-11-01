"""mess's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from modules.mess.models import (
    DeregistrationRequest,
    MonthlyBill,
    RegistrationRequest,
)


@dataclass(frozen=True)
class MessStatusDTO:
    user_id: int
    is_registered: bool


def get_mess_status(user_ids: Sequence[int]) -> dict[int, MessStatusDTO]:
    """Registered = an APPROVED registration and no EFFECTIVE deregistration."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    approved = set(RegistrationRequest.objects
                   .filter(user_id__in=ids, status="APPROVED")
                   .values_list("user_id", flat=True))
    left = set(DeregistrationRequest.objects
               .filter(user_id__in=ids, status="EFFECTIVE")
               .values_list("user_id", flat=True))
    return {uid: MessStatusDTO(uid, uid in approved and uid not in left)
            for uid in ids}


@dataclass(frozen=True)
class MessDuesDTO:
    """Outstanding balance = sum of PUBLISHED bills (payments are outside MMS)."""

    user_id: int
    outstanding: Decimal


def get_outstanding_dues(user_ids: Sequence[int]) -> dict[int, MessDuesDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = (MonthlyBill.objects
            .filter(user_id__in=ids, status="PUBLISHED")
            .values("user_id").annotate(total=Sum("total_amount")))
    totals = {r["user_id"]: r["total"] for r in rows}
    return {uid: MessDuesDTO(uid, totals.get(uid) or Decimal("0"))
            for uid in ids}
