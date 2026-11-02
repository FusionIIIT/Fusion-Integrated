"""Hostel security guard scheduling services (CFR-HM-029, HM-UC-030, BR-HM-028)."""

from __future__ import annotations

from datetime import date

from django.db import transaction

from modules.hostel.domain.constants import SecurityShiftType
from modules.hostel.domain.errors import ValidationError
from modules.hostel.models import Hostel, SecurityShift


@transaction.atomic
def schedule_security_shift(
    hostel_id: int,
    guard_name: str,
    shift_date: date,
    shift_type: str = SecurityShiftType.MORNING.value,
    gate_location: str = "Main Gate",
) -> SecurityShift:
    """CFR-HM-029, HM-UC-030: Warden maintains security guard shift schedule."""
    if not guard_name or not guard_name.strip():
        raise ValidationError("Guard name is required")

    hostel = Hostel.objects.get(id=hostel_id)

    return SecurityShift.objects.create(
        hostel=hostel,
        guard_name=guard_name.strip(),
        shift_date=shift_date,
        shift_type=shift_type,
        gate_location=gate_location.strip(),
        status="scheduled",
    )
