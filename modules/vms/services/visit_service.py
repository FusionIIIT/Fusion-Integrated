"""Visit request workflow and host approval service (BR-006, BR-007, BR-008, BR-047)."""
from django.utils import timezone

from modules.vms.models.visitors import Visitor
from modules.vms.models.visits import VisitLog, VisitRequest
from modules.vms.services.exceptions import VMSDomainException
from modules.vms.services.pass_service import issue_visit_pass


def create_visit_request(
    visitor: Visitor,
    host_user_id: int,
    purpose: str,
    intended_start: timezone.datetime,
    intended_end: timezone.datetime,
) -> VisitRequest:
    """Submits a new pre-visit request for host review."""
    # Enforce basic sanity: end time must be after start time
    if intended_end <= intended_start:
        raise VMSDomainException("Visit intended end time must be strictly after start time.")

    visit = VisitRequest.objects.create(
        visitor=visitor,
        host_user_id=host_user_id,
        purpose=purpose,
        intended_start=intended_start,
        intended_end=intended_end,
        status="pending",
    )

    # Audit log entry
    VisitLog.objects.create(
        visit=visit,
        action="registered",
        notes=f"Visit request created for Host IAM #{host_user_id}. Awaiting decision.",
    )
    return visit


def decide_visit_request(
    visit: VisitRequest,
    decision: str,  # "approved" or "rejected"
    decided_by_user_id: int,
    instructions: str = "",
    rejection_reason: str = "",
) -> VisitRequest:
    """Processes host approval or rejection.

    Enforces BR-007: Approval preserves original request ID in workflow & logs.
    Enforces BR-047: If rejected, no pass generated and no host-approval notification dispatched.
    """
    if visit.status != "pending":
        raise VMSDomainException(
            f"Cannot decide visit #{visit.id}: Current status is already '{visit.status}'.",
            rule_id="BR-006",
        )

    now = timezone.now()
    visit.decided_at = now
    visit.decided_by_user_id = decided_by_user_id

    if decision == "approved":
        visit.status = "approved"
        visit.instructions = instructions
        visit.save()

        # Generate active pass for approved visit
        issue_visit_pass(
            visit=visit,
            pass_type="registered_guest",
        )
        VisitLog.objects.create(
            visit=visit,
            action="registered",
            logged_by_user_id=decided_by_user_id,
            notes=f"Visit approved by Host #{decided_by_user_id}. Instructions: {instructions}",
        )
    elif decision == "rejected":
        # BR-047: Rejection closes request with reason, no pass created
        visit.status = "rejected"
        visit.rejection_reason = rejection_reason
        visit.save()

        VisitLog.objects.create(
            visit=visit,
            action="terminated_early",
            logged_by_user_id=decided_by_user_id,
            notes=f"Visit rejected by Host #{decided_by_user_id}. Reason: {rejection_reason}",
        )
    else:
        raise VMSDomainException(f"Invalid decision '{decision}'. Expected 'approved' or 'rejected'.")

    return visit


def terminate_visit_early(visit: VisitRequest, terminated_by_user_id: int, reason: str = "") -> VisitRequest:
    """Terminates an on-site visit before its scheduled end time (BR-006)."""
    if visit.status in ("completed", "terminated"):
        raise VMSDomainException(
            f"Visit #{visit.id} is already closed/completed. Cannot terminate.",
            rule_id="BR-006",
        )

    now = timezone.now()
    visit.status = "terminated"
    visit.actual_departure = now
    visit.save()

    # Deactivate active passes associated with this visit
    for p in visit.passes.filter(status="active"):
        p.status = "deactivated"
        p.save(update_fields=["status", "updated_at"])

    VisitLog.objects.create(
        visit=visit,
        action="terminated_early",
        logged_by_user_id=terminated_by_user_id,
        notes=f"Early termination enforced. Reason: {reason}",
    )
    return visit
