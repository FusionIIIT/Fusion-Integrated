"""Security guard shift schedule services (3.10, CFR-HM-030, BR-HM-028)."""

from datetime import date
from django.db import transaction
from ..domain.constants import ShiftType
from ..domain.errors import HostelDomainError
from ..models import Hostel, SecurityGuardShift


@transaction.atomic
def create_or_update_security_shift(
    warden_user_id: int,
    hostel_id: int,
    guard_name: str,
    shift_date: date,
    shift_type: str = ShiftType.NIGHT.value,
    agency_or_badge_number: str = "",
    gate_or_post: str = "Main Gate",
    contact_number: str = "",
    supervisor_name: str = "",
    shift_id: int | None = None,
) -> SecurityGuardShift:
    """Warden maintains guard shift schedule (HM-UC-030)."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")

    if shift_id:
        shift = SecurityGuardShift.objects.filter(id=shift_id, hostel=hostel).first()
        if not shift:
            raise HostelDomainError(f"Security shift {shift_id} not found.")
        shift.guard_name = guard_name.strip()
        shift.shift_date = shift_date
        shift.shift_type = shift_type
        shift.agency_or_badge_number = agency_or_badge_number.strip()
        shift.gate_or_post = gate_or_post.strip()
        shift.contact_number = contact_number.strip()
        shift.supervisor_name = supervisor_name.strip()
        shift.save()
        return shift
    else:
        return SecurityGuardShift.objects.create(
            hostel=hostel,
            guard_name=guard_name.strip(),
            agency_or_badge_number=agency_or_badge_number.strip(),
            shift_type=shift_type,
            shift_date=shift_date,
            gate_or_post=gate_or_post.strip(),
            contact_number=contact_number.strip(),
            supervisor_name=supervisor_name.strip(),
            is_verified=True,
            created_by_user_id=warden_user_id,
        )
