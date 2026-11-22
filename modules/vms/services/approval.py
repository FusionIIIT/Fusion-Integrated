"""Host and Admin approval, extension, and termination services."""

from __future__ import annotations

import uuid
from datetime import date

from django.db import transaction
from django.utils import timezone

from modules.vms.domain.qr_crypto import generate_qr_token
from modules.vms.domain.state_machine import (
    MissingJustificationError,
    assert_can_transition,
    validate_rejection,
    validate_termination,
)
from modules.vms.models import HostPreAuthorization, Pass, VisitRequest


@transaction.atomic
def decide_visit_request(
    visit_id: int,
    host_id: int,
    decision: str,
    reason: str = "",
) -> VisitRequest:
    """Host decides (APPROVE or REJECT) a pending visit request (UC-013, BR-052)."""
    visit = VisitRequest.objects.select_for_update().get(pk=visit_id)

    if visit.host_id != host_id:
        raise PermissionError("Only the assigned host can decide this visit request.")

    decision = decision.upper()
    if decision == "APPROVE":
        assert_can_transition(visit.status, "APPROVED")
        visit.status = "APPROVED"
        visit.save(update_fields=["status", "updated_at"])

        # Generate digital pass if not already generated
        if not hasattr(visit, "digital_pass"):
            pass_number = f"PASS-{uuid.uuid4().hex[:8].upper()}"
            qr_token = generate_qr_token(pass_number)
            Pass.objects.create(
                visit_request=visit,
                pass_number=pass_number,
                qr_token=qr_token,
                pass_type=visit.pass_type,
                valid_from=visit.scheduled_start,
                valid_to=visit.scheduled_end,
                status="ACTIVE",
            )
    elif decision == "REJECT":
        validate_rejection(reason)
        assert_can_transition(visit.status, "REJECTED")
        visit.status = "REJECTED"
        visit.rejection_reason = reason
        visit.save(update_fields=["status", "rejection_reason", "updated_at"])
    else:
        raise ValueError(f"Invalid decision '{decision}'; must be 'APPROVE' or 'REJECT'.")

    return visit


@transaction.atomic
def contingency_approve(
    visit_id: int,
    admin_id: int,
    reason: str,
) -> VisitRequest:
    """Admin contingency approval for unavailable host (UC-033, BR-049, BR-050)."""
    if not reason or not reason.strip():
        raise MissingJustificationError("A contingency approval reason is required.")

    visit = VisitRequest.objects.select_for_update().get(pk=visit_id)
    assert_can_transition(visit.status, "APPROVED")

    visit.status = "APPROVED"
    visit.admin_notes = f"Contingency approved by Admin #{admin_id}: {reason}"
    visit.save(update_fields=["status", "admin_notes", "updated_at"])

    if not hasattr(visit, "digital_pass"):
        pass_number = f"CONT-{uuid.uuid4().hex[:8].upper()}"
        qr_token = generate_qr_token(pass_number)
        Pass.objects.create(
            visit_request=visit,
            pass_number=pass_number,
            qr_token=qr_token,
            pass_type=visit.pass_type,
            valid_from=visit.scheduled_start,
            valid_to=visit.scheduled_end,
            status="ACTIVE",
        )

    return visit


@transaction.atomic
def extend_visit(
    visit_id: int,
    hours: int,
    operator_id: int,
    reason: str = "",
) -> VisitRequest:
    """Extend on-site visit duration (UC-034, BR-194)."""
    visit = VisitRequest.objects.select_for_update().get(pk=visit_id)
    if visit.status != "CHECKED_IN":
        raise ValueError("Only currently on-site (CHECKED_IN) visits can be extended.")

    if hours <= 0 or hours > 8:
        raise ValueError("Extension hours must be between 1 and 8.")

    delta = timezone.timedelta(hours=hours)
    visit.scheduled_end = visit.scheduled_end + delta
    visit.extension_hours += hours
    if reason:
        note = f"{visit.admin_notes}\nExtension +{hours}h by #{operator_id}: {reason}"
        visit.admin_notes = note.strip()
    visit.save(update_fields=["scheduled_end", "extension_hours", "admin_notes", "updated_at"])

    # Update digital pass valid_to
    if hasattr(visit, "digital_pass"):
        pass_record = visit.digital_pass
        pass_record.valid_to = pass_record.valid_to + delta
        pass_record.save(update_fields=["valid_to", "updated_at"])

    return visit


@transaction.atomic
def terminate_visit(
    visit_id: int,
    operator_id: int,
    reason: str,
) -> VisitRequest:
    """Early termination of visit by Host or Admin (UC-016, UC-036, BR-073)."""
    validate_termination(reason)
    visit = VisitRequest.objects.select_for_update().get(pk=visit_id)
    assert_can_transition(visit.status, "TERMINATED_EARLY")

    was_checked_in = (visit.status == "CHECKED_IN")
    visit.status = "TERMINATED_EARLY"
    visit.admin_notes = f"{visit.admin_notes}\nTerminated early by #{operator_id}: {reason}".strip()
    if was_checked_in and not visit.actual_check_out:
        visit.actual_check_out = timezone.now()
    visit.save(update_fields=["status", "admin_notes", "actual_check_out", "updated_at"])

    if hasattr(visit, "digital_pass"):
        pass_record = visit.digital_pass
        pass_record.status = "REVOKED"
        pass_record.save(update_fields=["status", "updated_at"])

    return visit


@transaction.atomic
def create_pre_authorization(
    host_id: int,
    visitor_email: str,
    visitor_name: str,
    valid_from: date,
    valid_to: date,
) -> HostPreAuthorization:
    """Host creates recurring pre-authorization for frequent visitor (UC-014, BR-195)."""
    if valid_to < valid_from:
        raise ValueError("valid_to must be on or after valid_from.")

    return HostPreAuthorization.objects.create(
        host_id=host_id,
        visitor_email=visitor_email,
        visitor_name=visitor_name,
        valid_from=valid_from,
        valid_to=valid_to,
        is_active=True,
    )
