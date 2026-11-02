"""Gate entry validation and check-in/out service (BR-002, BR-023, BR-028, BR-029, BR-030, BR-040)."""
from django.utils import timezone
from modules.vms.models.visits import VisitPass, VisitRequest, VisitLog
from modules.vms.models.access import GateAlert
from modules.vms.services.pass_service import validate_pass_validity
from modules.vms.services.exceptions import (
    GateValidationException,
    CheckoutBlockedException,
)


def validate_and_check_in_visitor(
    qr_code_hash: str,
    gate_machine_id: str,
    security_user_id: int,
    gate_name: str = "Main Gate",
) -> VisitPass:
    """Validates visitor pass QR and processes gate check-in.
    
    Enforces BR-028: Auto-closes pending non-critical gate alerts on successful entry.
    Enforces BR-029: Captures nominal machine ID of the scanning device.
    Enforces BR-040: On validation failure, raises GateValidationException without creating duplicate alerts.
    """
    pass_record = VisitPass.objects.filter(qr_code_hash=qr_code_hash).first()
    if not pass_record:
        # BR-040: Clean failure on invalid token without creating bogus alerts
        raise GateValidationException("Invalid QR pass token scanned at gate.", rule_id="BR-040")

    # Validate pass validity window (BR-003)
    validate_pass_validity(pass_record)

    visit = pass_record.visit
    now = timezone.now()

    # Update visit status to on_site
    visit.status = "on_site"
    if not visit.actual_arrival:
        visit.actual_arrival = now
    visit.current_zone = gate_name
    visit.save(update_fields=["status", "actual_arrival", "current_zone", "updated_at"])

    # BR-002 & BR-028: Auto-close any open non-critical alert for this visitor upon entrance
    open_alerts = GateAlert.objects.filter(
        visitor=pass_record.visitor,
        status="open",
    ).exclude(severity="critical")
    for a in open_alerts:
        a.status = "closed"
        a.closed_at = now
        a.closed_by_user_id = security_user_id
        a.details += " | Resolved automatically on gate entrance (BR-028)."
        a.save(update_fields=["status", "closed_at", "closed_by_user_id", "details"])

    # Log entry event with machine ID (BR-029)
    VisitLog.objects.create(
        visit=visit,
        pass_record=pass_record,
        action="check_in",
        gate_or_location=gate_name,
        logged_by_user_id=security_user_id,
        machine_id=gate_machine_id,
        notes=f"Check-in verified via gate terminal {gate_machine_id}.",
    )
    return pass_record


def check_out_visitor(
    pass_number: str,
    security_user_id: int | None = None,
    gate_machine_id: str = "",
    gate_name: str = "Main Gate",
) -> VisitPass:
    """Processes check-out and campus exit for a visitor.
    
    Enforces BR-023: Checkout not logged when already completed.
    Enforces BR-030: Pass and visit closed on checkout.
    """
    pass_record = VisitPass.objects.filter(pass_number=pass_number).first()
    if not pass_record:
        raise GateValidationException(f"Pass '{pass_number}' not found.")

    visit = pass_record.visit

    # Enforce BR-023: Do not double-log checkout if already exited
    if visit.status == "completed" or pass_record.status == "completed":
        raise CheckoutBlockedException(
            f"Pass {pass_number} is already marked as checked out/completed (BR-023).",
            rule_id="BR-023",
        )

    now = timezone.now()
    visit.status = "completed"
    visit.actual_departure = now
    visit.save(update_fields=["status", "actual_departure", "updated_at"])

    pass_record.status = "completed"
    pass_record.save(update_fields=["status", "updated_at"])

    # Audit log entry
    VisitLog.objects.create(
        visit=visit,
        pass_record=pass_record,
        action="check_out",
        gate_or_location=gate_name,
        logged_by_user_id=security_user_id,
        machine_id=gate_machine_id,
        notes=f"Visitor checked out cleanly through {gate_name}.",
    )
    return pass_record
