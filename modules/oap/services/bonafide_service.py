"""Domain services for bonafide certificate requests."""
from __future__ import annotations

from django.db import transaction

from modules.oap.domain.exceptions import OAPDomainError
from modules.oap.models.bonafide import BonafidePurpose, BonafideRequest, BonafideStatus


@transaction.atomic
def submit_bonafide_request(
    student_id: str, purpose: str = BonafidePurpose.GENERAL, details: str = ""
) -> BonafideRequest:
    # Ensure no duplicate pending bonafide request for the same purpose
    if BonafideRequest.objects.filter(
        student_id=student_id, purpose=purpose, status=BonafideStatus.PENDING
    ).exists():
        raise OAPDomainError(
            f"A pending bonafide certificate request for '{purpose}' already exists."
        )

    return BonafideRequest.objects.create(
        student_id=student_id,
        purpose=purpose,
        details=details,
        status=BonafideStatus.PENDING,
    )


@transaction.atomic
def approve_and_issue_bonafide(
    request_id: int, admin_id: str, remarks: str = ""
) -> str:
    req = BonafideRequest.objects.select_for_update().get(pk=request_id)
    return req.approve_and_issue(issued_by=admin_id, remarks=remarks)


@transaction.atomic
def reject_bonafide(request_id: int, admin_id: str, reason: str) -> BonafideRequest:
    req = BonafideRequest.objects.select_for_update().get(pk=request_id)
    req.reject(issued_by=admin_id, reason=reason)
    return req
