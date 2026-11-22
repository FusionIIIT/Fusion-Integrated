"""Domain services for student no-dues clearance procedures."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from modules.oap.domain.exceptions import OAPDomainError
from modules.oap.models.nodues import (
    DepartmentSignoffStatus,
    DepartmentType,
    NoDuesDepartmentalSignoff,
    NoDuesOverallStatus,
    NoDuesReason,
    NoDuesRequest,
)


@transaction.atomic
def initiate_no_dues(
    student_id: str, reason: str = NoDuesReason.GRADUATION
) -> NoDuesRequest:
    existing = NoDuesRequest.objects.filter(student_id=student_id).first()
    if existing and existing.overall_status == NoDuesOverallStatus.PENDING:
        raise OAPDomainError("A pending no-dues clearance request already exists for this student.")
    if existing and existing.overall_status == NoDuesOverallStatus.CLEARED:
        raise OAPDomainError("Student has already completed and received final no-dues clearance.")

    no_dues = NoDuesRequest.objects.create(
        student_id=student_id, reason=reason, overall_status=NoDuesOverallStatus.PENDING
    )

    # Initialize all department sign-offs
    for dept in DepartmentType.values:
        NoDuesDepartmentalSignoff.objects.create(
            no_dues_request=no_dues,
            department=dept,
            status=DepartmentSignoffStatus.PENDING,
        )
    return no_dues


@transaction.atomic
def record_department_signoff(
    request_id: int,
    department: str,
    status: str,
    signoff_by: str,
    dues_amount: Decimal = Decimal("0.00"),
    remarks: str = "",
) -> NoDuesDepartmentalSignoff:
    signoff = NoDuesDepartmentalSignoff.objects.select_for_update().get(
        no_dues_request_id=request_id, department=department
    )
    signoff.record_signoff(
        status=status,
        signoff_by=signoff_by,
        dues_amount=dues_amount,
        remarks=remarks,
    )
    # Check if this sign-off clears the entire request
    signoff.no_dues_request.check_and_finalize(admin_id=signoff_by)
    return signoff


@transaction.atomic
def finalize_no_dues(request_id: int, admin_id: str) -> bool:
    no_dues = NoDuesRequest.objects.select_for_update().get(pk=request_id)
    return no_dues.check_and_finalize(admin_id=admin_id)
