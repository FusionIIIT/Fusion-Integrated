"""Security gate validation, check-in, check-out, override, and offline sync services."""

from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from modules.vms.domain.blacklist import is_blacklisted
from modules.vms.domain.qr_crypto import verify_qr_token
from modules.vms.domain.state_machine import (
    assert_can_transition,
    validate_manual_override,
)
from modules.vms.models import GateCheckLog, Pass
from modules.vms.selectors.blacklist import get_active_blacklist_candidates


class GateValidationError(ValueError):
    """Raised when gate validation fails."""


@transaction.atomic
def validate_pass_at_gate(
    qr_token: str,
    gate_name: str,
    operator_id: int | None = None,
) -> tuple[bool, str, Pass | None]:
    """Validate pass at security gate (UC-018, BR-077, BR-082, BR-112)."""
    now = timezone.now()

    # 1. QR Authenticity check
    is_valid_qr, pass_number = verify_qr_token(qr_token)
    if not is_valid_qr:
        return False, "Invalid or tampered QR code token.", None

    pass_record = (
        Pass.objects.select_related("visit_request", "visit_request__visitor")
        .filter(pass_number=pass_number)
        .first()
    )

    if not pass_record:
        return False, "Pass record not found in system.", None

    # 2. Pass Status Check (BR-077)
    if pass_record.status != "ACTIVE":
        return False, f"Pass status is {pass_record.status}, not ACTIVE.", pass_record

    # 3. Validity window check (BR-190)
    if now < pass_record.valid_from or now > pass_record.valid_to:
        GateCheckLog.objects.create(
            pass_record=pass_record,
            gate_name=gate_name,
            checkpoint_type="ENTRY",
            action="DENIED",
            operator_id=operator_id,
            timestamp=now,
        )
        return False, "Pass is outside its validity window.", pass_record

    # 4. Blacklist checkpoint check (BR-112)
    visitor = pass_record.visit_request.visitor
    candidates = get_active_blacklist_candidates()
    blocked, reason = is_blacklisted(
        visitor.name, visitor.id_document_number, visitor.phone, candidates, now
    )
    if blocked:
        GateCheckLog.objects.create(
            pass_record=pass_record,
            gate_name=gate_name,
            checkpoint_type="ENTRY",
            action="DENIED",
            operator_id=operator_id,
            timestamp=now,
        )
        return False, f"Gate entry denied: Blacklist match ({reason}).", pass_record

    return True, "Pass is valid for entry.", pass_record


@transaction.atomic
def check_in_visitor(
    pass_id: int,
    gate_name: str,
    operator_id: int | None = None,
) -> GateCheckLog:
    """Check in visitor at security gate (UC-018, BW-VMS-01)."""
    pass_record = Pass.objects.select_for_update().select_related("visit_request").get(pk=pass_id)
    visit = pass_record.visit_request

    assert_can_transition(visit.status, "CHECKED_IN")

    now = timezone.now()
    visit.status = "CHECKED_IN"
    visit.actual_check_in = now
    visit.save(update_fields=["status", "actual_check_in", "updated_at"])

    return GateCheckLog.objects.create(
        pass_record=pass_record,
        gate_name=gate_name,
        checkpoint_type="ENTRY",
        action="CHECK_IN",
        operator_id=operator_id,
        timestamp=now,
    )


@transaction.atomic
def check_out_visitor(
    pass_id: int,
    gate_name: str = "Main Exit Gate",
    operator_id: int | None = None,
) -> GateCheckLog:
    """Check out visitor at security gate or self-checkout (UC-021, UC-031, BR-105)."""
    pass_record = Pass.objects.select_for_update().select_related("visit_request").get(pk=pass_id)
    visit = pass_record.visit_request

    assert_can_transition(visit.status, "CHECKED_OUT")

    now = timezone.now()
    visit.status = "CHECKED_OUT"
    visit.actual_check_out = now
    visit.save(update_fields=["status", "actual_check_out", "updated_at"])

    pass_record.status = "USED"
    pass_record.save(update_fields=["status", "updated_at"])

    return GateCheckLog.objects.create(
        pass_record=pass_record,
        gate_name=gate_name,
        checkpoint_type="EXIT",
        action="CHECK_OUT",
        operator_id=operator_id,
        timestamp=now,
    )


@transaction.atomic
def manual_gate_override(
    pass_id: int,
    admin_id: int,
    reason: str,
    gate_name: str = "Main Gate Override",
) -> GateCheckLog:
    """Admin authorizes manual gate override for eligible exceptions (UC-019, BR-085)."""
    validate_manual_override(reason)

    pass_record = (
        Pass.objects.select_for_update()
        .select_related("visit_request", "visit_request__visitor")
        .get(pk=pass_id)
    )
    visitor = pass_record.visit_request.visitor

    # Blacklist check: blacklist cannot be overridden unless safe-listed
    now = timezone.now()
    candidates = get_active_blacklist_candidates()
    blocked, b_reason = is_blacklisted(
        visitor.name, visitor.id_document_number, visitor.phone, candidates, now
    )
    if blocked:
        raise PermissionError(f"Manual override prohibited for blacklisted individual: {b_reason}")

    visit = pass_record.visit_request
    assert_can_transition(visit.status, "CHECKED_IN")

    visit.status = "CHECKED_IN"
    visit.actual_check_in = now
    visit.admin_notes = f"{visit.admin_notes}\nGate Override by Admin #{admin_id}: {reason}".strip()
    visit.save(update_fields=["status", "actual_check_in", "admin_notes", "updated_at"])

    return GateCheckLog.objects.create(
        pass_record=pass_record,
        gate_name=gate_name,
        checkpoint_type="ENTRY",
        action="OVERRIDE",
        operator_id=admin_id,
        is_override=True,
        override_reason=reason,
        timestamp=now,
    )


@transaction.atomic
def offline_batch_sync(
    events: list[dict],
    operator_id: int | None = None,
) -> dict[str, int]:
    """Reconcile cached offline gate check-in logs (UC-028, UC-039, BW-VMS-11)."""
    synced = 0
    failed = 0

    for ev in events:
        pass_id = ev.get("pass_id")
        gate_name = ev.get("gate_name", "Offline Gate")
        op_id = ev.get("operator_id") or operator_id
        ts = ev.get("timestamp")
        timestamp = datetime.fromisoformat(ts) if isinstance(ts, str) else timezone.now()

        try:
            pass_record = Pass.objects.filter(pk=pass_id).select_related("visit_request").first()
            if pass_record and pass_record.visit_request.status in ["APPROVED", "PENDING_APPROVAL"]:
                visit = pass_record.visit_request
                visit.status = "CHECKED_IN"
                visit.actual_check_in = timestamp
                visit.save(update_fields=["status", "actual_check_in", "updated_at"])

                GateCheckLog.objects.create(
                    pass_record=pass_record,
                    gate_name=gate_name,
                    checkpoint_type="ENTRY",
                    action="CHECK_IN",
                    operator_id=op_id,
                    is_offline_sync=True,
                    timestamp=timestamp,
                )
                synced += 1
            else:
                failed += 1
        except (KeyError, ValueError, Pass.DoesNotExist):
            failed += 1

    return {"synced": synced, "failed": failed}
