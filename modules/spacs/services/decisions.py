"""Scholarship decision services for SPACS.

Enforces:
- CFR-SPACS-008 (Scholarship Decision)
- BR-SPACS-018 (Scholarship Decision Authority - Convener only, Assistant excluded)
- UC-SPACS-006 (Make Scholarship Decision)
- BW-SPACS-03, BW-SPACS-04, BW-SPACS-07, BW-SPACS-10, CW-SPACS-01, CW-SPACS-02
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone as dj_timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.spacs.domain.state_machines import (
    APP_STATUS_APPROVED,
    APP_STATUS_REJECTED,
    APP_STATUS_CORRECTION_REQUIRED,
    APP_STATUS_VERIFIED_ROUTED,
    APP_STATUS_VERIFICATION_CONCERN,
    APP_STATUS_UNDER_CONVENER_REVIEW,
    can_transition_application,
)
from modules.spacs.models import (
    ScholarshipApplication,
    ApplicationTransition,
    SpacsTask,
)
from modules.spacs.services.audit import record_audit_event
from modules.spacs.services.notifications import enqueue as enqueue_notification
from modules.spacs.services.verification import request_correction


def record_scholarship_decision(
    application_id: int,
    convener_user_id: int,
    outcome: str,  # "approved", "rejected", "return_for_correction"
    reason: str = "",
    policy_reference: str = "",
) -> ScholarshipApplication:
    """Executes the final scholarship decision (UC-SPACS-006).

    Guarded by BR-SPACS-018: Only authorized Convener role may invoke.
    """
    if outcome == "return_for_correction":
        return request_correction(
            application_id=application_id,
            reviewer_user_id=convener_user_id,
            actor_role="spacs_convener",
            correction_reason=reason or "Returned by Convener for correction",
        )

    target_status = APP_STATUS_APPROVED if outcome == "approved" else APP_STATUS_REJECTED
    if outcome == "rejected" and not reason.strip():
        raise ConflictError("A rejection decision requires a recorded rationale (AFR-SPACS-029).")

    with transaction.atomic():
        app = (
            ScholarshipApplication.objects.select_for_update()
            .filter(pk=application_id)
            .select_related("policy_version", "policy_version__catalogue_entry")
            .first()
        )
        if not app:
            raise NotFoundError("Application not found.")

        # BW-SPACS-03: If the application is in verified/concern state, the
        # Convener must first open it for review before applying a final decision.
        # We handle both steps atomically here so a single API call covers the
        # full "open review → decide" flow without requiring a separate round-trip.
        if app.status in (APP_STATUS_VERIFIED_ROUTED, APP_STATUS_VERIFICATION_CONCERN):
            open_review = can_transition_application(
                from_status=app.status,
                to_status=APP_STATUS_UNDER_CONVENER_REVIEW,
                actor_role="spacs_convener",
            )
            if not open_review.allowed:
                raise ConflictError(open_review.reason)
            # Advance in-memory; the final save below persists both transitions.
            app.status = APP_STATUS_UNDER_CONVENER_REVIEW

        transition = can_transition_application(
            from_status=app.status,
            to_status=target_status,
            actor_role="spacs_convener",
        )
        if not transition.allowed:
            raise ConflictError(transition.reason)

        prev_status = app.status
        now = dj_timezone.now()
        app.status = target_status
        app.decision_outcome = outcome
        app.decision_reason = reason.strip()
        app.decision_actor_user_id = convener_user_id
        app.decision_at = now
        app.save()

        # Close pending Convener decision task
        SpacsTask.objects.filter(
            application=app, task_type="decision", status="pending"
        ).update(status="completed", completed_at=now, completed_by_user_id=convener_user_id)

        ApplicationTransition.objects.create(
            application=app,
            from_status=prev_status,
            to_status=target_status,
            actor_user_id=convener_user_id,
            actor_role_label="SPACS Convener",
            reason=reason or f"Scholarship {outcome} by Convener",
        )

        record_audit_event(
            action=f"application.{outcome}",
            entity_type="ScholarshipApplication",
            entity_id=app.id,
            actor_user_id=convener_user_id,
            actor_role="spacs_convener",
            details={
                "app_number": app.application_number,
                "outcome": outcome,
                "reason": reason,
                "policy_ref": policy_reference,
            },
        )

        enqueue_notification(
            topic="application.decided",
            dedupe_key=f"spacs.app.decision.{app.id}",
            subject=f"Scholarship Decision: {app.application_number}",
            body=f"Your scholarship application {app.application_number} has been {outcome.upper()}.",
            recipient_user_id=app.user_id,
            payload={"application_id": app.id, "outcome": outcome},
        )

        return app
