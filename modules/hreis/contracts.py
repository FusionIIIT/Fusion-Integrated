"""HR-EIS's read-only inter-module public contract.

These batched projections expose only the minimum records needed by other
trusted Fusion modules. No caller receives forms, medical reasons, review notes,
attachment references or service-history content.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from modules.hreis.models import EmployeeServiceRecord, HRRequest, LeaveLedgerEntry


@dataclass(frozen=True)
class EmployeeServiceSummaryDTO:
    user_id: int
    department: str
    designation: str
    retirement_status: str


@dataclass(frozen=True)
class RequestStatusDTO:
    request_id: int
    family: str
    state: str


@dataclass(frozen=True)
class ApprovedClaimStatusDTO:
    request_id: int
    family: str
    state: str
    externally_reported_payment_status: str | None


def _positive_ids(values: Sequence[int]) -> set[int]:
    return {value for value in values if type(value) is int and value > 0}


def get_employee_service_summaries(
    user_ids: Sequence[int],
) -> dict[int, EmployeeServiceSummaryDTO]:
    ids = _positive_ids(user_ids)
    if not ids:
        return {}
    return {
        row.user_id: EmployeeServiceSummaryDTO(
            user_id=row.user_id,
            department=row.department,
            designation=row.designation_snapshot,
            retirement_status=row.retirement_status,
        )
        for row in EmployeeServiceRecord.objects.filter(user_id__in=ids)
    }


def get_employee_leave_balances(
    user_ids: Sequence[int], leave_type: str
) -> dict[int, Decimal]:
    from modules.hreis.domain.leave import LEAVE_TYPES

    if leave_type not in LEAVE_TYPES:
        raise ValueError("A supported leave type is required.")
    ids = _positive_ids(user_ids)
    if not ids:
        return {}
    balances = {uid: Decimal("0") for uid in ids}
    for row in (
        LeaveLedgerEntry.objects.filter(user_id__in=ids, leave_type=leave_type)
        .values("user_id")
        .annotate(total=Sum("quantity"))
    ):
        balances[row["user_id"]] = row["total"]
    return balances


def get_request_statuses(
    request_ids: Sequence[int],
) -> dict[int, RequestStatusDTO]:
    ids = _positive_ids(request_ids)
    if not ids:
        return {}
    return {
        row.pk: RequestStatusDTO(
            request_id=row.pk, family=row.family, state=row.state
        )
        for row in HRRequest.objects.filter(pk__in=ids)
    }


def get_approved_claim_statuses(
    request_ids: Sequence[int],
) -> dict[int, ApprovedClaimStatusDTO]:
    ids = _positive_ids(request_ids)
    if not ids:
        return {}
    rows = HRRequest.objects.filter(
        pk__in=ids, family__in=("ltc", "cpda"),
        state__in=("approved", "financial_processing_recorded"),
    ).select_related("claim")
    return {
        row.pk: ApprovedClaimStatusDTO(
            request_id=row.pk,
            family=row.family,
            state=row.state,
            externally_reported_payment_status=(
                row.claim.financial_processing_details.get("payment_status")
                if row.state == "financial_processing_recorded" else None
            ),
        )
        for row in rows
    }
