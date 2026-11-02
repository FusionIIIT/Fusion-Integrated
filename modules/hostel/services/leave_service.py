"""Hostel leave management services (3.4, CFR-HM-011, BR-HM-013, CW-HM-01)."""

from datetime import date
from django.db import transaction
from django.utils import timezone
from ..domain.constants import AttendanceStatus, LeaveStatus
from ..domain.errors import HostelDomainError, InactiveHostelError
from ..domain.state_machine import WorkflowStateMachine
from ..models import AttendanceRecord, Hostel, LeaveRequest
from .notification_service import create_notification


@transaction.atomic
def submit_leave_request(
    student_user_id: int,
    student_roll_number: str,
    student_name: str,
    hostel_id: int,
    leave_type: str,
    start_date: date,
    end_date: date,
    reason: str,
    address_during_leave: str = "",
    emergency_contact: str = "",
    supporting_document: str = "",
) -> LeaveRequest:
    """Student submits leave request (HM-UC-014)."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")
    if not hostel.is_active:
        raise InactiveHostelError(hostel.name)
    if start_date > end_date:
        raise HostelDomainError("Leave start date cannot be after end date.", code="invalid_dates")

    req = LeaveRequest.objects.create(
        hostel=hostel,
        student_user_id=student_user_id,
        student_roll_number=student_roll_number.strip(),
        student_name=student_name.strip(),
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason.strip(),
        address_during_leave=address_during_leave.strip(),
        emergency_contact=emergency_contact.strip(),
        supporting_document=supporting_document.strip(),
        status=LeaveStatus.SUBMITTED.value,
    )

    create_notification(
        recipient_user_id=student_user_id,
        event_type="leave_submitted",
        title="Leave Request Submitted",
        message=f"Your {leave_type} leave request ({start_date} to {end_date}) has been submitted.",
        reference_id=str(req.id),
    )
    return req


@transaction.atomic
def record_leave_decision(
    caretaker_user_id: int,
    request_id: int,
    decision: str,  # 'approved' or 'rejected'
    remarks: str = "",
) -> LeaveRequest:
    """Caretaker approves or rejects leave request (HM-UC-015, CW-HM-01, BW-HM-02/03)."""
    req = LeaveRequest.objects.select_for_update().select_related("hostel").filter(id=request_id).first()
    if not req:
        raise HostelDomainError(f"Leave request {request_id} not found.", code="not_found")

    WorkflowStateMachine.validate_leave_transition(req.status, decision)

    req.status = decision
    req.decision_by_user_id = caretaker_user_id
    req.decision_at = timezone.now()
    req.decision_remarks = remarks.strip()
    req.save()

    # If approved, update or prefill attendance as on_leave for that period if today is within range
    if decision == LeaveStatus.APPROVED.value:
        today = date.today()
        if req.start_date <= today <= req.end_date:
            AttendanceRecord.objects.update_or_create(
                hostel=req.hostel,
                student_user_id=req.student_user_id,
                date=today,
                defaults={
                    "student_roll_number": req.student_roll_number,
                    "student_name": req.student_name,
                    "status": AttendanceStatus.ON_LEAVE.value,
                    "marked_by_user_id": caretaker_user_id,
                    "remarks": f"Approved leave #{req.id}",
                },
            )

    create_notification(
        recipient_user_id=req.student_user_id,
        event_type=f"leave_{decision}",
        title=f"Leave Request {decision.capitalize()}",
        message=f"Your leave request from {req.start_date} to {req.end_date} has been {decision}.",
        reference_id=str(req.id),
    )

    return req
