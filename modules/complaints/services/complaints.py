"""Core transactional services for Complaint Management System."""
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Sequence
from django.db import transaction
from django.utils import timezone

from modules.complaints.domain.entities import (
    ComplaintPriority,
    ComplaintStatus,
    EscalationType,
    ReopeningStatus,
)
from modules.complaints.domain.errors import (
    PermissionDenied,
    RuleViolation,
)
from modules.complaints.domain.state_machine import validate_transition
from modules.complaints.domain.validation import (
    validate_attachment,
    validate_escalation_eligibility,
    validate_feedback_eligibility,
    validate_priority,
    validate_reopening_eligibility,
    validate_role_assignment,
    validate_submission_fields,
)
from modules.complaints.models import (
    CMSRoleAssignment,
    ClosureVerification,
    Complaint,
    ComplaintAnnouncement,
    ComplaintAssignment,
    ComplaintAttachment,
    ComplaintFeedback,
    ProgressUpdate,
    ReopeningRequest,
    SLAPolicy,
    StatusHistoryEntry,
)
from modules.complaints.services.notifications import emit_notification_event


DEFAULT_SLA_HOURS = {
    ComplaintPriority.HIGH.value: 24,
    ComplaintPriority.MEDIUM.value: 48,
    ComplaintPriority.LOW.value: 72,
}


def _get_sla_deadline(priority: str) -> timezone.datetime:
    """Calculate SLA deadline based on configured policy or defaults."""
    policy = SLAPolicy.objects.filter(priority=priority).first()
    hours = policy.duration_hours if policy else DEFAULT_SLA_HOURS.get(priority, 72)
    return timezone.now() + timedelta(hours=hours)


def submit_complaint(
    *,
    complainant_user_id: int,
    category: str,
    description: str,
    priority: str = "low",
    attachments: Sequence[dict] | None = None,
) -> Complaint:
    """Submit a new complaint (CFR-CMS-001, AFR-CMS-001..010)."""
    validate_submission_fields(category, description)
    validated_priority = validate_priority(priority)

    if attachments:
        for att in attachments:
            validate_attachment(att.get("file_name", ""), att.get("file_size", 0))

    with transaction.atomic():
        # Generate unique human-readable complaint ID (CMP-YYYY-XXXXX)
        year = timezone.now().year
        unique_token = uuid.uuid4().hex[:6].upper()
        complaint_id_str = f"CMP-{year}-{unique_token}"

        complaint = Complaint.objects.create(
            complaint_id=complaint_id_str,
            complainant_user_id=complainant_user_id,
            category=category.strip(),
            description=description.strip(),
            priority=validated_priority.value,
            status=ComplaintStatus.SUBMITTED.value,
            sla_deadline=_get_sla_deadline(validated_priority.value),
        )

        if attachments:
            for att in attachments:
                ComplaintAttachment.objects.create(
                    complaint=complaint,
                    file_name=att.get("file_name", ""),
                    file_size=att.get("file_size", 0),
                    content_type=att.get("content_type", "application/octet-stream"),
                    file_path=att.get("file_path", ""),
                )

        StatusHistoryEntry.objects.create(
            complaint=complaint,
            from_status="none",
            to_status=ComplaintStatus.SUBMITTED.value,
            changed_by_user_id=complainant_user_id,
            reason="Complaint submitted",
        )

        emit_notification_event(
            "complaints.complaint.submitted",
            {
                "complaint_id": complaint.complaint_id,
                "category": complaint.category,
                "status": complaint.status,
            },
            recipient_user_id=complainant_user_id,
        )

    return complaint


