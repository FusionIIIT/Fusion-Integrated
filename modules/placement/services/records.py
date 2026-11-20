"""TPO maintenance of placement records (PC-UC-010, PC-BR-029, PC-AFR-031, PC-AFR-032)."""
from __future__ import annotations

import logging

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.placement.models import PlacementRecord, PlacementRecordRevision
from modules.placement.services.authz import require

log = logging.getLogger("fusion.placement.records")

P_MANAGE = "placement.record.manage"
CORRECTABLE = ("ctc_lpa", "kind", "is_active")


def _snapshot(record: PlacementRecord) -> dict:
    return {"ctc_lpa": None if record.ctc_lpa is None else str(record.ctc_lpa),
            "kind": record.kind, "is_active": record.is_active}


@transaction.atomic
def correct(*, record_id: int, actor, reason: str, **changes) -> PlacementRecord:
    """Apply a TPO correction and keep what the record said before (PC-BR-024)."""
    require(actor, P_MANAGE)
    record = (PlacementRecord.objects.select_for_update()
              .filter(pk=record_id).select_related("company", "policy").first())
    if record is None:
        raise NotFoundError("No such placement record.")
    before = _snapshot(record)
    for field in CORRECTABLE:
        if field in changes:
            setattr(record, field, changes[field])
    after = _snapshot(record)
    if after == before:
        raise ConflictError("The record already holds these values.",
                            code="nothing_changed")
    if after["is_active"] and not before["is_active"] and PlacementRecord.objects.filter(
            user_id=record.user_id, policy_id=record.policy_id,
            is_active=True).exclude(pk=record.pk).exists():
        raise ConflictError(
            "This person already has an active placement for the season. "
            "Deactivate that record first.", code="already_placed")
    record.save(update_fields=[*CORRECTABLE, "updated_at"])
    PlacementRecordRevision.objects.create(
        record=record, by_user_id=actor.user_id, reason=reason.strip(),
        before=before, after=after)
    log.info("placement.record.corrected record=%s by=%s", record.pk, actor.user_id)
    return record
