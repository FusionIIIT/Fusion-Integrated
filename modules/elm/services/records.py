"""Authorized, non-sanctioning maintenance of approved leave records."""
from __future__ import annotations

import json
from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.models import LeaveRequest
from modules.elm.services.leave import _event

EDITABLE_FIELDS = (
    "purpose", "station_leave", "station_destination", "station_contact",
    "medical_evidence", "offline_reference", "offline_reason",
    "offline_sanctioned_on",
)


@transaction.atomic
def maintain_leave_record(
    *, request_id: int, actor_id: int, reason: str,
    changes: dict,
) -> LeaveRequest:
    request = LeaveRequest.objects.select_for_update().filter(pk=request_id).first()
    if request is None:
        raise NotFoundError("The leave record was not found.")
    if request.status not in ("approved", "cancelled"):
        raise ConflictError(
            "Only an already-sanctioned leave record can be maintained.",
            code="record_not_maintainable")
    if not reason.strip():
        raise ConflictError("A maintenance reason is required.",
                            code="maintenance_reason_required")
    unknown = set(changes) - set(EDITABLE_FIELDS)
    if unknown:
        raise ConflictError(
            "Maintenance cannot change dates, category, workflow, or sanction state.",
            code="sanctioning_change_not_allowed")
    changes = {key: value for key, value in changes.items()
               if value is not None}
    changes.pop("reason", None)
    if not changes:
        raise ConflictError("Provide at least one record correction.",
                            code="maintenance_change_required")
    if "offline_reference" in changes:
        reference = changes["offline_reference"].strip()
        if not reference and request.offline_reference:
            raise ConflictError(
                "The offline sanction reference is required record evidence.",
                code="offline_evidence_required")
        if reference and LeaveRequest.objects.filter(
                applicant_user_id=request.applicant_user_id,
                offline_reference=reference).exclude(pk=request.pk).exists():
            raise ConflictError(
                "This offline sanction reference is already used by the employee.",
                code="duplicate_offline_reference")
        if reference and not request.offline_reference:
            raise ConflictError(
                "Offline sanction evidence can only be maintained on an offline record.",
                code="offline_record_required")
        changes["offline_reference"] = reference
    if any(field in changes for field in ("offline_reason", "offline_sanctioned_on")) \
            and not request.offline_reference:
        raise ConflictError(
            "Offline sanction evidence can only be maintained on an offline record.",
            code="offline_record_required")
    sanctioned_on = changes.get("offline_sanctioned_on")
    if isinstance(sanctioned_on, date) and sanctioned_on > timezone.localdate():
        raise ConflictError("The offline sanction date cannot be in the future.",
                            code="invalid_offline_sanction_date")

    before_after = {}
    for field, value in changes.items():
        current = getattr(request, field)
        if current == value:
            continue
        before_after[field] = {
            "before": current.isoformat() if isinstance(current, date) else current,
            "after": value.isoformat() if isinstance(value, date) else value,
        }
        setattr(request, field, value)
    if not before_after:
        raise ConflictError("The submitted corrections do not change this record.",
                            code="maintenance_no_change")
    try:
        with transaction.atomic():
            request.save(update_fields=[*before_after, "updated_at"])
    except IntegrityError as exc:
        raise ConflictError(
            "This offline sanction reference is already used by the employee.",
            code="duplicate_offline_reference") from exc

    _event(
        request, actor_id, "record_maintained",
        note=f"{reason.strip()} | changes={json.dumps(before_after, sort_keys=True)}")
    return request
