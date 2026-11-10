"""SPACS Verification Service (CFR-SPACS-006)."""

from ..domain.rules import (
    assert_assistant_action_permitted,
    check_application_review_access,
    validate_document_verification_recording,
)
from ..domain.state_machine import (
    CORRECTION_REQUIRED,
    RESUBMITTED,
    SUBMITTED,
    UNDER_VERIFICATION,
    VERIFICATION_CONCERN,
    VERIFIED,
    resolve_application_transition,
)
from ..models import SpacsApplication
from .audit import log_action, notify_user
from .tasks import close_pending_tasks, create_task


def open_verification_task(
    application_id: str,
    assistant_user_id: int,
    user_roles: list[str],
) -> SpacsApplication:
    """Assistant opens assigned application for verification (AFR-SPACS-019)."""
    check_application_review_access(user_roles)
    app = SpacsApplication.objects.get(application_id=application_id)

    action = "open_renewal_verification" if app.is_renewal else "open_verification"
    transition = resolve_application_transition(app.state, action, "spacs_assistant")
    app.state = transition.target
    app.verification_assigned_to_user_id = assistant_user_id
    app.save()

    log_action(
        event_type="verification_opened",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=assistant_user_id,
    )
    return app


def record_verification_findings(
    application_id: str,
    assistant_user_id: int,
    user_roles: list[str],
    findings: str,
    is_authenticity_confirmed: bool = True,
) -> SpacsApplication:
    """Record verification notes and authenticity findings without final sanction (AFR-SPACS-020, BR-SPACS-006, BR-SPACS-016)."""
    check_application_review_access(user_roles)
    assert_assistant_action_permitted("record_findings")
    validate_document_verification_recording(is_authenticity_confirmed, findings)

    app = SpacsApplication.objects.get(application_id=application_id)
    app.verification_findings = findings
    app.verification_authenticity_confirmed = is_authenticity_confirmed
    app.save()

    log_action(
        event_type="verification_findings_recorded",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=assistant_user_id,
        details={"findings": findings, "authenticity_confirmed": is_authenticity_confirmed},
    )
    return app


def request_correction(
    application_id: str,
    assistant_user_id: int,
    user_roles: list[str],
    reason: str,
) -> SpacsApplication:
    """Return application to student with correction request (AFR-SPACS-021, BW-SPACS-02)."""
    check_application_review_access(user_roles)
    assert_assistant_action_permitted("request_correction")

    app = SpacsApplication.objects.get(application_id=application_id)
    transition = resolve_application_transition(app.state, "request_correction", "spacs_assistant")
    app.state = transition.target
    app.correction_reason = reason
    app.save()

    close_pending_tasks(entity_type="application", entity_id=app.application_id)

    notify_user(
        recipient_user_id=app.applicant_user_id,
        event_type="correction_required",
        title="Correction Required for Scholarship Application",
        message=f"Your application {app.application_id} requires correction: {reason}",
    )

    log_action(
        event_type="correction_requested",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=assistant_user_id,
        details={"reason": reason},
    )
    return app


def record_verification_concern(
    application_id: str,
    assistant_user_id: int,
    user_roles: list[str],
    concern_notes: str,
) -> SpacsApplication:
    """Record an unresolved concern and route to Convener (AFR-SPACS-025, BW-SPACS-04)."""
    check_application_review_access(user_roles)
    assert_assistant_action_permitted("record_concern")

    app = SpacsApplication.objects.get(application_id=application_id)
    transition = resolve_application_transition(app.state, "record_concern", "spacs_assistant")
    app.state = transition.target
    app.verification_findings = concern_notes
    app.save()

    close_pending_tasks(entity_type="application", entity_id=app.application_id)
    create_task(
        task_type="decision",
        entity_type="application",
        entity_id=app.application_id,
        assigned_role="spacs_convener",
    )

    log_action(
        event_type="verification_concern_recorded",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=assistant_user_id,
        details={"concern": concern_notes},
    )
    return app


def mark_verified(
    application_id: str,
    assistant_user_id: int,
    user_roles: list[str],
) -> SpacsApplication:
    """Mark application Verified and route to Convener for decision (AFR-SPACS-024, BW-SPACS-01, BW-SPACS-06)."""
    check_application_review_access(user_roles)
    assert_assistant_action_permitted("mark_verified")

    app = SpacsApplication.objects.get(application_id=application_id)
    action = "mark_renewal_verified" if app.is_renewal else "mark_verified"
    transition = resolve_application_transition(app.state, action, "spacs_assistant")
    app.state = transition.target
    app.save()

    close_pending_tasks(entity_type="application", entity_id=app.application_id)
    create_task(
        task_type="decision",
        entity_type="application",
        entity_id=app.application_id,
        assigned_role="spacs_convener",
    )

    log_action(
        event_type="application_verified",
        entity_type="application",
        entity_id=app.application_id,
        actor_user_id=assistant_user_id,
    )
    return app
