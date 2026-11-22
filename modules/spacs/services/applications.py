"""Scholarship application service (writes, transitions, validations, audits).

Raises domain errors (ConflictError, NotFoundError, PermissionDeniedError), never DRF exceptions.
"""
from __future__ import annotations

import logging
from typing import Any
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.spacs.domain import state_machine as sm
from modules.spacs.domain.eligibility import evaluate_criteria
from modules.spacs.domain.renewal import evaluate_renewal_eligibility
from modules.spacs.models import (
    ApplicationDocument,
    ApplicationTransition,
    ScholarshipApplication,
    SchemeCatalogue,
    SchemePolicyVersion,
)
from modules.spacs.services.audit import record_audit_event
from modules.spacs.services.notifications import notify

log = logging.getLogger("fusion.spacs.applications")


def _actor_kind(actor, application: ScholarshipApplication | None = None) -> str:
    """Resolves state machine lane for caller."""
    if actor is None:
        return sm.SYSTEM
    # If caller owns the application, they act in the student lane
    if application is not None and application.student_user_id == getattr(actor, "user_id", None):
        return sm.STUDENT
    if actor.has_permission("spacs.application.approve"):
        return sm.CONVENER
    if actor.has_permission("spacs.application.review"):
        return sm.ASSISTANT
    return sm.STUDENT


def create_draft_application(
    *,
    scheme_id: int,
    academic_cycle: str,
    application_data: dict[str, Any] | None = None,
    actor,
) -> ScholarshipApplication:
    """Creates a new draft application (AFR-SPACS-014)."""
    if actor is None or not actor.has_permission("spacs.application.create"):
        raise PermissionDeniedError("Permission denied.")

    scheme = SchemeCatalogue.objects.filter(pk=scheme_id).first()
    if scheme is None:
        raise NotFoundError("Scheme not found.")

    version = (
        SchemePolicyVersion.objects.filter(scheme=scheme, status="published")
        .order_by("-version_number")
        .first()
    )
    if version is None:
        raise ConflictError("No active published policy version found for this scheme.", code="no_policy_version")

    # Guard: Duplicate draft / active application check in cycle (CFR-SPACS-001, BR-SPACS-002)
    existing_active = ScholarshipApplication.objects.filter(
        student_user_id=actor.user_id,
        scheme=scheme,
        academic_cycle=academic_cycle,
    ).exclude(status__in=[sm.WITHDRAWN, sm.REJECTED]).exists()
    if existing_active:
        raise ConflictError(
            f"Duplicate application: You already have an active application for scheme {scheme.code} in cycle {academic_cycle}.",
            code="duplicate_draft",
        )

    # Generate draft application number
    stamp = timezone.now().strftime("%Y%m%d%H%M%S")
    app_num = f"SPACS-{scheme.code.upper()}-DRAFT-{actor.user_id}-{stamp}"

    with transaction.atomic():
        app = ScholarshipApplication.objects.create(
            application_number=app_num,
            student_user_id=actor.user_id,
            scheme=scheme,
            policy_version=version,
            academic_cycle=academic_cycle,
            status=sm.DRAFT,
            application_data=application_data or {},
        )
        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="student",
            action="application.draft_created",
            entity_type="scholarship_application",
            entity_id=str(app.id),
            details={"scheme_code": scheme.code, "cycle": academic_cycle},
        )
        return app


