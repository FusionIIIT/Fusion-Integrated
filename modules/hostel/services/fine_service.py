"""Fine recording services (CFR-HM-025..027, HM-UC-026, 027, 038, BR-HM-025, 026)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.hostel.domain.constants import FineStatus, NotificationEventType
from modules.hostel.domain.errors import ValidationError
from modules.hostel.models import Hostel, HostelFine
from modules.hostel.services.notification_service import emit_notification


@transaction.atomic
def record_fine(
    student_user_id: int,
    hostel_id: int,
    amount: Decimal | float,
    reason: str,
    issued_date: date | None = None,
    due_date: date | None = None,
    imposed_by_user_id: int | None = None,
    remarks: str = "",
) -> HostelFine:
    """CFR-HM-025, HM-UC-026, BR-HM-025: Caretaker/Warden records disciplinary fine."""
    # BR-HM-025 mandatory fields: student, amount, reason, date
    if not student_user_id:
        raise ValidationError("Student is mandatory for fine imposition (BR-HM-025)")
    if amount is None or Decimal(str(amount)) <= 0:
        raise ValidationError("Fine amount must be greater than zero (BR-HM-025)")
    if not reason or not reason.strip():
        raise ValidationError("Reason is mandatory for fine imposition (BR-HM-025)")

    hostel = Hostel.objects.get(id=hostel_id)
    issued = issued_date or timezone.now().date()

    fine = HostelFine.objects.create(
        student_user_id=student_user_id,
        hostel=hostel,
        amount=Decimal(str(amount)),
        reason=reason.strip(),
        issued_date=issued,
        due_date=due_date,
        status=FineStatus.PENDING.value,
        imposed_by_user_id=imposed_by_user_id,
        remarks=remarks.strip(),
    )

    emit_notification(
        recipient_user_id=student_user_id,
        title="Hostel Fine Imposed",
        message=f"A disciplinary fine of Rs. {fine.amount} has been issued: {fine.reason}",
        event_type=NotificationEventType.FINE_ISSUED,
        link="/hostel/fines",
    )

    return fine


@transaction.atomic
def update_fine_status(
    fine_id: int,
    status: str,  # 'paid' or 'waived'
    receipt_reference: str = "",
    remarks: str = "",
) -> HostelFine:
    """CFR-HM-026: Update fine payment or waiver status."""
    if status == FineStatus.PAID.value and (not receipt_reference or not receipt_reference.strip()):
        raise ValidationError("Receipt reference is mandatory to mark fine as paid (BR-HM-026)")
    fine = HostelFine.objects.get(id=fine_id)
    fine.status = status
    if receipt_reference:
        fine.receipt_reference = receipt_reference.strip()
    if remarks:
        fine.remarks = f"{fine.remarks}\nStatus update: {remarks}".strip()
    fine.save(update_fields=["status", "receipt_reference", "remarks", "updated_at"])
    return fine
