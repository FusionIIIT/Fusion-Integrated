"""IAA's public contract surface. Plural by signature."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from modules.iaa.models import ExpenseVoucherRequest, TAClaim


@dataclass(frozen=True)
class RequestStatusDTO:
    request_id: int
    user_id: int
    department: str
    request_type: str
    total_amount: Decimal
    status: str


@dataclass(frozen=True)
class TAClaimStatusDTO:
    claim_id: int
    user_id: int
    department: str
    claimed_amount: Decimal
    status: str


def get_request_statuses(request_ids: Sequence[int]) -> dict[int, RequestStatusDTO]:
    ids = {int(i) for i in request_ids if i is not None}
    if not ids:
        return {}
    rows = ExpenseVoucherRequest.objects.filter(id__in=ids)
    return {
        r.id: RequestStatusDTO(
            request_id=r.id,
            user_id=r.user_id,
            department=r.department,
            request_type=r.request_type,
            total_amount=r.total_amount,
            status=r.status,
        )
        for r in rows
    }


def get_travel_statuses(claim_ids: Sequence[int]) -> dict[int, TAClaimStatusDTO]:
    ids = {int(i) for i in claim_ids if i is not None}
    if not ids:
        return {}
    rows = TAClaim.objects.filter(id__in=ids)
    return {
        c.id: TAClaimStatusDTO(
            claim_id=c.id,
            user_id=c.user_id,
            department=c.department,
            claimed_amount=c.claimed_amount,
            status=c.status,
        )
        for c in rows
    }
