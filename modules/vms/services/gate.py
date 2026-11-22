"""VMS Gate Service and Single Transactional Choke Point.
All visit state movements pass through transition_visit_state with select_for_update().
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.vms.domain.rules import (
    validate_blacklist_match,
    validate_zone_access,
)
from modules.vms.domain.state_machine import (
    InvalidStateTransitionError,
    TransitionTrigger,
    validate_transition,
)
from modules.vms.models.access import GateAlert, GateLog
from modules.vms.models.visitors import BlacklistEntry
from modules.vms.models.visits import Visit
from modules.vms.services.errors import (
    BlacklistMatchError,
    InvalidTransitionError,
    PassExpiredError,
    UnauthorizedZoneError,
    VisitNotFoundError,
)


@transaction.atomic
def transition_visit_state(
    visit_id: int,
    trigger: TransitionTrigger | str,
    actor_id: int | None = None,
    note: str = "",
    gate_name: str = "Main Gate",
    reader_machine_id: str = "",
) -> Visit:
    """Single transactional choke point for all visit state movements.
    Locks row with select_for_update, validates domain state-machine rules,
    records audit gate logs, and persists state atomically.
    """
    trigger_str = str(trigger.value if isinstance(trigger, TransitionTrigger) else trigger)

    try:
        visit = Visit.objects.select_for_update().select_related("visitor").get(id=visit_id)
    except Visit.DoesNotExist as err:
        raise VisitNotFoundError(f"Visit with ID {visit_id} not found.") from err

    # Validate transition in pure domain
    try:
        new_state = validate_transition(visit.status, trigger_str)
    except InvalidStateTransitionError as err:
        raise InvalidTransitionError(str(err)) from err

    # Execute state mutations and audit logs
    visit.status = new_state
    now = timezone.now()

    if trigger_str == TransitionTrigger.GATE_CHECK_IN.value:
        visit.check_in_time = now
        visit.checked_in_by = actor_id
        GateLog.objects.create(
            visit=visit,
            action="check_in",
            gate_name=gate_name,
            reader_machine_id=reader_machine_id,
            logged_by=actor_id,
        )
    elif trigger_str in (
        TransitionTrigger.GATE_CHECK_OUT.value,
        TransitionTrigger.AUTO_CHECKOUT.value,
    ):
        visit.check_out_time = now
        visit.checked_out_by = actor_id
        GateLog.objects.create(
            visit=visit,
            action="check_out",
            gate_name=gate_name,
            reader_machine_id=reader_machine_id,
            logged_by=actor_id,
        )
    elif trigger_str == TransitionTrigger.HOST_REJECT.value and note:
        visit.rejection_reason = note

    visit.save()
    return visit


def verify_qr_and_check_in(
    qr_code_hash: str,
    guard_user_id: int,
    gate_name: str = "Main Gate",
    reader_machine_id: str = "",
) -> Visit:
    """Verifies QR code hash, checks pass expiry and blacklist, then executes check-in."""
    try:
        visit = Visit.objects.select_related("visitor").get(qr_code_hash=qr_code_hash)
    except Visit.DoesNotExist as err:
        raise VisitNotFoundError("Invalid or unrecognized QR code hash.") from err

    now = timezone.now()

    # Rule BR-045: Check validity window
    if now < visit.valid_from or now > visit.valid_to:
        v_start = visit.valid_from.isoformat()
        v_end = visit.valid_to.isoformat()
        raise PassExpiredError(f"Pass is not valid at this time (Valid: {v_start} to {v_end}).")

    # Re-verify blacklist at gate (Rule BR-001 / BR-004)
    active_bl = list(
        BlacklistEntry.objects.filter(is_active=True).values(
            "id_number_hash", "phone", "full_name", "reason", "severity", "is_active"
        )
    )
    bl_check = validate_blacklist_match(
        visit.visitor.id_number_hash,
        visit.visitor.phone,
        f"{visit.visitor.first_name} {visit.visitor.last_name}",
        active_bl,
    )
    if bl_check.is_blacklisted:
        alert_msg = (
            f"Blacklisted visitor check-in attempt: {visit.visitor.phone} ({bl_check.reason})"
        )
        GateAlert.objects.create(
            alert_type="blacklist_gate_entry_attempt",
            severity="critical",
            message=alert_msg,
            visit_id=visit.id,
            visitor_id=visit.visitor.id,
        )
        raise BlacklistMatchError(f"Entry denied: {bl_check.reason}")

    return transition_visit_state(
        visit_id=visit.id,
        trigger=TransitionTrigger.GATE_CHECK_IN,
        actor_id=guard_user_id,
        gate_name=gate_name,
        reader_machine_id=reader_machine_id,
    )


def execute_check_out(
    visit_id: int,
    guard_user_id: int,
    gate_name: str = "Main Gate",
) -> Visit:
    """Executes check out for an on-site visit."""
    return transition_visit_state(
        visit_id=visit_id,
        trigger=TransitionTrigger.GATE_CHECK_OUT,
        actor_id=guard_user_id,
        gate_name=gate_name,
    )


def verify_zone_access(
    visit_id: int,
    requested_zone: str,
    guard_user_id: int,
) -> bool:
    """Enforces BR-041: zone access authorization."""
    try:
        visit = Visit.objects.get(id=visit_id)
    except Visit.DoesNotExist as err:
        raise VisitNotFoundError("Visit not found.") from err

    result = validate_zone_access(visit.allowed_zones, requested_zone)
    if not result.allowed:
        z_msg = f"Visitor {visit.pass_number} unauthorized access to zone {requested_zone}."
        GateAlert.objects.create(
            alert_type="zone_violation",
            severity="warning",
            message=z_msg,
            visit_id=visit.id,
            visitor_id=visit.visitor_id,
        )
        raise UnauthorizedZoneError(result.reason)

    GateLog.objects.create(
        visit=visit,
        action="zone_transit",
        gate_name=f"Zone Gate: {requested_zone}",
        logged_by=guard_user_id,
    )
    return True


@transaction.atomic
def reconcile_offline_gate_events(records: list[dict], guard_user_id: int) -> dict:
    """Processes offline gate check-in/out records atomically (BW-VMS-11)."""
    processed = 0
    errors = []

    for r in records:
        qr_hash = r.get("qr_code_hash")
        action = r.get("action", "check_in")
        gate_name = r.get("gate_name", "Main Gate")
        reader_id = r.get("reader_machine_id", "offline_device")

        try:
            visit = Visit.objects.get(qr_code_hash=qr_hash)
            trigger = (
                TransitionTrigger.GATE_CHECK_IN
                if action == "check_in"
                else TransitionTrigger.GATE_CHECK_OUT
            )
            transition_visit_state(
                visit_id=visit.id,
                trigger=trigger,
                actor_id=guard_user_id,
                gate_name=gate_name,
                reader_machine_id=reader_id,
            )
            processed += 1
        except (
            VisitNotFoundError,
            InvalidTransitionError,
            BlacklistMatchError,
            PassExpiredError,
            UnauthorizedZoneError,
            InvalidStateTransitionError,
            ValueError,
        ) as e:
            errors.append({"qr_code_hash": qr_hash, "error": str(e)})

    return {"processed": processed, "errors": errors}
