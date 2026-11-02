"""Visitor registration and identity service (BR-009, BR-015, BR-017, BR-020, BR-035)."""
from django.utils import timezone

from modules.vms.models.visitors import SafeListRecord, Visitor
from modules.vms.models.visits import VisitPass
from modules.vms.services.blacklist_service import check_blacklist
from modules.vms.services.exceptions import DuplicatePassException


def register_visitor(
    full_name: str,
    phone: str,
    email: str = "",
    identity_type: str = "aadhaar",
    id_number: str = "",
    organization: str = "",
) -> Visitor:
    """Registers or updates a visitor profile.

    Enforces BR-011 & BR-024: Immediate blacklist verification.
    """
    clean_phone = phone.strip()
    clean_id = id_number.strip()

    # Blacklist check throws BlacklistMatchException on hit
    check_blacklist(phone=clean_phone, id_number=clean_id)

    visitor, _ = Visitor.objects.update_or_create(
        phone=clean_phone,
        defaults={
            "full_name": full_name.strip(),
            "email": email.strip().lower(),
            "identity_type": identity_type,
            "id_number": clean_id,
            "organization": organization.strip(),
            "is_active": True,
        },
    )
    return visitor


def check_same_day_duplicate_pass(visitor: Visitor, target_date: timezone.datetime | None = None) -> None:
    """Validates that visitor does not already hold an active pass for the same calendar date.

    Enforces BR-017 & BR-020: No duplicate pass for same visitor on same day.
    """
    check_date = target_date or timezone.now()
    start_of_day = check_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = check_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    existing_pass = VisitPass.objects.filter(
        visitor=visitor,
        status="active",
        valid_from__lte=end_of_day,
        valid_to__gte=start_of_day,
    ).first()

    if existing_pass:
        raise DuplicatePassException(
            f"Visitor '{visitor.full_name}' already possesses an active pass (#{existing_pass.pass_number}) for today.",
            rule_id="BR-020",
        )


def check_safelist_status(phone: str, id_number: str = "") -> SafeListRecord | None:
    """Checks if a visitor is on the pre-approved safe-list.

    Enforces BR-009 & BR-015: Safe-listed visitor has NO implicit zone access;
    must be issued an explicit pass.
    """
    now = timezone.now()
    clean_phone = phone.strip()
    clean_id = id_number.strip()

    qs = SafeListRecord.objects.filter(is_active=True, valid_until__gte=now)
    if clean_phone and qs.filter(phone=clean_phone).exists():
        return qs.filter(phone=clean_phone).first()
    if clean_id and qs.filter(id_number=clean_id).exists():
        return qs.filter(id_number=clean_id).first()
    return None


def get_anonymized_visitor_record(visitor: Visitor) -> dict:
    """Returns privacy-compliant anonymized view of a visitor record for reporting."""
    masked_phone = f"{visitor.phone[:2]}******{visitor.phone[-2:]}" if len(visitor.phone) >= 4 else "***"
    masked_email = f"{visitor.email[:2]}***@***" if "@" in visitor.email else "***"
    return {
        "visitor_id": visitor.id,
        "masked_name": f"{visitor.full_name[:1]}*** {visitor.full_name.split()[-1][:1]}***",
        "masked_phone": masked_phone,
        "masked_email": masked_email,
        "organization": visitor.organization,
        "identity_type": visitor.identity_type,
    }
