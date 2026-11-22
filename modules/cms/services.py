"""Transactional CMS writes and SLA processing."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.cms import domain
from modules.cms.models import (
    CmsAuditEvent,
    CmsNotificationEvent,
    CmsRoleAssignment,
    Complaint,
    ComplaintAnnouncement,
    ComplaintFeedback,
    ComplaintHistory,
    ComplaintProgress,
    ReopeningRequest,
)

log = logging.getLogger("fusion.cms")


def _event(event_type, complaint=None, *, recipient=None, payload=None):
    return CmsNotificationEvent.objects.create(
        event_type=event_type,
        complaint=complaint,
        recipient_user_id=recipient,
        payload=payload or {},
    )


def _audit(action, actor, obj, **details):
    return CmsAuditEvent.objects.create(
        actor_user_id=getattr(actor, "user_id", None),
        actor_role=getattr(actor, "active_role", "") or "",
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(getattr(obj, "pk", "")),
        details=details,
    )


def get_complaint(complaint_id: int) -> Complaint:
    complaint = Complaint.objects.filter(pk=complaint_id).first()
    if complaint is None:
        raise NotFoundError("No such complaint.")
    return complaint


def submit(*, actor, category, description):
    category = category.strip()
    description = description.strip()
    if not category or not description:
        raise ConflictError("Category and description are required.", code="mandatory_fields")
    with transaction.atomic():
        complaint = Complaint.objects.create(
            complaint_id=f"CMS-{uuid.uuid4().hex[:12].upper()}",
            complainant_user_id=actor.user_id,
            category=category,
            description=description,
            status="submitted",
        )
        ComplaintHistory.objects.create(
            complaint=complaint,
            from_status="",
            to_status="submitted",
            actor_user_id=actor.user_id,
            actor_role="complainant",
            note="Complaint submitted.",
        )
        _event("complaint.submitted", complaint, recipient=actor.user_id)
        _audit("complaint.submitted", actor, complaint, category=category)
    return complaint


def setup_handling(*, complaint_id, actor, category, priority, note=""):
    if priority not in domain.PRIORITIES:
        raise ConflictError("Priority must be Low, Medium, or High.", code="invalid_priority")
    category = category.strip()
    if not category:
        raise ConflictError("Category is required.", code="mandatory_fields")
    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().filter(pk=complaint_id).first()
        if complaint is None:
            raise NotFoundError("No such complaint.")
        if complaint.status != "submitted" or complaint.assigned_handler_user_id:
            raise ConflictError(
                "Handling setup is already complete or not available.",
                code="handling_setup_unavailable",
            )
        complaint.assigned_handler_user_id = actor.user_id
        complaint.category = category
        complaint.priority = priority
        complaint.assignment_note = note.strip()
        sla_hours = getattr(settings, "CMS_SLA_HOURS", {}).get(priority)
        complaint.sla_due_at = timezone.now() + timedelta(hours=sla_hours) if sla_hours else None
        complaint.save(
            update_fields=[
                "assigned_handler_user_id",
                "category",
                "priority",
                "assignment_note",
                "sla_due_at",
                "updated_at",
            ]
        )
        _audit(
            "complaint.assigned", actor, complaint, handler_user_id=actor.user_id, priority=priority
        )
    return complaint


def add_progress(*, complaint_id, actor, text):
    text = text.strip()
    if not text:
        raise ConflictError("A progress update is required.", code="empty_progress")
    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().filter(pk=complaint_id).first()
        if complaint is None:
            raise NotFoundError("No such complaint.")
        if complaint.assigned_handler_user_id != actor.user_id or not domain.is_unresolved(
            complaint.status
        ):
            raise ConflictError(
                "Progress can only be added to your unresolved assignment.",
                code="progress_unavailable",
            )
        progress = ComplaintProgress.objects.create(
            complaint=complaint, actor_user_id=actor.user_id, update_text=text
        )
        _audit("complaint.progress_added", actor, complaint, progress_id=progress.pk)
    return progress


def decide_outcome(*, complaint_id, actor, outcome, details):
    details = details.strip()
    if outcome not in {"resolved", "rejected"}:
        raise ConflictError("Outcome must be resolved or rejected.", code="invalid_outcome")
    if not details:
        raise ConflictError("Outcome details are required.", code="outcome_details_required")
    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().filter(pk=complaint_id).first()
        if complaint is None:
            raise NotFoundError("No such complaint.")
        if not complaint.assigned_handler_user_id:
            raise ConflictError(
                "The complaint must be assigned before an outcome.", code="assignment_required"
            )
        if complaint.assigned_handler_user_id != actor.user_id:
            raise PermissionDeniedError("Only the assigned handler may record an outcome.")
        try:
            domain.transition(complaint.status, outcome)
        except domain.InvalidTransition as exc:
            raise ConflictError(str(exc), code="invalid_transition") from exc
        old = complaint.status
        complaint.status = outcome
        if outcome == "resolved":
            complaint.resolution_details = details
            complaint.closure_verifier = getattr(settings, "CMS_CLOSURE_VERIFIER", "complainant")
        else:
            complaint.rejection_reason = details
        complaint.save(
            update_fields=[
                "status",
                "resolution_details",
                "rejection_reason",
                "closure_verifier",
                "updated_at",
            ]
        )
        ComplaintHistory.objects.create(
            complaint=complaint,
            from_status=old,
            to_status=outcome,
            actor_user_id=actor.user_id,
            actor_role="handler",
            note=details,
        )
        _event(f"complaint.{outcome}", complaint, recipient=complaint.complainant_user_id)
        _audit(f"complaint.{outcome}", actor, complaint)
    return complaint


def verify_closure(*, complaint_id, actor, verifier):
    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().filter(pk=complaint_id).first()
        if complaint is None:
            raise NotFoundError("No such complaint.")
        if complaint.status != "resolved" or complaint.closure_verifier != verifier:
            raise ConflictError(
                "This complaint is not awaiting your closure verification.",
                code="verification_unavailable",
            )
        if verifier == "complainant" and complaint.complainant_user_id != actor.user_id:
            raise NotFoundError("No such complaint.")
        try:
            domain.transition(complaint.status, "closed")
        except domain.InvalidTransition as exc:
            raise ConflictError(str(exc), code="invalid_transition") from exc
        complaint.status = "closed"
        complaint.closed_at = timezone.now()
        complaint.save(update_fields=["status", "closed_at", "updated_at"])
        ComplaintHistory.objects.create(
            complaint=complaint,
            from_status="resolved",
            to_status="closed",
            actor_user_id=actor.user_id,
            actor_role=verifier,
            note="Closure verification recorded.",
        )
        _event("complaint.closed", complaint, recipient=complaint.complainant_user_id)
        _audit("complaint.closed", actor, complaint, verifier=verifier)
    return complaint


def request_reopening(*, complaint_id, actor, reason):
    reason = reason.strip()
    if not reason:
        raise ConflictError(
            "A reason is required to request reopening.", code="reopening_reason_required"
        )
    with transaction.atomic():
        complaint = (
            Complaint.objects.select_for_update()
            .filter(pk=complaint_id, complainant_user_id=actor.user_id)
            .first()
        )
        if complaint is None:
            raise NotFoundError("No such complaint.")
        if complaint.status != "closed":
            raise ConflictError(
                "Only a closed complaint can be reopened.", code="reopening_unavailable"
            )
        if complaint.reopening_requests.filter(decision="pending").exists():
            raise ConflictError("A reopening request is already pending.", code="reopening_pending")
        req = ReopeningRequest.objects.create(
            complaint=complaint, requested_by_user_id=actor.user_id, request_reason=reason
        )
        _audit("complaint.reopening_requested", actor, complaint, request_id=req.pk)
    return req


def review_reopening(*, request_id, actor, decision, note=""):
    if decision not in {"approved", "denied"}:
        raise ConflictError("Decision must be approved or denied.", code="invalid_decision")
    with transaction.atomic():
        req = (
            ReopeningRequest.objects.select_for_update()
            .select_related("complaint")
            .filter(pk=request_id)
            .first()
        )
        if req is None:
            raise NotFoundError("No such reopening request.")
        complaint = Complaint.objects.select_for_update().get(pk=req.complaint_id)
        if req.decision != "pending" or complaint.status != "closed":
            raise ConflictError(
                "This reopening request is no longer pending.", code="reopening_not_pending"
            )
        req.decision = decision
        req.decided_by_user_id = actor.user_id
        req.decision_note = note.strip()
        req.decided_at = timezone.now()
        req.save(
            update_fields=[
                "decision",
                "decided_by_user_id",
                "decision_note",
                "decided_at",
                "updated_at",
            ]
        )
        if decision == "approved":
            target = getattr(settings, "CMS_REOPENED_STATUS", "in_progress")
            try:
                domain.transition("closed", target)
            except domain.InvalidTransition as exc:
                raise ConflictError(
                    "CMS_REOPENED_STATUS must be submitted or in_progress.",
                    code="invalid_reopened_status",
                ) from exc
            complaint.status = target
            complaint.reopened_at = timezone.now()
            complaint.closed_at = None
            complaint.save(update_fields=["status", "reopened_at", "closed_at", "updated_at"])
            ComplaintHistory.objects.create(
                complaint=complaint,
                from_status="closed",
                to_status=target,
                actor_user_id=actor.user_id,
                actor_role="supervisor",
                note=f"Reopening approved. {note.strip()}".strip(),
            )
        _event(
            "complaint.reopening_outcome",
            complaint,
            recipient=req.requested_by_user_id,
            payload={"decision": decision},
        )
        _audit(
            "complaint.reopening_reviewed", actor, complaint, request_id=req.pk, decision=decision
        )
    return req


def escalate(*, complaint_id, actor=None, kind="manual"):
    if kind not in {"manual", "automatic"}:
        raise ConflictError("Escalation type is invalid.", code="invalid_escalation")
    with transaction.atomic():
        complaint = Complaint.objects.select_for_update().filter(pk=complaint_id).first()
        if complaint is None:
            raise NotFoundError("No such complaint.")
        if not domain.is_unresolved(complaint.status) or not complaint.assigned_handler_user_id:
            raise ConflictError(
                "Only assigned unresolved complaints can be escalated.",
                code="escalation_unavailable",
            )
        if complaint.escalated_at:
            return complaint
        if kind == "manual" and complaint.assigned_handler_user_id != actor.user_id:
            raise PermissionDeniedError("Only the assigned handler may escalate manually.")
        complaint.escalated_at = timezone.now()
        complaint.escalation_kind = kind
        complaint.save(update_fields=["escalated_at", "escalation_kind", "updated_at"])
        _event(
            "complaint.escalated",
            complaint,
            recipient=complaint.complainant_user_id,
            payload={"kind": kind},
        )
        _audit(f"complaint.escalated_{kind}", actor, complaint)
    return complaint


def submit_feedback(*, complaint_id, actor, text):
    text = text.strip()
    if not text:
        raise ConflictError("Feedback is required.", code="empty_feedback")
    with transaction.atomic():
        complaint = (
            Complaint.objects.select_for_update()
            .filter(pk=complaint_id, complainant_user_id=actor.user_id)
            .first()
        )
        if complaint is None:
            raise NotFoundError("No such complaint.")
        if complaint.status not in {"resolved", "closed"}:
            raise ConflictError(
                "Feedback is available after resolution or closure.", code="feedback_unavailable"
            )
        feedback = ComplaintFeedback.objects.create(
            complaint=complaint, submitted_by_user_id=actor.user_id, feedback_text=text
        )
        _event(
            "complaint.feedback_submitted",
            complaint,
            recipient=complaint.complainant_user_id,
            payload={"feedback_id": feedback.pk},
        )
        _audit("complaint.feedback_submitted", actor, complaint, feedback_id=feedback.pk)
    return feedback


def publish_announcement(*, actor, title, body, notify_users=False):
    title, body = title.strip(), body.strip()
    if not title or not body:
        raise ConflictError(
            "Title and announcement text are required.", code="announcement_fields_required"
        )
    with transaction.atomic():
        item = ComplaintAnnouncement.objects.create(
            title=title, body=body, published_by_user_id=actor.user_id, notify_users=notify_users
        )
        if notify_users:
            _event(
                "announcement.published",
                recipient=None,
                payload={"announcement_id": item.pk, "broadcast": True},
            )
        _audit("announcement.published", actor, item, notify_users=notify_users)
    return item


@transaction.atomic
def assign_role(*, actor, role, user_id, starts_at, ends_at):
    if role not in {"handler", "supervisor"}:
        raise ConflictError("CMS role must be handler or supervisor.", code="invalid_role")
    if user_id <= 0 or starts_at >= ends_at:
        raise ConflictError(
            "Choose an institutional user and a valid role period.", code="invalid_role_period"
        )
    # IAM owns user records. The CMS checks identity through its plural contract.
    from modules.directory import contracts as directory

    known = directory.get_users([user_id])
    if user_id not in known:
        raise ConflictError(
            "The selected user is not present in the IAM directory.",
            code="unknown_institutional_user",
        )
    now = timezone.now()
    CmsRoleAssignment.objects.select_for_update().filter(role=role, is_active=True).update(
        is_active=False, updated_at=now
    )
    assignment = CmsRoleAssignment.objects.create(
        role=role,
        user_id=user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        assigned_by_user_id=actor.user_id,
    )
    _audit(
        "role.assigned",
        actor,
        assignment,
        role=role,
        user_id=user_id,
        starts_at=starts_at.isoformat(),
        ends_at=ends_at.isoformat(),
    )
    return assignment


def process_sla(now=None):
    """Issue reminder and escalation trigger records for configured priority SLAs."""
    now = now or timezone.now()
    reminder_hours = getattr(settings, "CMS_SLA_REMINDER_HOURS", None)
    eligible = Complaint.objects.filter(
        status__in=["submitted", "in_progress"],
        assigned_handler_user_id__isnull=False,
        sla_due_at__isnull=False,
    )
    reminded = 0
    if reminder_hours is not None:
        for complaint in eligible.filter(
            sla_reminded_at__isnull=True,
            sla_due_at__lte=now + timedelta(hours=reminder_hours),
            sla_due_at__gt=now,
        ):
            with transaction.atomic():
                locked = Complaint.objects.select_for_update().get(pk=complaint.pk)
                if locked.sla_reminded_at or not domain.is_unresolved(locked.status):
                    continue
                locked.sla_reminded_at = now
                locked.save(update_fields=["sla_reminded_at", "updated_at"])
                _event("complaint.sla_reminder", locked, recipient=locked.complainant_user_id)
                _audit("complaint.sla_reminder", None, locked)
                reminded += 1
    escalated = 0
    for complaint in eligible.filter(sla_due_at__lte=now, escalated_at__isnull=True):
        try:
            escalate(complaint_id=complaint.pk, kind="automatic")
        except ConflictError:
            continue
        escalated += 1
    return {"reminded": reminded, "escalated": escalated}