def setup_handling(
    *,
    complaint_id: int,
    principal,
    handler_user_id: int,
    category: str | None = None,
    priority: str | None = None,
) -> Complaint:
    """Assign, categorize, and prioritize complaint (CFR-CMS-002, AFR-CMS-011..015, UC-CMS-004)."""
    if not principal.has_perm("complaints.complaint.assign"):
        raise PermissionDenied("complaints.complaint.assign")

    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().get(pk=complaint_id)

        if category and category.strip():
            complaint.category = category.strip()

        if priority:
            validated_priority = validate_priority(priority)
            complaint.priority = validated_priority.value
            complaint.sla_deadline = _get_sla_deadline(validated_priority.value)

        complaint.assigned_handler_id = handler_user_id
        
        # Advance status to in_progress if currently submitted
        if complaint.status == ComplaintStatus.SUBMITTED.value:
            validate_transition(complaint.status, ComplaintStatus.IN_PROGRESS, permissions={"*"})
            complaint.status = ComplaintStatus.IN_PROGRESS.value
            StatusHistoryEntry.objects.create(
                complaint=complaint,
                from_status=ComplaintStatus.SUBMITTED.value,
                to_status=ComplaintStatus.IN_PROGRESS.value,
                changed_by_user_id=principal.erp_user_id,
                reason=f"Assigned to handler {handler_user_id}",
            )

        complaint.save()

        ComplaintAssignment.objects.create(
            complaint=complaint,
            handler_user_id=handler_user_id,
            assigned_by_user_id=principal.erp_user_id,
            category=complaint.category,
            priority=complaint.priority,
        )

        emit_notification_event(
            "complaints.complaint.assigned",
            {
                "complaint_id": complaint.complaint_id,
                "handler_user_id": handler_user_id,
                "priority": complaint.priority,
            },
            recipient_user_id=handler_user_id,
        )

    return complaint


def update_progress(
    *,
    complaint_id: int,
    principal,
    notes: str,
) -> ProgressUpdate:
    """Record progress update on a complaint (CFR-CMS-003, AFR-CMS-019, 021, UC-CMS-005)."""
    if not principal.has_perm("complaints.complaint.update"):
        raise PermissionDenied("complaints.complaint.update")

    if not notes or not notes.strip():
        raise RuleViolation("Progress update notes cannot be empty.", code="empty_progress_notes")

    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().get(pk=complaint_id)

        # If submitted, move to in_progress
        if complaint.status == ComplaintStatus.SUBMITTED.value:
            validate_transition(complaint.status, ComplaintStatus.IN_PROGRESS, permissions={"*"})
            complaint.status = ComplaintStatus.IN_PROGRESS.value
            complaint.save(update_fields=["status", "updated_at"])
            StatusHistoryEntry.objects.create(
                complaint=complaint,
                from_status=ComplaintStatus.SUBMITTED.value,
                to_status=ComplaintStatus.IN_PROGRESS.value,
                changed_by_user_id=principal.erp_user_id,
                reason="Work started on complaint",
            )

        progress = ProgressUpdate.objects.create(
            complaint=complaint,
            user_id=principal.erp_user_id,
            notes=notes.strip(),
        )

        emit_notification_event(
            "complaints.complaint.status_changed",
            {
                "complaint_id": complaint.complaint_id,
                "status": complaint.status,
                "notes": notes.strip(),
            },
            recipient_user_id=complaint.complainant_user_id,
        )

    return progress


def resolve_complaint(
    *,
    complaint_id: int,
    principal,
    resolution_details: str,
) -> Complaint:
    """Resolve a complaint with resolution details (CFR-CMS-004, AFR-CMS-023, UC-CMS-006, BR-CMS-013)."""
    if not principal.has_perm("complaints.complaint.resolve"):
        raise PermissionDenied("complaints.complaint.resolve")

    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        validate_transition(
            complaint.status,
            ComplaintStatus.RESOLVED.value,
            permissions={"*"},
            resolution_details=resolution_details,
        )

        from_status = complaint.status
        complaint.status = ComplaintStatus.RESOLVED.value
        complaint.resolution_details = resolution_details.strip()
        complaint.resolved_at = timezone.now()
        complaint.save()

        StatusHistoryEntry.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=ComplaintStatus.RESOLVED.value,
            changed_by_user_id=principal.erp_user_id,
            reason=f"Resolved: {resolution_details.strip()}",
        )

        emit_notification_event(
            "complaints.complaint.resolved",
            {
                "complaint_id": complaint.complaint_id,
                "resolution_details": complaint.resolution_details,
                "resolved_at": complaint.resolved_at.isoformat(),
            },
            recipient_user_id=complaint.complainant_user_id,
        )

    return complaint


