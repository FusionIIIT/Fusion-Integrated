"""Domain services for undergraduate branch change procedures."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from modules.oap.domain.exceptions import OAPDomainError
from modules.oap.domain.validators import validate_branch_change_eligibility
from modules.oap.models.branch_change import BranchChangeRequest, BranchChangeStatus


@transaction.atomic
def submit_branch_change(
    student_id: str,
    current_branch: str,
    preferred_branch_1: str,
    preferred_branch_2: str | None = None,
    current_cpi: Decimal = Decimal("0.00"),
    credits_completed: int = 0,
    has_backlogs: bool = False,
) -> BranchChangeRequest:
    if BranchChangeRequest.objects.filter(student_id=student_id).exists():
        raise OAPDomainError(
            "A branch change application has already been recorded for this student."
        )

    validate_branch_change_eligibility(current_cpi, credits_completed, has_backlogs)

    return BranchChangeRequest.objects.create(
        student_id=student_id,
        current_branch=current_branch,
        preferred_branch_1=preferred_branch_1,
        preferred_branch_2=preferred_branch_2,
        current_cpi=current_cpi,
        credits_completed=credits_completed,
        has_backlogs=has_backlogs,
        status=BranchChangeStatus.SUBMITTED,
    )


@transaction.atomic
def verify_branch_change(request_id: int) -> bool:
    req = BranchChangeRequest.objects.select_for_update().get(pk=request_id)
    return req.verify_eligibility()


@transaction.atomic
def allocate_and_sanction(
    request_id: int, allocated_branch: str, approved_by: str
) -> BranchChangeRequest:
    req = BranchChangeRequest.objects.select_for_update().get(pk=request_id)
    if req.status == BranchChangeStatus.SUBMITTED:
        req.verify_eligibility()
    req.allocate_seat(allocated_branch=allocated_branch)
    req.sanction(
        approved_by=approved_by,
        remarks=f"Allocated to {allocated_branch} based on CPI merit ranking.",
    )
    return req
