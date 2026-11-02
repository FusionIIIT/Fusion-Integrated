"""Hostel fine management services (3.8, CFR-HM-024, BR-HM-025, BR-HM-026)."""

from datetime import date
from decimal import Decimal
from django.db import transaction
from ..domain.constants import FineType
from ..domain.errors import HostelDomainError, MandatoryFieldError
from ..models import Hostel, HostelFine
from .notification_service import create_notification


@transaction.atomic
def record_fine(
    caretaker_user_id: int,
    hostel_id: int,
    student_user_id: int,
    student_roll_number: str,
    student_name: str,
    reason: str,
    amount: Decimal | float | int,
    date_val: date,
    fine_type: str = FineType.RULE_VIOLATION.value,
) -> HostelFine:
    """Caretaker records fine for hostel rule violation or damage (HM-UC-026, BR-HM-025)."""
    # Enforce mandatory fields under BR-HM-025
    if not reason or not reason.strip():
        raise MandatoryFieldError("reason", "BR-HM-025")
    if amount is None or Decimal(str(amount)) <= 0:
        raise MandatoryFieldError("amount", "BR-HM-025")
    if not date_val:
        raise MandatoryFieldError("date", "BR-HM-025")
    if not student_user_id or not student_roll_number.strip():
        raise MandatoryFieldError("student_reference", "BR-HM-025")

    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")

    fine = HostelFine.objects.create(
        hostel=hostel,
        student_user_id=student_user_id,
        student_roll_number=student_roll_number.strip(),
        student_name=student_name.strip(),
        reason=reason.strip(),
        amount=Decimal(str(amount)),
        date=date_val,
        fine_type=fine_type,
        is_paid=False,
        imposed_by_user_id=caretaker_user_id,
    )

    create_notification(
        recipient_user_id=student_user_id,
        event_type="fine_imposed",
        title="Hostel Fine Imposed",
        message=f"A fine of Rs. {amount} has been imposed for: {reason}.",
        reference_id=str(fine.id),
    )

    return fine
