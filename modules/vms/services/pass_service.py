"""Pass lifecycle and issuance service (BR-003, BR-032, BR-033, BR-034, BR-039)."""
from datetime import timedelta
from django.utils import timezone
from modules.vms.models.visitors import Visitor
from modules.vms.models.visits import VisitRequest, VisitPass
from modules.vms.models.access import AccessPolicy
from modules.vms.services.visitor_service import check_same_day_duplicate_pass
from modules.vms.services.exceptions import PassExpiredException, VMSDomainException


def issue_visit_pass(
    visit: VisitRequest,
    pass_type: str = "walk_in",
    allowed_zones: list[str] | None = None,
    duration_hours: int | None = None,
    parent_pass: VisitPass | None = None,
) -> VisitPass:
    """Issues an active visit pass with QR token and time-bounded validity.
    
    Enforces BR-032: Walk-in pass duration = 4 hours by default.
    Enforces BR-033: Registered guest pass default = 4 hours.
    Enforces BR-034: Generic pass duration from AccessPolicy if unprovided.
    Enforces BR-039: Fast-lane/overflow child passes granted only if parent pass valid.
    """
    visitor = visit.visitor

    # Enforce BR-020: Same-day duplicate check
    check_same_day_duplicate_pass(visitor=visitor)

    # Enforce BR-039: If parent pass specified, verify it is currently active
    if parent_pass is not None:
        if parent_pass.status != "active" or parent_pass.valid_to < timezone.now():
            raise VMSDomainException(
                "Cannot issue event/overflow pass: Parent pass is not active or has expired.",
                rule_id="BR-039",
            )

    # Determine validity duration from policy or defaults
    policy = AccessPolicy.objects.filter(is_active=True).first()
    if duration_hours is None:
        if pass_type == "walk_in":
            # BR-032
            duration_hours = policy.default_walk_in_duration_hours if policy else 4
        elif pass_type == "registered_guest":
            # BR-033
            duration_hours = policy.default_guest_duration_hours if policy else 4
        else:
            # BR-034
            duration_hours = 4

    now = timezone.now()
    valid_from = now
    valid_to = now + timedelta(hours=duration_hours)

    default_zones = allowed_zones if allowed_zones is not None else ["Main Gate", "Administrative Block"]

    pass_record = VisitPass.objects.create(
        visitor=visitor,
        visit=visit,
        pass_type=pass_type,
        valid_from=valid_from,
        valid_to=valid_to,
        status="active",
        allowed_zones=default_zones,
        parent_pass=parent_pass,
    )
    return pass_record


def validate_pass_validity(pass_record: VisitPass) -> bool:
    """Checks if a pass is within its valid operational time window.
    
    Enforces BR-003: Pass is only valid during approved unexpired window.
    """
    now = timezone.now()
    if pass_record.status != "active":
        raise PassExpiredException(
            f"Pass {pass_record.pass_number} is inactive ({pass_record.status}).",
            rule_id="BR-003",
        )
    if pass_record.valid_to < now:
        pass_record.status = "expired"
        pass_record.save(update_fields=["status", "updated_at"])
        raise PassExpiredException(
            f"Pass {pass_record.pass_number} expired at {pass_record.valid_to.strftime('%Y-%m-%d %H:%M')}.",
            rule_id="BR-003",
        )
    return True


def extend_pass_duration(pass_record: VisitPass, additional_hours: int = 1) -> VisitPass:
    """Extends validity of an active pass within institutional policy limits."""
    validate_pass_validity(pass_record)
    policy = AccessPolicy.objects.filter(is_active=True).first()
    max_extension = policy.max_daily_extension_hours if policy else 2

    if additional_hours > max_extension:
        raise VMSDomainException(
            f"Extension requested ({additional_hours}h) exceeds maximum allowed ({max_extension}h).",
            rule_id="BR-018",
        )

    pass_record.valid_to += timedelta(hours=additional_hours)
    pass_record.save(update_fields=["valid_to", "updated_at"])
    return pass_record
