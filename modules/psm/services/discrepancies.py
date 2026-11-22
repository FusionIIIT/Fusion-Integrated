# Discrepancy reporting, vendor comms, and resolution (PSM-UC-020, 032).
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from core.files.drive import InvalidDriveLink
from core.files.drive import parse as parse_drive_link
from core.files.validators import sanitise_filename
from modules.psm.domain import state_machine as sm
from modules.psm.models import DiscrepancyCase, DiscrepancyCommunication, Invoice
from modules.psm.selectors import scoping
from modules.psm.services.common import (
    audit_record,
    enqueue_notification,
    next_number,
    translate_errors,
)


@transaction.atomic
def report_discrepancy(
    *,
    actor,
    grn_id: int,
    discrepancy_type: str,
    affected_quantity: int,
    description: str,
    requested_resolution: str,
    evidence_url: str = "",
    evidence_filename: str = "",
) -> DiscrepancyCase:
    """Log a delivery discrepancy with optional Drive evidence (PSM-UC-020)."""
    grn = scoping.grns_for(actor).select_for_update(of=("self",)).filter(pk=grn_id).first()
    if grn is None:
        raise NotFoundError("Goods receipt note not found.")
    if affected_quantity <= 0 or affected_quantity > grn.received_quantity:
        raise DomainError(
            f"Affected quantity must be between 1 and {grn.received_quantity}.",
            code="invalid_affected_quantity",
        )
    if not (description or "").strip():
        raise DomainError(
            "Describe the delivery discrepancy or damage.", code="description_required"
        )
    clean_url = ""
    if (evidence_url or "").strip():
        try:
            clean_url = parse_drive_link(evidence_url).url
        except InvalidDriveLink as exc:
            raise DomainError(exc.message, code=exc.code) from exc
    clean_name = (
        sanitise_filename(evidence_filename, fallback="evidence") if evidence_filename else ""
    )
    case = DiscrepancyCase.objects.create(
        case_number=next_number("DSC"),
        grn=grn,
        reported_by_user_id=actor.user_id,
        discrepancy_type=discrepancy_type,
        affected_quantity=affected_quantity,
        description=description.strip(),
        evidence_url=clean_url,
        evidence_filename=clean_name,
        requested_resolution=requested_resolution,
        status=sm.DISC_OPEN,
    )
    if grn.purchase_order_id:
        Invoice.objects.filter(
            purchase_order_id=grn.purchase_order_id,
            status__in=(sm.INV_SUBMITTED, sm.INV_VERIFIED),
        ).update(
            status=sm.INV_ON_HOLD,
            hold_reason=f"Blocked by open discrepancy case {case.case_number}",
        )
    audit_record(
        actor=actor,
        action="discrepancy.reported",
        target_type="discrepancy",
        target_id=case.pk,
        to_state=sm.DISC_OPEN,
    )
    enqueue_notification(
        topic="discrepancy.reported",
        dedupe_key=f"discrepancy.reported:{case.pk}",
        recipient_user_id=actor.user_id,
        subject=f"Discrepancy case {case.case_number} opened",
        body=f"Reported {discrepancy_type} on {grn.grn_number} for {affected_quantity} unit(s).",
        payload={"case_id": case.pk, "grn_id": grn.pk},
    )
    return case


@transaction.atomic
def add_communication(
    *, actor, case_id: int, sender_label: str, message: str
) -> DiscrepancyCommunication:
    """Append a vendor communication record to a discrepancy case (PSM-UC-032, AFR-PSM-052)."""
    case = scoping.discrepancies_for(actor).filter(pk=case_id).first()
    if case is None:
        raise NotFoundError("Discrepancy case not found.")
    if case.status == sm.DISC_CLOSED:
        raise ConflictError(
            "Cannot append communications to a closed discrepancy case.", code="case_closed"
        )
    if not (message or "").strip():
        raise DomainError("Enter the communication message before saving.", code="message_required")
    comm = DiscrepancyCommunication.objects.create(
        case=case,
        sender_label=(sender_label or "PS Admin").strip()[:120],
        message=message.strip(),
        recorded_by_user_id=actor.user_id,
    )
    audit_record(
        actor=actor,
        action="discrepancy.communication_logged",
        target_type="discrepancy",
        target_id=case.pk,
    )
    return comm


@transaction.atomic
def resolve_case(
    *,
    actor,
    case_id: int,
    resolution_action: str,
    resolution_notes: str,
    inventory_adjusted: bool = False,
    accounting_adjusted: bool = False,
) -> DiscrepancyCase:
    """Resolve discrepancy via return/adjustment or one replacement (BW-PSM-06, 10)."""
    case = (
        scoping.discrepancies_for(actor).select_for_update(of=("self",)).filter(pk=case_id).first()
    )
    if case is None:
        raise NotFoundError("Discrepancy case not found.")
    if not (resolution_notes or "").strip():
        raise DomainError(
            "Provide resolution notes when updating this discrepancy case.", code="notes_required"
        )
    old_status = case.status
    if resolution_action == "await_replacement":
        if case.replacement_count >= 1:
            raise ConflictError(
                "Only one replacement traversal is permitted per discrepancy case.",
                code="replacement_limit_reached",
            )
        with translate_errors():
            sm.resolve("discrepancy", case.status, sm.DISC_REPLACEMENT_AWAITED, sm.PS_ADMIN)
        case.status = sm.DISC_REPLACEMENT_AWAITED
        case.replacement_count += 1
        case.resolution_notes = resolution_notes.strip()
        case.save(update_fields=["status", "replacement_count", "resolution_notes", "updated_at"])
    elif resolution_action == "resolve":
        with translate_errors():
            sm.resolve("discrepancy", case.status, sm.DISC_RESOLVED, sm.PS_ADMIN)
        case.status = sm.DISC_RESOLVED
        case.resolution_notes = resolution_notes.strip()
        case.inventory_adjusted = inventory_adjusted
        case.accounting_adjusted = accounting_adjusted
        case.resolved_by_user_id = actor.user_id
        case.resolved_at = timezone.now()
        case.save(
            update_fields=[
                "status",
                "resolution_notes",
                "inventory_adjusted",
                "accounting_adjusted",
                "resolved_by_user_id",
                "resolved_at",
                "updated_at",
            ]
        )
    elif resolution_action == "close":
        with translate_errors():
            sm.resolve("discrepancy", case.status, sm.DISC_CLOSED, sm.PS_ADMIN)
        case.status = sm.DISC_CLOSED
        case.resolution_notes = resolution_notes.strip()
        case.inventory_adjusted = case.inventory_adjusted or inventory_adjusted
        case.accounting_adjusted = case.accounting_adjusted or accounting_adjusted
        case.save(
            update_fields=[
                "status",
                "resolution_notes",
                "inventory_adjusted",
                "accounting_adjusted",
                "updated_at",
            ]
        )
    else:
        raise DomainError(
            "Choose 'await_replacement', 'resolve', or 'close'.", code="invalid_resolution_action"
        )
    audit_record(
        actor=actor,
        action=f"discrepancy.{resolution_action}",
        target_type="discrepancy",
        target_id=case.pk,
        from_state=old_status,
        to_state=case.status,
    )
    return case
