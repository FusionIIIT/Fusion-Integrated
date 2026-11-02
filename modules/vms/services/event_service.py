"""Bulk event visitor management service (BR-021, BR-039, BR-043, BR-044)."""
from django.utils import timezone
from modules.vms.models.visitors import Visitor
from modules.vms.models.visits import VisitRequest, VisitPass
from modules.vms.models.muster import EmergencyMuster
from modules.vms.services.visitor_service import register_visitor
from modules.vms.services.pass_service import issue_visit_pass
from modules.vms.services.gate_service import check_out_visitor
from modules.vms.services.exceptions import VMSDomainException, CheckoutBlockedException


def process_bulk_event_attendees(
    event_name: str,
    organizer_user_id: int,
    attendees: list[dict],  # list of {"name": str, "phone": str, "email": str}
    duration_hours: int = 8,
    allowed_zones: list[str] | None = None,
) -> list[VisitPass]:
    """Bulk-registers attendees for a seminar/drive and generates event passes.
    
    Enforces BR-021: Bulk event batch generates passes for all supplied records.
    """
    if not attendees:
        raise VMSDomainException("Attendee list cannot be empty for event visitor upload.", rule_id="BR-021")

    zones = allowed_zones or ["Main Gate", "Auditorium", "Seminar Hall"]
    now = timezone.now()
    generated_passes: list[VisitPass] = []

    for item in attendees:
        visitor = register_visitor(
            full_name=item["name"],
            phone=item["phone"],
            email=item.get("email", ""),
            organization=event_name,
        )
        visit = VisitRequest.objects.create(
            visitor=visitor,
            host_user_id=organizer_user_id,
            purpose=f"Special Event: {event_name}",
            intended_start=now,
            intended_end=now + timezone.timedelta(hours=duration_hours),
            status="approved",
            decided_at=now,
            decided_by_user_id=organizer_user_id,
        )
        p = issue_visit_pass(
            visit=visit,
            pass_type="event",
            allowed_zones=zones,
            duration_hours=duration_hours,
        )
        generated_passes.append(p)

    return generated_passes


def process_event_checkout(
    pass_number: str,
    gate_machine_id: str = "",
    security_user_id: int | None = None,
) -> VisitPass:
    """Processes checkout for event attendee.
    
    Enforces BR-043: If an emergency muster is currently in progress, standard checkout is
    blocked until evacuation protocol is respected.
    Enforces BR-044: Direct exit permitted without requiring transfer back to host.
    """
    # BR-043: Check if campus evacuation muster is active
    active_muster = EmergencyMuster.objects.filter(status="in_progress").exists()
    if active_muster:
        raise CheckoutBlockedException(
            "Campus emergency evacuation in progress. Exit must follow muster evacuation procedure (BR-043).",
            rule_id="BR-043",
        )

    # BR-044: Direct exit without needing event host transfer
    return check_out_visitor(
        pass_number=pass_number,
        security_user_id=security_user_id,
        gate_machine_id=gate_machine_id,
        gate_name="Event Gate / Main Gate",
    )
