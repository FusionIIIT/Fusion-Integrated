"""Extended stay services (CFR-HM-022..024, BW-HM-08/09, CW-HM-04, BR-HM-020..024)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.hostel.domain.constants import (
    ExtendedStayReason,
    ExtendedStayStatus,
    NotificationEventType,
)
from modules.hostel.domain.errors import ValidationError
from modules.hostel.domain.state_machine import EXTENDED_STAY_TRANSITIONS, validate_transition
from modules.hostel.models import ExtendedStayRequest, Hostel
from modules.hostel.services.notification_service import emit_notification


@transaction.atomic
def submit_extended_stay_request(
    student_user_id: int,
    hostel_id: int,
    from_date: date,
    to_date: date,
    reason_type: str = ExtendedStayReason.INTERNSHIP.value,
    reason_details: str = "",
    supporting_document_url: str = "",
) -> ExtendedStayRequest:
    """CFR-HM-022, HM-UC-023: Student submits vacation extended-stay request."""
    if from_date > to_date:
        raise ValidationError("From date cannot be after to date")
    if not reason_details or not reason_details.strip():
        raise ValidationError("Reason details are required")

    hostel = Hostel.objects.get(id=hostel_id)

    return ExtendedStayRequest.objects.create(
        student_user_id=student_user_id,
        hostel=hostel,
        from_date=from_date,
        to_date=to_date,
        reason_type=reason_type,
        reason_details=reason_details.strip(),
        supporting_document_url=supporting_document_url.strip(),
        status=ExtendedStayStatus.PENDING.value,
    )


@transaction.atomic
def decide_extended_stay_request(
    request_id: int,
    decision: str,  # 'approved' or 'rejected'
    warden_user_id: int | None = None,
    charge_amount: Decimal | float = 0.00,
    payment_deadline: date | None = None,
    remarks: str = "",
) -> ExtendedStayRequest:
    """CFR-HM-023, HM-UC-024, BW-HM-08/09, CW-HM-04: Warden reviews extended-stay request."""
    req = ExtendedStayRequest.objects.select_for_update().get(id=request_id)

    validate_transition(
        transitions=EXTENDED_STAY_TRANSITIONS,
        current_status=req.status,
        target_status=decision,
        actor_role="warden",
    )

    req.status = decision
    req.charge_amount = Decimal(str(charge_amount))
    req.payment_deadline = payment_deadline
    req.decided_by_user_id = warden_user_id
    req.decided_at = timezone.now()
    req.decision_remarks = remarks.strip()
    req.save(
        update_fields=[
            "status",
            "charge_amount",
            "payment_deadline",
            "decided_by_user_id",
            "decided_at",
            "decision_remarks",
            "updated_at",
        ]
    )

    emit_notification(
        recipient_user_id=req.student_user_id,
        title=f"Extended Stay Request {decision.capitalize()}",
        message=f"Your extended stay request has been {decision}. Amount: Rs. {req.charge_amount}",
        event_type=NotificationEventType.EXTENDED_STAY_DECIDED,
        link="/hostel/extended-stays",
    )

    return req


@transaction.atomic
def update_extended_stay_compliance(
    request_id: int,
    compliance_status: str,
    remarks: str = "",
) -> ExtendedStayRequest:
    """CFR-HM-024, HM-UC-025, BR-HM-020, 021: Record fee payment or compliance status."""
    req = ExtendedStayRequest.objects.get(id=request_id)
    req.compliance_status = compliance_status
    if remarks:
        req.decision_remarks = f"{req.decision_remarks}\nCompliance: {remarks}".strip()
    req.save(update_fields=["compliance_status", "decision_remarks", "updated_at"])
    return req
