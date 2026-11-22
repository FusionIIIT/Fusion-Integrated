"""Domain services for student leave lifecycle."""
from __future__ import annotations

import datetime

from django.db import transaction

from modules.oap.domain.exceptions import OAPDomainError
from modules.oap.domain.validators import validate_leave_dates, validate_medical_certificate
from modules.oap.models.leave import RequestStatus, StudentLeaveRequest


@transaction.atomic
def submit_leave_application(
    student_id: str,
    student_name: str,
    leave_type: str,
    start_date: datetime.date,
    end_date: datetime.date,
    reason: str,
    document_url: str | None = None,
) -> StudentLeaveRequest:
    validate_leave_dates(start_date, end_date)
    duration_days = (end_date - start_date).days + 1
    validate_medical_certificate(leave_type, duration_days, document_url)

    # Disallow overlapping approved/pending leaves
    overlapping = StudentLeaveRequest.objects.filter(
        student_id=student_id,
        status__in=[RequestStatus.PENDING, RequestStatus.RECOMMENDED, RequestStatus.APPROVED],
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists()
    if overlapping:
        msg = "An active or approved leave application already exists for this date range."
        raise OAPDomainError(msg)

    return StudentLeaveRequest.objects.create(
        student_id=student_id,
        student_name=student_name,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        document_url=document_url or "",
        status=RequestStatus.PENDING,
    )


@transaction.atomic
def recommend_leave(request_id: int, supervisor_id: str, remarks: str = "") -> StudentLeaveRequest:
    leave = StudentLeaveRequest.objects.select_for_update().get(pk=request_id)
    leave.recommend(supervisor_id=supervisor_id, remarks=remarks)
    return leave


@transaction.atomic
def hod_approve_leave(request_id: int, hod_id: str, remarks: str = "") -> StudentLeaveRequest:
    leave = StudentLeaveRequest.objects.select_for_update().get(pk=request_id)
    leave.hod_approve(hod_id=hod_id, remarks=remarks)
    return leave


@transaction.atomic
def hod_reject_leave(request_id: int, hod_id: str, remarks: str = "") -> StudentLeaveRequest:
    leave = StudentLeaveRequest.objects.select_for_update().get(pk=request_id)
    leave.hod_reject(hod_id=hod_id, remarks=remarks)
    return leave


@transaction.atomic
def cancel_leave(request_id: int, student_id: str) -> StudentLeaveRequest:
    leave = StudentLeaveRequest.objects.select_for_update().get(pk=request_id)
    if leave.student_id != student_id:
        raise OAPDomainError("Students can only cancel their own leave requests.")
    leave.cancel()
    return leave