def reject_complaint(
    *,
    complaint_id: int,
    principal,
    rejection_reason: str,
) -> Complaint:
    """Reject a complaint with reason (CFR-CMS-004, AFR-CMS-024, UC-CMS-006, BR-CMS-014)."""
    if not principal.has_perm("complaints.complaint.reject"):
        raise PermissionDenied("complaints.complaint.reject")

    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        validate_transition(
            complaint.status,
            ComplaintStatus.REJECTED.value,
            permissions={"*"},
            rejection_reason=rejection_reason,
        )

        from_status = complaint.status
        complaint.status = ComplaintStatus.REJECTED.value
        complaint.rejection_reason = rejection_reason.strip()
        complaint.rejected_at = timezone.now()
        complaint.save()

        StatusHistoryEntry.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=ComplaintStatus.REJECTED.value,
            changed_by_user_id=principal.erp_user_id,
            reason=f"Rejected: {rejection_reason.strip()}",
        )

        emit_notification_event(
            "complaints.complaint.rejected",
            {
                "complaint_id": complaint.complaint_id,
                "rejection_reason": complaint.rejection_reason,
            },
            recipient_user_id=complaint.complainant_user_id,
        )

    return complaint


def verify_closure(
    *,
    complaint_id: int,
    principal,
    is_satisfied: bool = True,
    comments: str = "",
    verifier_role: str = "complainant",
) -> Complaint:
    """Verify resolved complaint for closure (CFR-CMS-005, AFR-CMS-027..029, UC-CMS-007, UC-CMS-019)."""
    if not principal.has_perm("complaints.complaint.verify"):
        raise PermissionDenied("complaints.complaint.verify")

    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().get(pk=complaint_id)

        # Verification is only applicable for resolved complaints
        if complaint.status != ComplaintStatus.RESOLVED.value:
            raise RuleViolation(
                f"Cannot verify complaint in '{complaint.status}' status. Must be resolved.",
                code="complaint_not_resolved",
            )

        # If verifier is user/complainant, ensure ownership
        if verifier_role == "complainant" and complaint.complainant_user_id != principal.erp_user_id:
            raise RuleViolation(
                "User verification must be performed by the complainant.",
                code="unauthorized_complainant_verification",
            )

        verification, _ = ClosureVerification.objects.update_or_create(
            complaint=complaint,
            defaults={
                "verified_by_user_id": principal.erp_user_id,
                "verifier_role": verifier_role,
                "is_satisfied": is_satisfied,
                "comments": comments.strip(),
            },
        )

        if is_satisfied:
            validate_transition(complaint.status, ComplaintStatus.CLOSED.value, permissions={"*"})
            complaint.status = ComplaintStatus.CLOSED.value
            complaint.closed_at = timezone.now()
            complaint.closed_by_user_id = principal.erp_user_id
            complaint.save()

            StatusHistoryEntry.objects.create(
                complaint=complaint,
                from_status=ComplaintStatus.RESOLVED.value,
                to_status=ComplaintStatus.CLOSED.value,
                changed_by_user_id=principal.erp_user_id,
                reason=f"Closure verified by {verifier_role}: {comments.strip()}",
            )

            emit_notification_event(
                "complaints.complaint.status_changed",
                {"complaint_id": complaint.complaint_id, "status": complaint.status},
                recipient_user_id=complaint.complainant_user_id,
            )

    return complaint


def request_reopening(
    *,
    complaint_id: int,
    principal,
    reason: str,
) -> ReopeningRequest:
    """Request reopening of a closed complaint (CFR-CMS-006, AFR-CMS-030, UC-CMS-008, BR-CMS-018)."""
    if not reason or not reason.strip():
        raise RuleViolation("Reopening reason is required.", code="reopening_reason_required")

    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        if complaint.complainant_user_id != principal.erp_user_id:
            raise RuleViolation("Only the complainant can request reopening.", code="not_complainant")

        validate_reopening_eligibility(complaint.status)

        req = ReopeningRequest.objects.create(
            complaint=complaint,
            requested_by_user_id=principal.erp_user_id,
            reason=reason.strip(),
            status=ReopeningStatus.PENDING.value,
        )

        emit_notification_event(
            "complaints.complaint.reopening_requested",
            {"complaint_id": complaint.complaint_id, "reason": reason.strip()},
            recipient_user_id=complaint.assigned_handler_id,
        )

    return req


