"""Blacklist matching and verification service (BR-001, BR-004, BR-011, BR-024)."""
from django.utils import timezone

from modules.vms.models.access import GateAlert
from modules.vms.models.visitors import BlacklistRecord, Visitor
from modules.vms.services.exceptions import BlacklistMatchException


def check_blacklist(phone: str, id_number: str = "", visitor: Visitor | None = None) -> bool:
    """Checks whether the applicant matches any active blacklist record.

    Enforces BR-001: Exact match on phone or ID number only; no partial matches.
    Enforces BR-004 & BR-024: If hit, raises BlacklistMatchException and logs critical alert.
    """
    clean_phone = phone.strip()
    clean_id = id_number.strip() if id_number else ""

    qs = BlacklistRecord.objects.filter(is_active=True)

    matched_record = None
    if clean_phone and qs.filter(phone=clean_phone).exists():
        matched_record = qs.filter(phone=clean_phone).first()
    elif clean_id and qs.filter(id_number=clean_id).exists():
        matched_record = qs.filter(id_number=clean_id).first()

    if matched_record:
        # BR-004: Trigger critical GateAlert on blacklist match
        GateAlert.objects.create(
            alert_type="blacklist_hit",
            severity="critical",
            status="open",
            visitor=visitor,
            details=(
                f"Blacklist hit detected for {matched_record.full_name} "
                f"(Phone: {clean_phone}, ID: {clean_id}). Reason: {matched_record.reason}"
            ),
        )
        raise BlacklistMatchException(
            f"Registration blocked: Visitor is blacklisted ({matched_record.reason}).",
            rule_id="BR-004",
        )
    return False


def add_to_blacklist(
    full_name: str,
    phone: str,
    id_number: str,
    reason: str,
    added_by_user_id: int,
) -> BlacklistRecord:
    """Adds a prohibited individual to the blacklist registry."""
    record, _ = BlacklistRecord.objects.update_or_create(
        phone=phone.strip(),
        id_number=id_number.strip(),
        defaults={
            "full_name": full_name.strip(),
            "reason": reason.strip(),
            "added_by_user_id": added_by_user_id,
            "is_active": True,
            "updated_at": timezone.now(),
        },
    )
    return record


def remove_from_blacklist(record_id: int) -> bool:
    """Deactivates a blacklist record."""
    record = BlacklistRecord.objects.filter(id=record_id).first()
    if record:
        record.is_active = False
        record.save()
        return True
    return False