def submit_application(
    *,
    application_id: int,
    application_data: dict[str, Any] | None = None,
    student_facts: dict[str, Any] | None = None,
    actor,
) -> ScholarshipApplication:
    """Submits a scholarship application (UC-SPACS-001, CW-SPACS-01).

    Enforces BR-SPACS-001 (eligibility), BR-SPACS-002 (no duplicates),
    BR-SPACS-004 (completeness), BR-SPACS-014 (policy version).
    """
    if actor is None or not actor.has_permission("spacs.application.create"):
        raise PermissionDeniedError("Permission denied.")

    with transaction.atomic():
        app = (
            ScholarshipApplication.objects.select_for_update()
            .select_related("scheme", "policy_version")
            .filter(pk=application_id)
            .first()
        )
        if app is None:
            raise NotFoundError("Application not found.")

        if app.student_user_id != actor.user_id:
            raise PermissionDeniedError("Cannot submit another student's application.")

        if app.status != sm.DRAFT:
            raise ConflictError(f"Application is in '{app.status}' status, cannot submit.", code="not_in_draft")

        version = app.policy_version
        now = timezone.now()

        # Guard: Window check
        if version.application_window_start and now < version.application_window_start:
            raise ConflictError("Application window has not opened yet.", code="window_not_open")
        if version.application_window_end and now > version.application_window_end:
            raise ConflictError("Application window has closed.", code="window_closed")

        # Guard: BR-SPACS-002: No Duplicate active applications
        existing_active = ScholarshipApplication.objects.filter(
            student_user_id=actor.user_id,
            scheme=app.scheme,
            academic_cycle=app.academic_cycle,
        ).exclude(pk=app.pk).exclude(status__in=[sm.DRAFT, sm.WITHDRAWN, sm.REJECTED]).exists()

        if existing_active:
            raise ConflictError(
                f"You already have an active or submitted application for {app.scheme.name} in cycle {app.academic_cycle}.",
                code="duplicate_application",
            )

        # Merge data
        data = {**app.application_data, **(application_data or {})}
        facts = student_facts or data

        # Guard: BR-SPACS-001: Machine-checkable eligibility check
        eligibility = evaluate_criteria(version.eligibility_criteria, facts)
        if not eligibility.is_eligible:
            reasons = "; ".join(eligibility.failed_reasons)
            raise ConflictError(
                f"Eligibility criteria not satisfied: {reasons}",
                code="eligibility_failed",
                details=[{"criterion": o.criterion, "reason": o.reason} for o in eligibility.outcomes if not o.passed],
            )

        # Guard: BR-SPACS-004: Required documents check
        required_docs = [d["type"] for d in version.required_documents if d.get("required", True)]
        if required_docs:
            uploaded_types = set(
                ApplicationDocument.objects.filter(application=app).values_list("doc_type", flat=True)
            )
            missing_docs = [rt for rt in required_docs if rt not in uploaded_types]
            if missing_docs:
                raise ConflictError(
                    f"Missing required documents: {', '.join(missing_docs)}",
                    code="missing_documents",
                    details=[{"missing": missing_docs}],
                )

        # Valid transition: DRAFT -> SUBMITTED
        sm.resolve(sm.DRAFT, sm.SUBMITTED, sm.STUDENT)

        app.application_number = f"SPACS-{now.year}-{app.id:05d}"
        app.status = sm.SUBMITTED
        app.submitted_at = now
        app.application_data = data
        app.eligibility_snapshot = {
            "is_eligible": eligibility.is_eligible,
            "checked_at": now.isoformat(),
            "outcomes": [
                {
                    "criterion": o.criterion,
                    "passed": o.passed,
                    "actual": o.actual,
                    "reason": o.reason,
                }
                for o in eligibility.outcomes
            ],
        }
        app.save()

        # Audit transition
        ApplicationTransition.objects.create(
            application=app,
            from_status=sm.DRAFT,
            to_status=sm.SUBMITTED,
            actor_user_id=actor.user_id,
            actor_role="student",
            reason="Submitted by student",
        )

        # Notify student (BR-SPACS-008, AFR-SPACS-018)
        notify(
            recipient_user_id=actor.user_id,
            recipient_role="student",
            event_type="application.submitted",
            title=f"Application {app.application_number} Submitted",
            message=f"Your application for {app.scheme.name} ({app.academic_cycle}) was successfully submitted.",
            reference_id=str(app.id),
        )

        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="student",
            action="application.submitted",
            entity_type="scholarship_application",
            entity_id=str(app.id),
            details={"application_number": app.application_number},
        )
        return app