def review_reopening(
    *,
    reopening_request_id: int,
    principal,
    approved: bool,
    decision_notes: str = "",
) -> ReopeningRequest:
    """Review reopening request by Supervisor (CFR-CMS-006, AFR-CMS-031..034, UC-CMS-020, BR-CMS-019..021)."""
    if not principal.has_perm("complaints.complaint.reopen"):
        raise PermissionDenied("complaints.complaint.reopen")

    with transaction.atomic():
        req = ReopeningRequest.objects.select_for_update().get(pk=reopening_request_id)
        complaint = Complaint.objects.select_for_update().get(pk=req.complaint_id)

        req.reviewed_by_user_id = principal.erp_user_id
        req.decision_notes = decision_notes.strip()
        req.reviewed_at = timezone.now()

        if approved:
            req.status = ReopeningStatus.APPROVED.value
            validate_transition(complaint.status, ComplaintStatus.IN_PROGRESS.value, permissions={"*"})
            complaint.status = ComplaintStatus.IN_PROGRESS.value
            complaint.closed_at = None
            complaint.closed_by_user_id = None
            complaint.save()

            StatusHistoryEntry.objects.create(
                complaint=complaint,
                from_status=ComplaintStatus.CLOSED.value,
                to_status=ComplaintStatus.IN_PROGRESS.value,
                changed_by_user_id=principal.erp_user_id,
                reason=f"Reopening approved: {decision_notes.strip()}",
            )
        else:
            req.status = ReopeningStatus.DENIED.value

        req.save()

        emit_notification_event(
            "complaints.complaint.reopening_decided",
            {
                "complaint_id": complaint.complaint_id,
                "reopening_approved": approved,
                "decision_notes": decision_notes.strip(),
            },
            recipient_user_id=complaint.complainant_user_id,
        )

    return req


def submit_feedback(
    *,
    complaint_id: int,
    principal,
    rating: int,
    comments: str = "",
) -> ComplaintFeedback:
    """Submit feedback for resolved or closed complaint (CFR-CMS-007, AFR-CMS-035, UC-CMS-009, BR-CMS-022)."""
    if not principal.has_perm("complaints.feedback.submit"):
        raise PermissionDenied("complaints.feedback.submit")

    with transaction.atomic():
        complaint = Complaint.objects.get(pk=complaint_id)
        if complaint.complainant_user_id != principal.erp_user_id:
            raise RuleViolation("Only the complainant can submit feedback.", code="not_complainant")

        validate_feedback_eligibility(complaint.status, rating)

        fb, _ = ComplaintFeedback.objects.update_or_create(
            complaint=complaint,
            defaults={
                "complainant_user_id": principal.erp_user_id,
                "rating": rating,
                "comments": comments.strip(),
            },
        )

        emit_notification_event(
            "complaints.complaint.feedback_submitted",
            {"complaint_id": complaint.complaint_id, "rating": rating},
            recipient_user_id=complaint.assigned_handler_id,
        )

    return fb


def escalate_manually(
    *,
    complaint_id: int,
    principal,
    reason: str,
) -> Complaint:
    """Manually escalate an unresolved complaint (CFR-CMS-008, AFR-CMS-038, UC-CMS-011, BR-CMS-024)."""
    if not principal.has_perm("complaints.complaint.escalate"):
        raise PermissionDenied("complaints.complaint.escalate")

    if not reason or not reason.strip():
        raise RuleViolation("Escalation reason is required.", code="escalation_reason_required")

    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        validate_escalation_eligibility(complaint.status, complaint.is_escalated)

        complaint.is_escalated = True
        complaint.escalation_type = EscalationType.MANUAL.value
        complaint.escalation_reason = reason.strip()
        complaint.escalated_at = timezone.now()
        complaint.save()

        emit_notification_event(
            "complaints.complaint.escalated",
            {
                "complaint_id": complaint.complaint_id,
                "type": EscalationType.MANUAL.value,
                "reason": reason.strip(),
            },
            recipient_user_id=complaint.assigned_handler_id,
        )

    return complaint


