"""Public cross-module contract for MMS. Plural signatures only."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from modules.mms.models import MessRegistration, MessBill
from modules.mms.domain import state_machine as sm


@dataclass(frozen=True)
class StudentMessStatusDTO:
    user_id: int
    is_registered: bool
    active_registration_id: int | None


def get_student_mess_statuses(user_ids: Sequence[int]) -> dict[int, StudentMessStatusDTO]:
    """Returns mess registration status for multiple users."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    registrations = MessRegistration.objects.filter(
        user_id__in=ids,
        status=sm.REG_APPROVED,
    )
    reg_map = {r.user_id: r.pk for r in registrations}

    result = {}
    for uid in ids:
        reg_id = reg_map.get(uid)
        result[uid] = StudentMessStatusDTO(
            user_id=uid,
            is_registered=(reg_id is not None),
            active_registration_id=reg_id,
        )
    return result


@dataclass(frozen=True)
class StudentMessBillDTO:
    user_id: int
    total_billed: Decimal
    total_outstanding: Decimal


def get_student_mess_bills(user_ids: Sequence[int]) -> dict[int, StudentMessBillDTO]:
    """Returns monthly bill summaries for multiple users."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    result = {}
    for uid in ids:
        bills = MessBill.objects.filter(user_id=uid, status=sm.BILL_PUBLISHED)
        total = sum((b.total_amount for b in bills), Decimal("0.00"))
        result[uid] = StudentMessBillDTO(
            user_id=uid,
            total_billed=total,
            total_outstanding=total,
        )
    return result