def modify_application(
    *,
    application_id: int,
    updated_data: dict[str, Any] | None = None,
    resubmit: bool = False,
    actor,
) -> ScholarshipApplication:
    """Modifies or resubmits an application in editable state (UC-SPACS-003, BR-SPACS-010, BR-SPACS-011)."""
    if actor is None:
        raise PermissionDeniedError("Authentication required.")

    with transaction.atomic():
        app = (
            ScholarshipApplication.objects.select_for_update()
            .select_related("scheme", "policy_version")
            .filter(pk=application_id)
            .first()
        )
        if app is None:
            raise NotFoundError("Application not found.")

        # BR-SPACS-010: Owner only
        if app.student_user_id != actor.user_id:
            raise PermissionDeniedError("Only the owning student can modify an application.")

        # AFR-SPACS-031: Must be in configured editable state
        if app.status not in sm.EDITABLE:
            raise ConflictError(
                f"Application is in '{app.status}' status and cannot be modified.",
                code="non_editable_state",
            )

        if updated_data:
            app.application_data = {**app.application_data, **updated_data}

        # If resubmitting after correction
        if resubmit or app.status == sm.CORRECTION_REQUIRED:
            from_st = app.status
            to_st = sm.RESUBMITTED

            sm.resolve(from_st, to_st, sm.STUDENT)

            # BR-SPACS-011: Clear prior verification findings invalidated by correction
            # Re-evaluate eligibility snapshot with updated facts
            facts = app.application_data or {}
            re_eval = evaluate_criteria(app.policy_version.eligibility_criteria, facts)
            app.eligibility_snapshot = {
                "is_eligible": re_eval.is_eligible,
                "checked_at": timezone.now().isoformat(),
                "outcomes": [
                    {
                        "criterion": o.criterion,
                        "passed": o.passed,
                        "actual": o.actual,
                        "reason": o.reason,
                    }
                    for o in re_eval.outcomes
                ],
            }

            app.status = to_st
            app.resubmitted_at = timezone.now()
            app.verification_findings = {}
            app.correction_requested_reason = ""
            app.save()

            ApplicationTransition.objects.create(
                application=app,
                from_status=from_st,
                to_status=to_st,
                actor_user_id=actor.user_id,
                actor_role="student",
                reason="Corrected application resubmitted by student",
            )

            record_audit_event(
                actor_user_id=actor.user_id,
                actor_role="student",
                action="application.resubmitted",
                entity_type="scholarship_application",
                entity_id=str(app.id),
                details={"application_number": app.application_number},
            )
        else:
            app.save(update_fields=["application_data", "updated_at"])

        return app


def withdraw_application(
    *,
    application_id: int,
    reason: str = "",
    actor,
) -> ScholarshipApplication:
    """Withdraws a pending application before final decision (UC-SPACS-004, BR-SPACS-009, BR-SPACS-010)."""
    if actor is None or not actor.has_permission("spacs.application.delete"):
        raise PermissionDeniedError("Permission denied.")

    with transaction.atomic():
        app = ScholarshipApplication.objects.select_for_update().filter(pk=application_id).first()
        if app is None:
            raise NotFoundError("Application not found.")

        # BR-SPACS-010: Owner only
        if app.student_user_id != actor.user_id:
            raise PermissionDeniedError("Only the owning student can withdraw their application.")

        # BR-SPACS-009: Check withdrawable state
        if app.status not in sm.WITHDRAWABLE:
            raise ConflictError(
                f"Application is in '{app.status}' status and cannot be withdrawn.",
                code="cannot_withdraw",
            )

        sm.resolve(app.status, sm.WITHDRAWN, sm.STUDENT)

        from_st = app.status
        app.status = sm.WITHDRAWN
        app.withdrawn_at = timezone.now()
        app.withdrawal_reason = reason
        app.save(update_fields=["status", "withdrawn_at", "withdrawal_reason", "updated_at"])

        ApplicationTransition.objects.create(
            application=app,
            from_status=from_st,
            to_status=sm.WITHDRAWN,
            actor_user_id=actor.user_id,
            actor_role="student",
            reason=reason or "Withdrawn by student",
        )

        notify(
            recipient_user_id=actor.user_id,
            recipient_role="student",
            event_type="application.withdrawn",
            title=f"Application {app.application_number} Withdrawn",
            message=f"Your application has been withdrawn.",
            reference_id=str(app.id),
        )

        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="student",
            action="application.withdrawn",
            entity_type="scholarship_application",
            entity_id=str(app.id),
            details={"reason": reason},
        )
        return app