def escalate_automatic_sla() -> int:
    """Autonomous SLA breach checker and auto-escalation (CFR-CMS-009, AFR-CMS-044, UC-CMS-022, BR-CMS-029)."""
    now = timezone.now()
    breached_complaints = Complaint.objects.filter(
        status__in=[ComplaintStatus.SUBMITTED.value, ComplaintStatus.IN_PROGRESS.value],
        is_escalated=False,
        sla_deadline__isnull=False,
        sla_deadline__lt=now,
    )

    count = 0
    for complaint in breached_complaints:
        with transaction.atomic():
            complaint.is_escalated = True
            complaint.escalation_type = EscalationType.AUTOMATIC.value
            complaint.escalated_at = now
            complaint.escalation_reason = f"Automated SLA breach after deadline {complaint.sla_deadline}"
            complaint.save(update_fields=["is_escalated", "escalation_type", "escalated_at", "escalation_reason"])

            emit_notification_event(
                "complaints.complaint.escalated",
                {
                    "complaint_id": complaint.complaint_id,
                    "type": EscalationType.AUTOMATIC.value,
                    "deadline": complaint.sla_deadline.isoformat(),
                },
                recipient_user_id=complaint.assigned_handler_id,
            )
            count += 1

    return count


def send_sla_reminders() -> int:
    """Autonomous pre-breach SLA reminder service (AFR-CMS-043, UC-CMS-021, BR-CMS-028)."""
    now = timezone.now()
    # Check complaints nearing deadline within 12 hours
    reminder_threshold = now + timedelta(hours=12)

    nearing_complaints = Complaint.objects.filter(
        status__in=[ComplaintStatus.SUBMITTED.value, ComplaintStatus.IN_PROGRESS.value],
        is_escalated=False,
        sla_reminder_sent=False,
        sla_deadline__isnull=False,
        sla_deadline__lte=reminder_threshold,
        sla_deadline__gt=now,
    )

    count = 0
    for complaint in nearing_complaints:
        with transaction.atomic():
            complaint.sla_reminder_sent = True
            complaint.save(update_fields=["sla_reminder_sent"])

            emit_notification_event(
                "complaints.sla.reminder",
                {
                    "complaint_id": complaint.complaint_id,
                    "deadline": complaint.sla_deadline.isoformat(),
                },
                recipient_user_id=complaint.assigned_handler_id,
            )
            count += 1

    return count


def publish_announcement(
    *,
    principal,
    title: str,
    content: str,
    target_audience: str = "all",
    expires_at: timezone.datetime | None = None,
) -> ComplaintAnnouncement:
    """Publish complaint-related announcement (CFR-CMS-010, AFR-CMS-045, 046, UC-CMS-013, BR-CMS-030)."""
    if not principal.has_perm("complaints.announcement.publish"):
        raise PermissionDenied("complaints.announcement.publish")

    if not title or not title.strip():
        raise RuleViolation("Announcement title cannot be empty.", code="empty_title")

    ann = ComplaintAnnouncement.objects.create(
        title=title.strip(),
        content=content.strip(),
        author_user_id=principal.erp_user_id,
        target_audience=target_audience,
        expires_at=expires_at,
    )

    emit_notification_event(
        "complaints.announcement.published",
        {"title": ann.title, "target_audience": ann.target_audience},
    )

    return ann


def assign_cms_role(
    *,
    principal,
    user_id: int,
    role_name: str,
    valid_from: timezone.datetime,
    valid_to: timezone.datetime | None = None,
) -> CMSRoleAssignment:
    """Assign/reassign CMS operational or supervisory roles (CFR-CMS-013, AFR-CMS-064..068, UC-CMS-018).

    Enforces exactly one active holder of each role (BR-CMS-037).
    """
    if not principal.has_perm("complaints.role.manage"):
        raise PermissionDenied("complaints.role.manage")

    validate_role_assignment(role_name, valid_from, valid_to)

    with transaction.atomic():
        # Deactivate any existing active assignment for this role (mid-cycle reassignment BR-CMS-036)
        CMSRoleAssignment.objects.filter(role_name=role_name, is_active=True).update(
            is_active=False,
            valid_to=timezone.now(),
        )

        assignment = CMSRoleAssignment.objects.create(
            user_id=user_id,
            role_name=role_name,
            assigned_by_user_id=principal.erp_user_id,
            valid_from=valid_from,
            valid_to=valid_to,
            is_active=True,
        )

    return assignment

