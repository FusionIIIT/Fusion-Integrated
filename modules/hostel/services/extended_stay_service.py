"""Extended-stay management for vacations/semester breaks (3.7, CFR-HM-020, BR-HM-020..024, CW-HM-04)."""

from datetime import date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from ..domain.constants import ExtendedStayStatus, PaymentComplianceStatus
from ..domain.errors import HostelDomainError, InactiveHostelError
from ..domain.state_machine import WorkflowStateMachine
from ..models import ExtendedStayRequest, Hostel
from .notification_service import create_notification


@transaction.atomic
def submit_extended_stay_request(
    student_user_id: int,
    student_roll_number: str,
    student_name: str,
    hostel_id: int,
    stay_reason: str,
    start_date: date,
    end_date: date,
    remarks: str = "",
) -> ExtendedStayRequest:
    """Student submits extended stay request for vacation or break (HM-UC-023)."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")
    if not hostel.is_active:
        raise InactiveHostelError(hostel.name)
    if start_date > end_date:
        raise HostelDomainError("Extended stay start date cannot be after end date.", code="invalid_dates")

    req = ExtendedStayRequest.objects.create(
        hostel=hostel,
        student_user_id=student_user_id,
        student_roll_number=student_roll_number.strip(),
        student_name=student_name.strip(),
        stay_reason=stay_reason,
        start_date=start_date,
        end_date=end_date,
        remarks=remarks.strip(),
        status=ExtendedStayStatus.SUBMITTED.value,
        payment_status=PaymentComplianceStatus.PENDING.value,
    )

    create_notification(
        recipient_user_id=student_user_id,
        event_type="extended_stay_submitted",
        title="Extended Stay Request Submitted",
        message=f"Your vacation extended stay request ({start_date} to {end_date}) is submitted for Warden review.",
        reference_id=str(req.id),
    )
    return req


@transaction.atomic
def record_extended_stay_decision(
    warden_user_id: int,
    request_id: int,
    decision: str,  # 'approved' or 'rejected'
    remarks: str = "",
) -> ExtendedStayRequest:
    """Warden reviews and records approval or rejection (HM-UC-024, CW-HM-04, BW-HM-08/09)."""
    req = ExtendedStayRequest.objects.select_for_update().select_related("hostel").filter(id=request_id).first()
    if not req:
        raise HostelDomainError(f"Extended stay request {request_id} not found.", code="not_found")

    WorkflowStateMachine.validate_extended_stay_transition(req.status, decision)

    req.status = decision
    req.decision_by_user_id = warden_user_id
    req.decision_at = timezone.now()
    req.decision_remarks = remarks.strip()
    req.save()

    create_notification(
        recipient_user_id=req.student_user_id,
        event_type=f"extended_stay_{decision}",
        title=f"Extended Stay Request {decision.capitalize()}",
        message=f"Your extended-stay request for {req.hostel.name} has been {decision}.",
        reference_id=str(req.id),
    )

    return req


@transaction.atomic
def record_charge_and_compliance(
    request_id: int,
    charge_amount: Decimal | float | int,
    payment_deadline: date | None = None,
    payment_status: str | None = None,
) -> ExtendedStayRequest:
    """Record extended stay charge, payment deadline, or compliance (HM-UC-025, BR-HM-020, BR-HM-021)."""
    req = ExtendedStayRequest.objects.select_for_update().filter(id=request_id).first()
    if not req:
        raise HostelDomainError(f"Extended stay request {request_id} not found.", code="not_found")

    req.charge_amount = Decimal(str(charge_amount))
    if payment_deadline:
        req.payment_deadline = payment_deadline
    if payment_status:
        req.payment_status = payment_status
    req.save()

    create_notification(
        recipient_user_id=req.student_user_id,
        event_type="extended_stay_compliance_updated",
        title="Extended Stay Fee & Compliance Updated",
        message=f"Fee: Rs. {req.charge_amount}, Deadline: {req.payment_deadline}, Status: {req.payment_status}.",
        reference_id=str(req.id),
    )

    return req