def verify_application(
    *,
    application_id: int,
    action_type: str,  # "start", "verify", "request_correction", "record_concern"
    findings: dict[str, Any] | None = None,
    reason: str = "",
    actor,
) -> ScholarshipApplication:
    """SPACS Assistant verification handling (UC-SPACS-002, BR-SPACS-006).

    Assistant does NOT make final approval/rejection decisions!
    """
    if actor is None or not actor.has_permission("spacs.application.review"):
        raise PermissionDeniedError("Only authorized SPACS Assistant may verify applications.")

    with transaction.atomic():
        app = ScholarshipApplication.objects.select_for_update().filter(pk=application_id).first()
        if app is None:
            raise NotFoundError("Application not found.")

        from_st = app.status

        if action_type == "start":
            # Move from submitted/resubmitted to under_verification
            target = sm.UNDER_VERIFICATION
            sm.resolve(from_st, target, sm.ASSISTANT)
            app.status = target
            app.assigned_assistant_user_id = actor.user_id
            app.save(update_fields=["status", "assigned_assistant_user_id", "updated_at"])

        elif action_type == "verify":
            # Mark verified -> routes to Convener
            target = sm.VERIFIED
            sm.resolve(from_st, target, sm.ASSISTANT)
            app.status = target
            app.verified_at = timezone.now()
            app.verified_by_user_id = actor.user_id
            if findings:
                app.verification_findings = findings
            app.save(update_fields=["status", "verified_at", "verified_by_user_id", "verification_findings", "updated_at"])

            notify(
                recipient_user_id=app.student_user_id,
                recipient_role="student",
                event_type="application.verified",
                title="Application Verified",
                message=f"Your application {app.application_number} has been verified and routed for Convener decision.",
                reference_id=str(app.id),
            )

        elif action_type == "request_correction":
            # Return for correction
            if not (reason or "").strip():
                raise ConflictError("A correction reason is required.", code="reason_required")
            target = sm.CORRECTION_REQUIRED
            sm.resolve(from_st, target, sm.ASSISTANT)
            app.status = target
            app.correction_requested_reason = reason
            app.correction_requested_at = timezone.now()
            if findings:
                app.verification_findings = findings
            app.save(update_fields=["status", "correction_requested_reason", "correction_requested_at", "verification_findings", "updated_at"])

            notify(
                recipient_user_id=app.student_user_id,
                recipient_role="student",
                event_type="application.correction_requested",
                title="Correction Requested on Application",
                message=f"Correction requested on your application {app.application_number}: {reason}",
                reference_id=str(app.id),
            )

        elif action_type == "record_concern":
            # Record verification concern -> routes to Convener (BR-SPACS-006, AFR-SPACS-025)
            if not (reason or "").strip():
                raise ConflictError("Details of the verification concern are required.", code="concern_details_required")
            target = sm.VERIFICATION_CONCERN
            sm.resolve(from_st, target, sm.ASSISTANT)
            app.status = target
            app.verification_concern_details = reason
            if findings:
                app.verification_findings = findings
            app.save(update_fields=["status", "verification_concern_details", "verification_findings", "updated_at"])

            notify(
                recipient_user_id=1,
                recipient_role="spacs_convener",
                event_type="application.verification_concern",
                title="Verification Concern Escalated",
                message=f"A verification concern was recorded on application {app.application_number}: {reason}",
                reference_id=str(app.id),
            )

        else:
            raise BadRequestError(f"Unknown verification action: {action_type}")

        ApplicationTransition.objects.create(
            application=app,
            from_status=from_st,
            to_status=app.status,
            actor_user_id=actor.user_id,
            actor_role="spacs_assistant",
            reason=reason or f"Verification action: {action_type}",
        )

        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="spacs_assistant",
            action=f"application.verification.{action_type}",
            entity_type="scholarship_application",
            entity_id=str(app.id),
            details={"from_status": from_st, "to_status": app.status, "reason": reason},
        )
        return app


