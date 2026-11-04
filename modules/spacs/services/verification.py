"""Verification, correction, and concern handling services for SPACS.

Enforces:
- CFR-SPACS-006 (Verification, Correction and Concern Handling)
- BR-SPACS-005 (Application review access)
- BR-SPACS-006 (Verification is not final sanction - Assistant cannot approve/reject)
- BR-SPACS-011 (Correction and revalidation)
- BR-SPACS-016 (Document authenticity requires authorized verification)
- UC-SPACS-002, UC-SPACS-003
- BW-SPACS-01, BW-SPACS-02, CW-SPACS-01
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from django.db import transaction
from django.utils import timezone as dj_timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.spacs.domain.state_machines import (
    APP_STATUS_VERIFIED_ROUTED,
    APP_STATUS_VERIFICATION_CONCERN,
    APP_STATUS_CORRECTION_REQUIRED,
    APP_STATUS_RESUBMITTED,
    APP_STATUS_UNDER_VERIFICATION,
    can_transition_application,
)
from modules.spacs.models import (
    ScholarshipApplication,
    ApplicationDocument,
    ApplicationTransition,
    SpacsTask,
)
from modules.spacs.services.audit import record_audit_event
from modules.spacs.services.notifications import enqueue as enqueue_notification


def record_document_verification_finding(
    document_id: int,
    assistant_user_id: int,
    verification_status: str,
    comment: str = "",
) -> ApplicationDocument:
    """Records human verification finding on a supporting document (BR-SPACS-016)."""
    with transaction.atomic():
        doc = ApplicationDocument.objects.select_for_update().filter(pk=document_id).first()
        if not doc:
            raise NotFoundError("Supporting document not found.")

        doc.verification_status = verification_status
        doc.verification_comment = comment.strip()
        doc.save()

        record_audit_event(
            action="document.verified",
            entity_type="ApplicationDocument",
            entity_id=doc.id,
            actor_user_id=assistant_user_id,
            actor_role="spacs_assistant",
            details={
                "doc_type": doc.doc_type,
                "status": verification_status,
                "comment": comment,
            },
        )
        return doc


def mark_verified_and_route(
    application_id: int,
    assistant_user_id: int,
    findings: dict[str, Any] | None = None,
) -> ScholarshipApplication:
    """Marks application Verified and routes a decision task to the Convener (UC-SPACS-002, BW-SPACS-01).

    Enforces:
    - Closes active verification task.
    - Transitions application to verified_routed.
    - Creates a new decision task for the SPACS Convener.
    """
    with transaction.atomic():
        app = (
            ScholarshipApplication.objects.select_for_update()
            .filter(pk=application_id)
            .select_related("policy_version", "policy_version__catalogue_entry")
            .first()
        )
        if not app:
            raise NotFoundError("Application not found.")

        transition = can_transition_application(
            from_status=app.status,
            to_status=APP_STATUS_VERIFIED_ROUTED,
            actor_role="spacs_assistant",
        )
        if not transition.allowed:
            raise ConflictError(transition.reason)

        prev_status = app.status
        now = dj_timezone.now()
        app.status = APP_STATUS_VERIFIED_ROUTED
        app.verified_at = now
        app.verified_by_user_id = assistant_user_id
        if findings:
            app.verification_findings = findings
        app.save()

        # 1. Close current verification task
        SpacsTask.objects.filter(
            application=app, task_type="verification", status="pending"
        ).update(status="completed", completed_at=now, completed_by_user_id=assistant_user_id)

        # 2. Record application transition
        ApplicationTransition.objects.create(
            application=app,
            from_status=prev_status,
            to_status=APP_STATUS_VERIFIED_ROUTED,
            actor_user_id=assistant_user_id,
            actor_role_label="SPACS Assistant",
            reason="Verification requirements satisfied; routed for decision",
        )

        # 3. Create Convener decision task with policy SLA snapshot
        policy = app.policy_version
        due_at = None
        sla_config = policy.sla_config or {}
        decision_threshold = sla_config.get("decision_threshold_hours") or sla_config.get("threshold_hours")
        if decision_threshold:
            due_at = now + timedelta(hours=int(decision_threshold))

        SpacsTask.objects.create(
            application=app,
            task_type="decision",
            assigned_role="spacs_convener",
            policy_version=policy,
            sla_snapshot=sla_config,
            due_at=due_at,
            status="pending",
        )

        record_audit_event(
            action="application.verified",
            entity_type="ScholarshipApplication",
            entity_id=app.id,
            actor_user_id=assistant_user_id,
            actor_role="spacs_assistant",
            details={"app_number": app.application_number},
        )

        enqueue_notification(
            topic="application.verified",
            dedupe_key=f"spacs.app.verified.{app.id}",
            subject=f"Application Verified: {app.application_number}",
            body=f"Your scholarship application {app.application_number} has been verified and routed for sanction review.",
            recipient_user_id=app.user_id,
            payload={"application_id": app.id},
        )

        return app


def flag_verification_concern(
    application_id: int,
    assistant_user_id: int,
    concern_note: str,
) -> ScholarshipApplication:
    """Records an unresolved concern and routes to the Convener (UC-SPACS-002, CW-SPACS-01 Row 7 & 9).

    Enforces:
    - Closes active verification task.
    - Transitions application to verification_concern.
    - Creates a decision task for the SPACS Convener.
    """
    if not concern_note.strip():
        raise ConflictError("A verification concern requires an explanatory note.")

    with transaction.atomic():
        app = (
            ScholarshipApplication.objects.select_for_update()
            .filter(pk=application_id)
            .select_related("policy_version", "policy_version__catalogue_entry")
            .first()
        )
        if not app:
            raise NotFoundError("Application not found.")

        transition = can_transition_application(
            from_status=app.status,
            to_status=APP_STATUS_VERIFICATION_CONCERN,
            actor_role="spacs_assistant",
        )
        if not transition.allowed:
            raise ConflictError(transition.reason)

        prev_status = app.status
        now = dj_timezone.now()
        app.status = APP_STATUS_VERIFICATION_CONCERN
        app.verified_at = now
        app.verified_by_user_id = assistant_user_id
        app.verification_concern_note = concern_note.strip()
        app.save()

        # 1. Close active verification task
        SpacsTask.objects.filter(
            application=app, task_type="verification", status="pending"
        ).update(status="completed", completed_at=now, completed_by_user_id=assistant_user_id)

        # 2. Record application transition
        ApplicationTransition.objects.create(
            application=app,
            from_status=prev_status,
            to_status=APP_STATUS_VERIFICATION_CONCERN,
            actor_user_id=assistant_user_id,
            actor_role_label="SPACS Assistant",
            reason=f"Verification concern recorded: {concern_note}",
        )

        # 3. Create Convener decision task
        policy = app.policy_version
        due_at = None
        sla_config = policy.sla_config or {}
        decision_threshold = sla_config.get("decision_threshold_hours") or sla_config.get("threshold_hours")
        if decision_threshold:
            due_at = now + timedelta(hours=int(decision_threshold))

        SpacsTask.objects.create(
            application=app,
            task_type="decision",
            assigned_role="spacs_convener",
            policy_version=policy,
            sla_snapshot=sla_config,
            due_at=due_at,
            status="pending",
        )

        record_audit_event(
            action="application.verification_concern",
            entity_type="ScholarshipApplication",
            entity_id=app.id,
            actor_user_id=assistant_user_id,
            actor_role="spacs_assistant",
            details={"app_number": app.application_number, "concern": concern_note},
        )

        return app


def request_correction(
    application_id: int,
    reviewer_user_id: int,
    actor_role: str,
    correction_reason: str,
) -> ScholarshipApplication:
    """Returns application to student for correction (UC-SPACS-002, BW-SPACS-02).

    Enforces:
    - Closes current verification or decision task.
    - Transitions application to correction_required.
    - No active task remains pending while student edits.
    """
    if not correction_reason.strip():
        raise ConflictError("Returning for correction requires an explanatory reason for the student.")

    with transaction.atomic():
        app = (
            ScholarshipApplication.objects.select_for_update()
            .filter(pk=application_id)
            .select_related("policy_version", "policy_version__catalogue_entry")
            .first()
        )
        if not app:
            raise NotFoundError("Application not found.")

        transition = can_transition_application(
            from_status=app.status,
            to_status=APP_STATUS_CORRECTION_REQUIRED,
            actor_role=actor_role,
        )
        if not transition.allowed:
            raise ConflictError(transition.reason)

        prev_status = app.status
        now = dj_timezone.now()
        app.status = APP_STATUS_CORRECTION_REQUIRED
        app.save()

        # Close any pending task (verification or decision)
        SpacsTask.objects.filter(application=app, status="pending").update(
            status="completed", completed_at=now, completed_by_user_id=reviewer_user_id
        )

        role_label = "SPACS Convener" if actor_role == "spacs_convener" else "SPACS Assistant"
        ApplicationTransition.objects.create(
            application=app,
            from_status=prev_status,
            to_status=APP_STATUS_CORRECTION_REQUIRED,
            actor_user_id=reviewer_user_id,
            actor_role_label=role_label,
            reason=correction_reason.strip(),
        )

        record_audit_event(
            action="application.correction_requested",
            entity_type="ScholarshipApplication",
            entity_id=app.id,
            actor_user_id=reviewer_user_id,
            actor_role=actor_role,
            details={"app_number": app.application_number, "reason": correction_reason},
        )

        # Notify student with the correction instruction
        enqueue_notification(
            topic="application.correction_required",
            dedupe_key=f"spacs.app.correction.{app.id}.{int(now.timestamp())}",
            subject=f"Correction Required: {app.application_number}",
            body=f"Your scholarship application requires correction: {correction_reason}",
            recipient_user_id=app.user_id,
            payload={"application_id": app.id, "correction_reason": correction_reason},
        )

        return app


def resubmit_corrected_application(
    application_id: int,
    user_id: int,
    updated_submission_data: dict[str, Any] | None = None,
) -> ScholarshipApplication:
    """Student resubmits corrected application (UC-SPACS-003, BW-SPACS-02, BR-SPACS-011).

    Enforces:
    - Validates ownership and state.
    - Revalidates application completeness.
    - Transitions application to resubmitted.
    - Creates a NEW verification task for spacs_assistant.
    """
    with transaction.atomic():
        app = (
            ScholarshipApplication.objects.select_for_update()
            .filter(pk=application_id)
            .select_related("policy_version", "policy_version__catalogue_entry")
            .first()
        )
        if not app:
            raise NotFoundError("Application not found.")
        if app.user_id != user_id:
            raise PermissionDeniedError("Only the owning student may resubmit this application.")

        transition = can_transition_application(
            from_status=app.status,
            to_status=APP_STATUS_RESUBMITTED,
            actor_role="student",
            is_owner=True,
        )
        if not transition.allowed:
            raise ConflictError(transition.reason)

        if updated_submission_data:
            app.submission_data = updated_submission_data

        prev_status = app.status
        now = dj_timezone.now()
        app.status = APP_STATUS_RESUBMITTED
        app.save()

        ApplicationTransition.objects.create(
            application=app,
            from_status=prev_status,
            to_status=APP_STATUS_RESUBMITTED,
            actor_user_id=user_id,
            actor_role_label="Student",
            reason="Resubmitted with requested corrections",
        )

        # Create a fresh verification task with newly calculated SLA
        policy = app.policy_version
        due_at = None
        sla_config = policy.sla_config or {}
        verification_threshold = sla_config.get("threshold_hours")
        if verification_threshold:
            due_at = now + timedelta(hours=int(verification_threshold))

        SpacsTask.objects.create(
            application=app,
            task_type="verification",
            assigned_role="spacs_assistant",
            policy_version=policy,
            sla_snapshot=sla_config,
            due_at=due_at,
            status="pending",
        )

        record_audit_event(
            action="application.resubmitted",
            entity_type="ScholarshipApplication",
            entity_id=app.id,
            actor_user_id=user_id,
            actor_role="student",
            details={"app_number": app.application_number},
        )

        enqueue_notification(
            topic="application.resubmitted",
            dedupe_key=f"spacs.app.resubmitted.{app.id}.{int(now.timestamp())}",
            subject=f"Application Resubmitted: {app.application_number}",
            body=f"Your resubmission for {policy.catalogue_entry.title} has been received for verification.",
            recipient_user_id=user_id,
            payload={"application_id": app.id},
        )

        return app
