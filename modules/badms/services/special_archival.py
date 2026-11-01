"""Special offline archival domain service for BADMS."""
from __future__ import annotations

import hashlib
from django.utils import timezone
from modules.badms.models import SpecialArchivalRecord
from modules.badms.services.audit import record_audit
from modules.badms.services.notifications import send_notification


class SpecialArchivalError(Exception):
    """Raised when offline special archival validation or execution fails."""
    pass


def record_special_archival(
    *,
    performer_id: int,
    performer_role: str,
    payload: dict,
) -> SpecialArchivalRecord:
    """Record an offline special archival operation performed for Sensitive research data.

    Business constraints:
    - Any authority can request offline special archival.
    - Only Super Admin performs special archival in the system.
    - Record the outcome and immutable audit event.
    - This is NOT an online approval workflow.
    """
    requester_name = (payload.get("requester_name") or "").strip()
    if not requester_name:
        raise SpecialArchivalError("Requester name is required for special archival.")

    requester_designation = (payload.get("requester_designation") or "").strip()
    if not requester_designation:
        raise SpecialArchivalError("Requester designation/authority is required.")

    dataset_title = (payload.get("dataset_title") or "").strip()
    if not dataset_title:
        raise SpecialArchivalError("Dataset title is required.")

    offline_media_type = (payload.get("offline_media_type") or "").strip()
    if not offline_media_type:
        raise SpecialArchivalError("Offline media type (e.g. LTO-8 Tape, Optical M-DISC) is required.")

    media_serial_number = (payload.get("media_serial_number") or "").strip()
    if not media_serial_number:
        raise SpecialArchivalError("Physical media serial number or volume label is required.")

    storage_vault_location = (payload.get("storage_vault_location") or "").strip()
    if not storage_vault_location:
        raise SpecialArchivalError("Air-gapped storage vault location is required.")

    checksum = (payload.get("checksum") or "").strip()
    if not checksum:
        digest_input = f"{dataset_title}-{media_serial_number}-{timezone.now().isoformat()}"
        checksum = hashlib.sha256(digest_input.encode()).hexdigest()

    record = SpecialArchivalRecord.objects.create(
        requester_name=requester_name,
        requester_designation=requester_designation,
        dataset_title=dataset_title,
        classification=payload.get("classification") or "Sensitive Research Data",
        offline_media_type=offline_media_type,
        media_serial_number=media_serial_number,
        storage_vault_location=storage_vault_location,
        performed_by_user_id=performer_id,
        notes=(payload.get("notes") or "").strip(),
        checksum=checksum,
        completed_at=timezone.now(),
    )

    # Immutable audit event
    record_audit(
        actor_user_id=performer_id,
        actor_role=performer_role,
        action="badms.archive.special",
        target_type="special_archive",
        target_id=record.pk,
        outcome="success",
        details={
            "dataset_title": record.dataset_title,
            "offline_media_type": record.offline_media_type,
            "media_serial_number": record.media_serial_number,
            "storage_vault_location": record.storage_vault_location,
            "requester_name": record.requester_name,
            "requester_designation": record.requester_designation,
            "checksum": record.checksum,
        },
    )

    # Notify IT Security
    send_notification(
        user_id=0,
        recipient_role="IT Security",
        subject=f"Offline Special Archival Completed: {record.dataset_title}",
        message=(
            f"Super Admin has completed offline special archival for sensitive research data "
            f"'{record.dataset_title}'. Deposited on {record.offline_media_type} "
            f"(Serial #{record.media_serial_number}) at {record.storage_vault_location}."
        ),
        notification_type="special_archival_completed",
        related_object_id=record.pk,
    )

    return record