def decide_application(
    *,
    application_id: int,
    decision: str,  # "approve", "reject", "return_correction"
    reason: str = "",
    actor,
) -> ScholarshipApplication:
    """SPACS Convener final scholarship decision (UC-SPACS-006, BR-SPACS-018)."""
    if actor is None or not actor.has_permission("spacs.application.approve"):
        raise PermissionDeniedError("Only the SPACS Convener may make scholarship decisions.")

    with transaction.atomic():
        app = ScholarshipApplication.objects.select_for_update().filter(pk=application_id).first()
        if app is None:
            raise NotFoundError("Application not found.")

        from_st = app.status
        now = timezone.now()

        if decision == "approve":
            target = sm.APPROVED
            sm.resolve(from_st, target, sm.CONVENER)
            app.status = target
            app.decision_outcome = "approved"
            app.decision_reason = reason
            app.decided_at = now
            app.decided_by_user_id = actor.user_id
            app.save(update_fields=["status", "decision_outcome", "decision_reason", "decided_at", "decided_by_user_id", "updated_at"])

            notify(
                recipient_user_id=app.student_user_id,
                recipient_role="student",
                event_type="application.approved",
                title="Scholarship Approved",
                message=f"Congratulations! Your application {app.application_number} for {app.scheme.name} has been approved.",
                reference_id=str(app.id),
            )

        elif decision == "reject":
            if not (reason or "").strip():
                raise ConflictError("A reason is required for rejection.", code="reason_required")
            target = sm.REJECTED
            sm.resolve(from_st, target, sm.CONVENER)
            app.status = target
            app.decision_outcome = "rejected"
            app.decision_reason = reason
            app.decided_at = now
            app.decided_by_user_id = actor.user_id
            app.save(update_fields=["status", "decision_outcome", "decision_reason", "decided_at", "decided_by_user_id", "updated_at"])

            notify(
                recipient_user_id=app.student_user_id,
                recipient_role="student",
                event_type="application.rejected",
                title="Scholarship Decision",
                message=f"Your application {app.application_number} has not been approved. Reason: {reason}",
                reference_id=str(app.id),
            )

        elif decision == "return_correction":
            if not (reason or "").strip():
                raise ConflictError("A reason is required to return for correction.", code="reason_required")
            target = sm.CORRECTION_REQUIRED
            sm.resolve(from_st, target, sm.CONVENER)
            app.status = target
            app.correction_requested_reason = reason
            app.correction_requested_at = now
            app.save(update_fields=["status", "correction_requested_reason", "correction_requested_at", "updated_at"])

            notify(
                recipient_user_id=app.student_user_id,
                recipient_role="student",
                event_type="application.correction_requested",
                title="Correction Requested by Convener",
                message=f"Convener requested correction on {app.application_number}: {reason}",
                reference_id=str(app.id),
            )

        else:
            raise BadRequestError(f"Unknown decision: {decision}")

        ApplicationTransition.objects.create(
            application=app,
            from_status=from_st,
            to_status=app.status,
            actor_user_id=actor.user_id,
            actor_role="spacs_convener",
            reason=reason or f"Decision: {decision}",
        )

        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="spacs_convener",
            action=f"application.decision.{decision}",
            entity_type="scholarship_application",
            entity_id=str(app.id),
            details={"decision": decision, "reason": reason, "application_number": app.application_number},
        )
        return app


