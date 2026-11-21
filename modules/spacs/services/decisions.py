"""SPACS Scholarship Decision Service (CFR-SPACS-008)."""

from django.utils import timezone

from ..domain.rules import assert_decision_authority
from ..domain.state_machine import (
    APPROVED,
    CORRECTION_REQUIRED,
    REJECTED,
    UNDER_CONVENER_REVIEW,
    resolve_application_transition,
)
from ..models import SpacsApplication
from .audit import log_action, notify_user
from .tasks import close_pending_tasks


def open_convener_decision(
    application_id: str,
    convener_user_id: int,
    user_roles: list[str],
) -> SpacsApplication:
    """Convener opens verified or concern application for final decision (AFR-SPACS-027, BW-SPACS-03, BW-SPACS-04)."""
    assert_decision_authority(user_roles)

    app = SpacsApplication.objects.get(application_id=application_id)
    action = "open_renewal_decision" if app.is_renewal else "open_decision"
    transition = resolve_application_transition(app.state, action, "spacs_convener")
    app.state = transition.target
    app.save()

    log_action(
        event_type="decision_review_opened",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=convener_user_id,
    )
    return app


def approve_application(
    application_id: str,
    convener_user_id: int,
    user_roles: list[str],
    reason: str = "Meets all criteria and verification satisfied",
) -> SpacsApplication:
    """Approve scholarship application (AFR-SPACS-028, AFR-SPACS-029, BW-SPACS-03)."""
    assert_decision_authority(user_roles)

    app = SpacsApplication.objects.get(application_id=application_id)
    action = "approve_renewal" if app.is_renewal else "approve"
    transition = resolve_application_transition(app.state, action, "spacs_convener")
    app.state = transition.target
    app.decision_actor_user_id = convener_user_id
    app.decision_reason = reason
    app.decision_at = timezone.now()
    app.save()

    close_pending_tasks(entity_type="application", entity_id=app.application_id)

    notify_user(
        recipient_user_id=app.applicant_user_id,
        event_type="approved",
        title="Scholarship Approved",
        message=f"Congratulations! Your scholarship application {app.application_id} has been approved.",
    )

    log_action(
        event_type="application_approved",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=convener_user_id,
        details={"reason": reason, "version": app.catalogue_version},
    )
    return app


def reject_application(
    application_id: str,
    convener_user_id: int,
    user_roles: list[str],
    reason: str,
) -> SpacsApplication:
    """Reject scholarship application (AFR-SPACS-028, AFR-SPACS-029, BW-SPACS-04)."""
    assert_decision_authority(user_roles)

    app = SpacsApplication.objects.get(application_id=application_id)
    action = "reject_renewal" if app.is_renewal else "reject"
    transition = resolve_application_transition(app.state, action, "spacs_convener")
    app.state = transition.target
    app.decision_actor_user_id = convener_user_id
    app.decision_reason = reason
    app.decision_at = timezone.now()
    app.save()

    close_pending_tasks(entity_type="application", entity_id=app.application_id)

    notify_user(
        recipient_user_id=app.applicant_user_id,
        event_type="rejected",
        title="Scholarship Application Rejected",
        message=f"Your scholarship application {app.application_id} was not approved: {reason}",
    )

    log_action(
        event_type="application_rejected",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=convener_user_id,
        details={"reason": reason},
    )
    return app


def return_for_correction(
    application_id: str,
    convener_user_id: int,
    user_roles: list[str],
    reason: str,
) -> SpacsApplication:
    """Convener returns application to student for correction (AFR-SPACS-028, BW-SPACS-04)."""
    assert_decision_authority(user_roles)

    app = SpacsApplication.objects.get(application_id=application_id)
    transition = resolve_application_transition(app.state, "return_for_correction", "spacs_convener")
    app.state = transition.target
    app.correction_reason = reason
    app.save()

    close_pending_tasks(entity_type="application", entity_id=app.application_id)

    notify_user(
        recipient_user_id=app.applicant_user_id,
        event_type="correction_required",
        title="Correction Required for Scholarship Application",
        message=f"The Convener returned your application {app.application_id} for correction: {reason}",
    )

    log_action(
        event_type="convener_correction_requested",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=convener_user_id,
        details={"reason": reason},
    )
    return app
