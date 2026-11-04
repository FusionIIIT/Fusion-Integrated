"""Scholarship application lifecycle services for SPACS.

Enforces:
- CFR-SPACS-003, CFR-SPACS-004, CFR-SPACS-005, CFR-SPACS-009, CFR-SPACS-010
- BR-SPACS-001 (Machine eligibility)
- BR-SPACS-002 (No duplicate active applications)
- BR-SPACS-004 (Completeness validation)
- BR-SPACS-007 (Server-side draft persistence)
- BR-SPACS-009 / BR-SPACS-010 (Withdrawal and ownership constraints)
- UC-SPACS-001, 003, 004
- BW-SPACS-01, BW-SPACS-05, CW-SPACS-01
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone as dj_timezone

from core.api.exceptions import ValidationError, NotFoundError, PermissionDenied
from core.files.drive import parse as parse_drive_url, InvalidDriveLink
from modules.spacs.domain.eligibility import evaluate_machine_eligibility
from modules.spacs.domain.state_machines import (
    APP_STATUS_DRAFT,
    APP_STATUS_SUBMITTED,
    APP_STATUS_CORRECTION_REQUIRED,
    APP_STATUS_WITHDRAWN,
    ACTIVE_APPLICATION_STATUSES,
    can_transition_application,
)
from modules.spacs.models import (
    ScholarshipApplication,
    ApplicationDocument,
    ApplicationTransition,
    CataloguePolicyVersion,
    SpacsTask,
)
from modules.spacs.services.audit import record_audit_event
from modules.spacs.services.notifications import enqueue as enqueue_notification


def generate_application_number(entry_code: str, cycle: str) -> str:
    short_uid = uuid.uuid4().hex[:6].upper()
    return f"SPACS-{entry_code[:6].upper()}-{cycle}-{short_uid}"


def save_draft(
    user_id: int,
    policy_version: CataloguePolicyVersion,
    academic_cycle: str,
    submission_data: dict[str, Any],
    documents: list[dict[str, Any]] | None = None,
    application_id: int | None = None,
    applicant_snapshot: dict[str, Any] | None = None,
) -> ScholarshipApplication:
    """Creates or updates a server-side recoverable application draft (BR-SPACS-007)."""
    with transaction.atomic():
        if application_id:
            application = ScholarshipApplication.objects.select_for_update().filter(pk=application_id).first()
            if not application:
                raise NotFoundError("Application draft not found.")
            if application.user_id != user_id:
                raise PermissionDenied("You do not own this application.")
            if application.status != APP_STATUS_DRAFT:
                raise ValidationError(f"Cannot edit draft in status '{application.status}'.")

            application.submission_data = submission_data
            if applicant_snapshot:
                application.applicant_snapshot = applicant_snapshot
            application.save()
        else:
            app_num = generate_application_number(
                policy_version.catalogue_entry.code, academic_cycle
            )
            application = ScholarshipApplication.objects.create(
                application_number=app_num,
                user_id=user_id,
                policy_version=policy_version,
                academic_cycle=academic_cycle,
                status=APP_STATUS_DRAFT,
                submission_data=submission_data,
                applicant_snapshot=applicant_snapshot or {},
            )

        # Sync documents if provided
        if documents is not None:
            _sync_application_documents(application, user_id, documents)

        return application


def submit_application(
    application_id: int,
    user_id: int,
    student_snapshot: dict[str, Any],
) -> ScholarshipApplication:
    """Submits a drafted scholarship application (UC-SPACS-001, BW-SPACS-01)."""
    with transaction.atomic():
        application = (
            ScholarshipApplication.objects.select_for_update()
            .filter(pk=application_id)
            .select_related("policy_version", "policy_version__catalogue_entry")
            .first()
        )
        if not application:
            raise NotFoundError("Application not found.")
        if application.user_id != user_id:
            raise PermissionDenied("You can only submit your own application.")

        transition = can_transition_application(
            from_status=application.status,
            to_status=APP_STATUS_SUBMITTED,
            actor_role="student",
            is_owner=True,
        )
        if not transition.allowed:
            raise ValidationError(transition.reason)

        policy = application.policy_version

        # 1. BR-SPACS-002: Check duplicate active application
        duplicates = ScholarshipApplication.objects.filter(
            policy_version=policy,
            user_id=user_id,
            academic_cycle=application.academic_cycle,
            status__in=ACTIVE_APPLICATION_STATUSES,
        ).exclude(pk=application.pk)
        if duplicates.exists():
            raise ValidationError("You already have an active application for this scholarship and cycle.")

        # 2. BR-SPACS-001: Machine-checkable eligibility evaluation
        combined_snapshot = {**application.applicant_snapshot, **student_snapshot}
        is_eligible, deficiencies = evaluate_machine_eligibility(
            policy.eligibility_schema, combined_snapshot
        )
        if not is_eligible:
            raise ValidationError(
                f"Eligibility criteria not satisfied: {'; '.join(deficiencies)}"
            )

        # 3. BR-SPACS-004: Validate completeness of mandatory evidence
        required_schema = policy.required_evidence_schema or []
        attached_doc_types = set(
            application.documents.values_list("doc_type", flat=True)
        )
        missing_docs = [
            req["doc_type"]
            for req in required_schema
            if req.get("mandatory", True) and req["doc_type"] not in attached_doc_types
        ]
        if missing_docs:
            raise ValidationError(f"Missing mandatory supporting evidence: {', '.join(missing_docs)}")

        # Transition application to Submitted
        prev_status = application.status
        now = dj_timezone.now()
        application.status = APP_STATUS_SUBMITTED
        application.submitted_at = now
        application.applicant_snapshot = combined_snapshot
        application.save()

        # Record Transition (BR-SPACS-021)
        ApplicationTransition.objects.create(
            application=application,
            from_status=prev_status,
            to_status=APP_STATUS_SUBMITTED,
            actor_user_id=user_id,
            actor_role_label="Student",
            reason="Submitted by applicant",
        )

        # Compute SLA due_at from policy snapshot
        due_at = None
        sla_config = policy.sla_config or {}
        verification_threshold = sla_config.get("threshold_hours")
        if verification_threshold:
            due_at = now + timedelta(hours=int(verification_threshold))

        # Create Assistant Verification Task (UC-SPACS-001, AFR-SPACS-017)
        SpacsTask.objects.create(
            application=application,
            task_type="verification",
            assigned_role="spacs_assistant",
            policy_version=policy,
            sla_snapshot=sla_config,
            due_at=due_at,
            status="pending",
        )

        record_audit_event(
            action="application.submitted",
            entity_type="ScholarshipApplication",
            entity_id=application.id,
            actor_user_id=user_id,
            actor_role="student",
            details={
                "app_number": application.application_number,
                "scheme": policy.catalogue_entry.code,
                "cycle": application.academic_cycle,
            },
        )

        # Outbox notification with deduplication key (CFR-SPACS-005, AFR-SPACS-018)
        enqueue_notification(
            topic="application.submitted",
            dedupe_key=f"spacs.app.submitted.{application.id}",
            subject=f"Scholarship Application Submitted: {application.application_number}",
            body=f"Your application {application.application_number} for {policy.catalogue_entry.title} has been submitted successfully.",
            recipient_user_id=user_id,
            payload={"application_id": application.id},
        )

        return application


def withdraw_application(
    application_id: int,
    user_id: int,
    reason: str = "",
) -> ScholarshipApplication:
    """Withdraws a pending scholarship application (UC-SPACS-004, BW-SPACS-05, BR-SPACS-009)."""
    with transaction.atomic():
        application = (
            ScholarshipApplication.objects.select_for_update()
            .filter(pk=application_id)
            .select_related("policy_version", "policy_version__catalogue_entry")
            .first()
        )
        if not application:
            raise NotFoundError("Application not found.")
        if application.user_id != user_id:
            raise PermissionDenied("Only the owning student may withdraw an application.")

        transition = can_transition_application(
            from_status=application.status,
            to_status=APP_STATUS_WITHDRAWN,
            actor_role="student",
            is_owner=True,
        )
        if not transition.allowed:
            raise ValidationError(transition.reason)

        prev_status = application.status
        now = dj_timezone.now()
        application.status = APP_STATUS_WITHDRAWN
        application.withdrawn_at = now
        application.withdrawn_reason = reason.strip()
        application.save()

        # AFR-SPACS-034: Close pending tasks
        SpacsTask.objects.filter(application=application, status="pending").update(
            status="cancelled", completed_at=now
        )

        ApplicationTransition.objects.create(
            application=application,
            from_status=prev_status,
            to_status=APP_STATUS_WITHDRAWN,
            actor_user_id=user_id,
            actor_role_label="Student",
            reason=reason or "Withdrawn by student",
        )

        record_audit_event(
            action="application.withdrawn",
            entity_type="ScholarshipApplication",
            entity_id=application.id,
            actor_user_id=user_id,
            actor_role="student",
            details={"app_number": application.application_number, "reason": reason},
        )

        enqueue_notification(
            topic="application.withdrawn",
            dedupe_key=f"spacs.app.withdrawn.{application.id}",
            subject=f"Application Withdrawn: {application.application_number}",
            body=f"Your application {application.application_number} has been withdrawn.",
            recipient_user_id=user_id,
            payload={"application_id": application.id},
        )

        return application


def _sync_application_documents(
    application: ScholarshipApplication,
    user_id: int,
    documents: list[dict[str, Any]],
):
    """Parses Drive links and updates attached application documents."""
    for doc_data in documents:
        raw_url = doc_data.get("drive_url", "")
        doc_type = doc_data.get("doc_type", "")
        title = doc_data.get("title", doc_type)
        validity = doc_data.get("declared_validity_date")
        is_reused = doc_data.get("is_reused", False)
        reused_id = doc_data.get("reused_from_doc_id")

        if not raw_url:
            continue

        try:
            drive_ref = parse_drive_url(raw_url)
        except InvalidDriveLink as exc:
            raise ValidationError(f"Invalid Google Drive link for {doc_type}: {exc.message}")

        ApplicationDocument.objects.update_or_create(
            application=application,
            doc_type=doc_type,
            defaults={
                "user_id": user_id,
                "title": title,
                "drive_file_id": drive_ref.file_id,
                "drive_url": drive_ref.url,
                "declared_validity_date": validity,
                "is_reused": is_reused,
                "reused_from_doc_id": reused_id,
                "verification_status": "pending",
            },
        )