def submit_renewal(
    *,
    prior_application_id: int,
    academic_cycle: str,
    renewal_data: dict[str, Any] | None = None,
    current_facts: dict[str, Any] | None = None,
    actor,
) -> ScholarshipApplication:
    """Submits a scholarship renewal application (UC-SPACS-015, CW-SPACS-02, BR-SPACS-017)."""
    if actor is None or not actor.has_permission("spacs.application.create"):
        raise PermissionDeniedError("Permission denied.")

    prior = (
        ScholarshipApplication.objects.select_related("scheme", "policy_version")
        .filter(pk=prior_application_id)
        .first()
    )
    if prior is None:
        raise NotFoundError("Prior scholarship application not found.")

    if prior.student_user_id != actor.user_id:
        raise PermissionDeniedError("You can only renew your own awarded scholarship.")

    scheme = prior.scheme
    version = (
        SchemePolicyVersion.objects.filter(scheme=scheme, status="published")
        .order_by("-version_number")
        .first()
    )
    if version is None:
        raise ConflictError("No active published policy version for this scheme.", code="no_policy_version")

    now = timezone.now()
    window_open = True
    if version.renewal_window_start and now < version.renewal_window_start:
        window_open = False
    if version.renewal_window_end and now > version.renewal_window_end:
        window_open = False

    # Count prior renewals
    renewal_count = ScholarshipApplication.objects.filter(
        student_user_id=actor.user_id,
        scheme=scheme,
        is_renewal=True,
    ).count()

    eval_result = evaluate_renewal_eligibility(
        is_renewable=version.is_renewable,
        prior_application_status=prior.status,
        renewal_window_open=window_open,
        renewal_rules=version.renewal_rules,
        current_facts=current_facts or renewal_data or {},
        previous_renewal_count=renewal_count,
    )

    if not eval_result.can_renew:
        reasons = "; ".join(eval_result.reasons)
        raise ConflictError(f"Renewal not permitted: {reasons}", code="renewal_ineligible")

    # Prevent duplicate active renewal
    existing_active = ScholarshipApplication.objects.filter(
        student_user_id=actor.user_id,
        scheme=scheme,
        academic_cycle=academic_cycle,
    ).exclude(status__in=[sm.WITHDRAWN, sm.REJECTED]).exists()
    if existing_active:
        raise ConflictError(
            f"An active application or renewal already exists for cycle {academic_cycle}.",
            code="duplicate_application",
        )

    # Prefill reusable data from prior application
    merged_data = {}
    for k in eval_result.prefill_fields:
        if k in prior.application_data:
            merged_data[k] = prior.application_data[k]
    merged_data.update(renewal_data or {})

    stamp = now.strftime("%Y%m%d%H%M%S")
    app_num = f"SPACS-{now.year}-REN-{actor.user_id}-{stamp}"

    with transaction.atomic():
        renewal_app = ScholarshipApplication.objects.create(
            application_number=app_num,
            student_user_id=actor.user_id,
            scheme=scheme,
            policy_version=version,
            academic_cycle=academic_cycle,
            is_renewal=True,
            prior_application_id=prior.id,
            status=sm.SUBMITTED,
            submitted_at=now,
            application_data=merged_data,
        )

        ApplicationTransition.objects.create(
            application=renewal_app,
            from_status=sm.DRAFT,
            to_status=sm.SUBMITTED,
            actor_user_id=actor.user_id,
            actor_role="student",
            reason="Renewal submitted by student",
        )

        notify(
            recipient_user_id=actor.user_id,
            recipient_role="student",
            event_type="renewal.submitted",
            title=f"Renewal Application {renewal_app.application_number} Submitted",
            message=f"Your renewal application for {scheme.name} ({academic_cycle}) was received.",
            reference_id=str(renewal_app.id),
        )

        record_audit_event(
            actor_user_id=actor.user_id,
            actor_role="student",
            action="application.renewal_submitted",
            entity_type="scholarship_application",
            entity_id=str(renewal_app.id),
            details={"prior_id": prior.id, "cycle": academic_cycle},
        )
        return renewal_app
