"""Complaint submission and supported lifecycle actions."""

from __future__ import annotations

import hashlib
import pathlib
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.files import storage
from modules.complaints.domain import state_machine as sm
from modules.complaints.domain.submission import InvalidSubmission, validate_submission
from modules.complaints.models import Complaint, ComplaintHistory, NotificationOutbox


@transaction.atomic
def submit(*, user_id: int, category: str, description: str, attachments=()) -> Complaint:
    category, description = validate_submission(category=category, description=description)
    attachments = list(attachments or ())
    if len(attachments) > settings.CMS_ATTACHMENT_MAX_COUNT:
        raise InvalidSubmission("The complaint exceeds the attachment count limit.")
    validated_files = [_validate_attachment_file(upload) for upload in attachments]
    complaint = Complaint.objects.create(
        complainant_user_id=user_id,
        category=category,
        description=description,
        verification_required=settings.CMS_REQUIRE_CLOSURE_VERIFICATION,
    )
    saved_paths = []
    try:
        for upload, validated in zip(attachments, validated_files, strict=True):
            _, path = _persist_attachment(complaint, user_id, upload, validated)
            saved_paths.append(path)
    except Exception:
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise
    ComplaintHistory.objects.create(
        complaint=complaint,
        event="submitted",
        to_status=sm.SUBMITTED,
        actor_user_id=user_id,
        actor_kind=sm.COMPLAINANT,
    )
    NotificationOutbox.objects.create(
        topic="complaint.submitted",
        dedupe_key=f"complaint.submitted:{complaint.reference}",
        recipient_user_id=user_id,
        subject="Complaint submitted",
        body=f"Your complaint {complaint.reference} was submitted.",
    )
    return complaint


@transaction.atomic
def assign(
    *, reference, actor_user_id: int, assignee_user_id: int, priority: str, category: str
) -> Complaint:
    from fusion_auth.client import IamUnavailable
    from modules.directory import contracts as directory

    if priority not in dict(Complaint.PRIORITY):
        raise InvalidSubmission("Priority must be low, medium, or high.")
    category = (category or "").strip()
    if not category:
        raise InvalidSubmission("Complaint category is required.")
    try:
        person = directory.get_users([assignee_user_id]).get(assignee_user_id)
    except IamUnavailable as exc:
        raise InvalidSubmission("The directory is temporarily unavailable.") from exc
    if person is None or not person.is_active or person.kind not in ("faculty", "staff"):
        raise InvalidSubmission("The assigned handler must be an active employee.")
    complaint = Complaint.objects.select_for_update().get(reference=reference)
    if complaint.status not in (sm.SUBMITTED, sm.IN_PROGRESS):
        raise InvalidSubmission("Only active complaints can be assigned.")
    before = complaint.status
    assigned_at = timezone.now()
    complaint.assigned_to_user_id = assignee_user_id
    complaint.assigned_at = assigned_at
    complaint.priority = priority
    complaint.category = category
    complaint.sla_due_at = assigned_at + timedelta(hours=settings.CMS_SLA_HOURS[priority])
    if complaint.status == sm.SUBMITTED:
        try:
            complaint.status = sm.resolve(complaint.status, "start", sm.HANDLER).target
        except sm.InvalidTransition as exc:
            raise InvalidSubmission(str(exc)) from exc
    complaint.save(
        update_fields=(
            "assigned_to_user_id",
            "assigned_at",
            "priority",
            "category",
            "sla_due_at",
            "status",
            "updated_at",
        )
    )
    ComplaintHistory.objects.create(
        complaint=complaint,
        event="assigned",
        from_status=before,
        to_status=complaint.status,
        actor_user_id=actor_user_id,
        actor_kind=sm.HANDLER,
        details=f"Assigned to user {assignee_user_id}; priority {priority}.",
    )
    if before != complaint.status:
        NotificationOutbox.objects.create(
            topic="complaint.status_updated",
            dedupe_key=f"complaint.status_updated:{complaint.reference}:{complaint.status}",
            recipient_user_id=complaint.complainant_user_id,
            subject="Complaint status updated",
            body=f"Complaint {complaint.reference} is now {complaint.status.replace('_', ' ')}.",
        )
    return complaint


@transaction.atomic
def add_progress(*, reference, actor_user_id: int, details: str) -> Complaint:
    text = (details or "").strip()
    if not text:
        raise InvalidSubmission("Progress details are required.")
    complaint = Complaint.objects.select_for_update().get(reference=reference)
    if complaint.assigned_to_user_id != actor_user_id:
        raise InvalidSubmission("Only the assigned handler can update this complaint.")
    if complaint.status not in (sm.SUBMITTED, sm.IN_PROGRESS):
        raise InvalidSubmission("Progress can only be added to an active complaint.")
    before = complaint.status
    if complaint.status == sm.SUBMITTED:
        try:
            transition = sm.resolve(complaint.status, "start", sm.HANDLER)
        except sm.InvalidTransition as exc:
            raise InvalidSubmission(str(exc)) from exc
        complaint.status = transition.target
        complaint.save(update_fields=("status", "updated_at"))
    ComplaintHistory.objects.create(
        complaint=complaint,
        event="progress_updated",
        from_status=before,
        to_status=complaint.status,
        actor_user_id=actor_user_id,
        actor_kind=sm.HANDLER,
        details=text,
    )
    return complaint


@transaction.atomic
def resolve(*, reference, actor_user_id: int, details: str) -> Complaint:
    text = (details or "").strip()
    if not text:
        raise InvalidSubmission("Resolution details are required.")
    complaint = Complaint.objects.select_for_update().get(reference=reference)
    if complaint.assigned_to_user_id != actor_user_id:
        raise InvalidSubmission("Only the assigned handler can resolve this complaint.")
    try:
        transition = sm.resolve(
            complaint.status, "resolve", sm.HANDLER, guards=frozenset({"resolution_details"})
        )
    except (sm.InvalidTransition, sm.ActorNotAllowed, sm.GuardFailed) as exc:
        raise InvalidSubmission(str(exc)) from exc
    before = complaint.status
    complaint.status = transition.target
    complaint.resolution_details = text
    complaint.resolved_at = timezone.now()
    resolved_status = complaint.status
    if not complaint.verification_required:
        complaint.status = sm.CLOSED
        complaint.closed_at = timezone.now()
    complaint.save(
        update_fields=("status", "resolution_details", "resolved_at", "closed_at", "updated_at")
    )
    ComplaintHistory.objects.create(
        complaint=complaint,
        event="resolved",
        from_status=before,
        to_status=resolved_status,
        actor_user_id=actor_user_id,
        actor_kind=sm.HANDLER,
        details=text,
    )
    if complaint.status == sm.CLOSED:
        ComplaintHistory.objects.create(
            complaint=complaint,
            event="closed_without_verification",
            from_status=resolved_status,
            to_status=sm.CLOSED,
            actor_user_id=actor_user_id,
            actor_kind=sm.HANDLER,
            details="Closed automatically because verification is disabled by CMS policy.",
        )
        NotificationOutbox.objects.create(
            topic="complaint.closed",
            dedupe_key=f"complaint.closed:{complaint.reference}",
            recipient_user_id=complaint.complainant_user_id,
            subject="Complaint closed",
            body=f"Complaint {complaint.reference} was closed after resolution.",
        )
    NotificationOutbox.objects.create(
        topic="complaint.resolved",
        dedupe_key=f"complaint.resolved:{complaint.reference}",
        recipient_user_id=complaint.complainant_user_id,
        subject="Complaint resolved",
        body=f"Complaint {complaint.reference} has been marked resolved.",
    )
    return complaint


@transaction.atomic
def reject(*, reference, actor_user_id: int, reason: str) -> Complaint:
    text = (reason or "").strip()
    if not text:
        raise InvalidSubmission("A rejection reason is required.")
    complaint = Complaint.objects.select_for_update().get(reference=reference)
    if complaint.assigned_to_user_id != actor_user_id:
        raise InvalidSubmission("Only the assigned handler can reject this complaint.")
    try:
        transition = sm.resolve(
            complaint.status, "reject", sm.HANDLER, guards=frozenset({"rejection_reason"})
        )
    except (sm.InvalidTransition, sm.ActorNotAllowed, sm.GuardFailed) as exc:
        raise InvalidSubmission(str(exc)) from exc
    before = complaint.status
    complaint.status = transition.target
    complaint.rejection_reason = text
    complaint.save(update_fields=("status", "rejection_reason", "updated_at"))
    ComplaintHistory.objects.create(
        complaint=complaint,
        event="rejected",
        from_status=before,
        to_status=complaint.status,
        actor_user_id=actor_user_id,
        actor_kind=sm.HANDLER,
        details=text,
    )
    NotificationOutbox.objects.create(
        topic="complaint.rejected",
        dedupe_key=f"complaint.rejected:{complaint.reference}",
        recipient_user_id=complaint.complainant_user_id,
        subject="Complaint update",
        body=f"Complaint {complaint.reference} was rejected. Reason: {text}",
    )
    return complaint


@transaction.atomic
def submit_feedback(*, reference, user_id: int, message: str):
    from modules.complaints.models import Feedback

    text = (message or "").strip()
    if not text:
        raise InvalidSubmission("Feedback is required.")
    complaint = Complaint.objects.select_for_update().get(
        reference=reference, complainant_user_id=user_id
    )
    if complaint.status not in (sm.RESOLVED, sm.CLOSED):
        raise InvalidSubmission("Feedback is available after complaint resolution.")
    try:
        row = Feedback.objects.create(
            complaint=complaint, submitted_by_user_id=user_id, message=text
        )
    except IntegrityError as exc:
        raise InvalidSubmission("Feedback has already been submitted.") from exc
    else:
        ComplaintHistory.objects.create(
            complaint=complaint,
            event="feedback_submitted",
            actor_user_id=user_id,
            actor_kind=sm.COMPLAINANT,
        )
        NotificationOutbox.objects.create(
            topic="complaint.feedback_submitted",
            dedupe_key=f"complaint.feedback_submitted:{row.pk}",
            recipient_user_id=user_id,
            subject="Feedback received",
            body=f"Your feedback for complaint {complaint.reference} was received.",
        )
        return row


@transaction.atomic
def request_reopening(*, reference, user_id: int, reason: str):
    from modules.complaints.models import ReopeningRequest

    text = (reason or "").strip()
    if not text:
        raise InvalidSubmission("A reopening reason is required.")
    complaint = Complaint.objects.select_for_update().get(
        reference=reference, complainant_user_id=user_id
    )
    if complaint.status != sm.CLOSED:
        raise InvalidSubmission("Only a closed complaint can be reopened.")
    if complaint.reopening_requests.filter(status="pending").exists():
        raise InvalidSubmission("A reopening request is already pending.")
    row = ReopeningRequest.objects.create(
        complaint=complaint, requested_by_user_id=user_id, reason=text
    )
    ComplaintHistory.objects.create(
        complaint=complaint,
        event="reopening_requested",
        actor_user_id=user_id,
        actor_kind=sm.COMPLAINANT,
        details=text,
    )
    return row


@transaction.atomic
def publish_announcement(*, actor_user_id: int, title: str, body: str):
    from modules.complaints.models import Announcement

    title, body = (title or "").strip(), (body or "").strip()
    if not title or not body:
        raise InvalidSubmission("Announcement title and body are required.")
    announcement = Announcement.objects.create(
        title=title,
        body=body,
        published_by_user_id=actor_user_id,
        published_at=timezone.now(),
        is_published=True,
    )
    if settings.CMS_NOTIFY_ANNOUNCEMENTS:
        from modules.directory import contracts as directory

        batch = []
        for recipient_id in directory.iter_active_user_ids():
            batch.append(
                NotificationOutbox(
                    topic="complaint.announcement",
                    dedupe_key=f"complaint.announcement:{announcement.pk}:{recipient_id}",
                    recipient_user_id=recipient_id,
                    subject=announcement.title,
                    body=announcement.body,
                )
            )
            if len(batch) >= 500:
                NotificationOutbox.objects.bulk_create(batch, batch_size=500)
                batch.clear()
        if batch:
            NotificationOutbox.objects.bulk_create(batch, batch_size=500)
    return announcement


@transaction.atomic
def verify_closure(*, reference, actor_user_id: int, actor_kind: str) -> Complaint:
    complaint = Complaint.objects.select_for_update().get(reference=reference)
    if actor_kind == sm.COMPLAINANT and complaint.complainant_user_id != actor_user_id:
        from core.api.exceptions import NotFoundError

        raise NotFoundError("No such complaint.")
    event = "verify_user" if actor_kind == sm.COMPLAINANT else "verify_supervisor"
    if not complaint.verification_required:
        raise InvalidSubmission("Closure verification is disabled for this complaint.")
    guard = (
        "user_verification_required"
        if actor_kind == sm.COMPLAINANT
        else "supervisor_verification_required"
    )
    try:
        transition = sm.resolve(
            complaint.status,
            event,
            actor_kind,
            guards=frozenset({guard}),
        )
    except (sm.InvalidTransition, sm.ActorNotAllowed, sm.GuardFailed) as exc:
        raise InvalidSubmission(str(exc)) from exc
    before = complaint.status
    complaint.status = transition.target
    complaint.closed_at = timezone.now()
    complaint.save(update_fields=("status", "closed_at", "updated_at"))
    ComplaintHistory.objects.create(
        complaint=complaint,
        event="closed",
        from_status=before,
        to_status=complaint.status,
        actor_user_id=actor_user_id,
        actor_kind=actor_kind,
    )
    NotificationOutbox.objects.create(
        topic="complaint.closed",
        dedupe_key=f"complaint.closed:{complaint.reference}",
        recipient_user_id=complaint.complainant_user_id,
        subject="Complaint closed",
        body=f"Complaint {complaint.reference} was closed after verification.",
    )
    return complaint


@transaction.atomic
def review_reopening(*, request_id: int, actor_user_id: int, decision: str, reason: str = ""):
    from modules.complaints.models import ReopeningRequest

    if decision not in ("approved", "denied"):
        raise InvalidSubmission("Decision must be approved or denied.")
    row = (
        ReopeningRequest.objects.select_for_update()
        .select_related("complaint")
        .filter(pk=request_id, status="pending")
        .first()
    )
    if row is None:
        from core.api.exceptions import NotFoundError

        raise NotFoundError("No pending reopening request.")
    row.status = decision
    row.reviewed_by_user_id = actor_user_id
    row.decision_reason = (reason or "").strip()
    row.decided_at = timezone.now()
    row.save(
        update_fields=(
            "status",
            "reviewed_by_user_id",
            "decision_reason",
            "decided_at",
            "updated_at",
        )
    )
    ComplaintHistory.objects.create(
        complaint=row.complaint,
        event=f"reopening_{decision}",
        actor_user_id=actor_user_id,
        actor_kind=sm.SUPERVISOR,
        details=row.decision_reason,
    )
    if decision == "approved":
        complaint = Complaint.objects.select_for_update().get(pk=row.complaint_id)
        complaint.status = sm.IN_PROGRESS
        complaint.resolved_at = None
        complaint.closed_at = None
        complaint.resolution_details = ""
        complaint.sla_due_at = timezone.now() + timedelta(
            hours=settings.CMS_SLA_HOURS[complaint.priority]
        )
        complaint.sla_reminded_at = None
        complaint.save(
            update_fields=(
                "status",
                "resolved_at",
                "closed_at",
                "resolution_details",
                "sla_due_at",
                "sla_reminded_at",
                "updated_at",
            )
        )
        ComplaintHistory.objects.create(
            complaint=complaint,
            event="reopened",
            from_status=sm.CLOSED,
            to_status=sm.IN_PROGRESS,
            actor_user_id=actor_user_id,
            actor_kind=sm.SUPERVISOR,
            details="Reopening request approved; complaint returned to active handling.",
        )
        NotificationOutbox.objects.create(
            topic="complaint.reopening_approved",
            dedupe_key=f"complaint.reopening:{row.pk}:approved",
            recipient_user_id=row.requested_by_user_id,
            subject="Reopening request approved",
            body=f"Complaint {complaint.reference} has been reopened.",
        )
    if decision == "denied":
        NotificationOutbox.objects.create(
            topic="complaint.reopening_denied",
            dedupe_key=f"complaint.reopening:{row.pk}:denied",
            recipient_user_id=row.requested_by_user_id,
            subject="Reopening request update",
            body=(
                f"Your reopening request for complaint {row.complaint.reference} "
                f"was denied. {row.decision_reason}"
            ).strip(),
        )
    return row


def process_sla(*, now=None, limit: int = 500) -> dict[str, int]:
    """Send one approaching-deadline reminder and one automatic escalation per complaint."""
    from modules.complaints.models import Escalation

    now = now or timezone.now()
    reminder_at = now + timedelta(hours=settings.CMS_SLA_REMINDER_HOURS)
    candidates = list(
        Complaint.objects.filter(status__in=(sm.SUBMITTED, sm.IN_PROGRESS))
        .filter(sla_due_at__isnull=False)
        .order_by("sla_due_at")
        .values_list("pk", flat=True)[:limit]
    )
    reminded = escalated = 0
    for complaint_id in candidates:
        with transaction.atomic():
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
            if complaint.status not in (sm.SUBMITTED, sm.IN_PROGRESS) or not complaint.sla_due_at:
                continue
            if complaint.sla_due_at <= now:
                _, created = Escalation.objects.get_or_create(
                    complaint=complaint,
                    source="sla",
                    defaults={"reason": "Generic priority SLA duration exceeded."},
                )
                if created:
                    ComplaintHistory.objects.create(
                        complaint=complaint,
                        event="sla_escalation",
                        from_status=complaint.status,
                        to_status=complaint.status,
                        actor_kind=sm.SYSTEM,
                        details="Generic priority SLA duration exceeded.",
                    )
                    NotificationOutbox.objects.create(
                        topic="complaint.sla_escalated",
                        dedupe_key=f"complaint.sla_escalated:{complaint.reference}",
                        recipient_user_id=complaint.complainant_user_id,
                        subject="Complaint escalated",
                        body=(
                            f"Complaint {complaint.reference} exceeded its response target "
                            "and was escalated."
                        ),
                    )
                    escalated += 1
            elif complaint.sla_due_at <= reminder_at and complaint.sla_reminded_at is None:
                recipient_id = complaint.assigned_to_user_id or complaint.complainant_user_id
                NotificationOutbox.objects.create(
                    topic="complaint.sla_reminder",
                    dedupe_key=f"complaint.sla_reminder:{complaint.reference}",
                    recipient_user_id=recipient_id,
                    subject="Complaint response deadline approaching",
                    body=f"Complaint {complaint.reference} is approaching its response deadline.",
                )
                complaint.sla_reminded_at = now
                complaint.save(update_fields=("sla_reminded_at", "updated_at"))
                reminded += 1
    return {"reminded": reminded, "escalated": escalated}


@transaction.atomic
def escalate_manual(*, reference, actor_user_id: int, reason: str):
    from modules.complaints.models import Escalation

    text = (reason or "").strip()
    if not text:
        raise InvalidSubmission("An escalation reason is required.")
    complaint = Complaint.objects.select_for_update().get(reference=reference)
    if complaint.assigned_to_user_id != actor_user_id:
        raise InvalidSubmission("Only the assigned handler can escalate this complaint.")
    if complaint.status not in (sm.SUBMITTED, sm.IN_PROGRESS):
        raise InvalidSubmission("Only active complaints can be escalated.")
    row, created = Escalation.objects.get_or_create(
        complaint=complaint,
        source="manual",
        defaults={"escalated_by_user_id": actor_user_id, "reason": text},
    )
    if not created:
        raise InvalidSubmission("This complaint has already been manually escalated.")
    ComplaintHistory.objects.create(
        complaint=complaint,
        event="manual_escalation",
        actor_user_id=actor_user_id,
        actor_kind=sm.HANDLER,
        details=text,
    )
    NotificationOutbox.objects.create(
        topic="complaint.manually_escalated",
        dedupe_key=f"complaint.manually_escalated:{complaint.reference}",
        recipient_user_id=complaint.complainant_user_id,
        subject="Complaint escalated",
        body=f"Complaint {complaint.reference} was escalated for review.",
    )
    return row


@transaction.atomic
def attach_file(*, reference, user_id: int, uploaded_file):
    complaint = (
        Complaint.objects.select_for_update()
        .filter(reference=reference, complainant_user_id=user_id)
        .first()
    )
    if complaint is None:
        from core.api.exceptions import NotFoundError

        raise NotFoundError("No such complaint.")
    if complaint.status not in (sm.SUBMITTED, sm.IN_PROGRESS):
        raise InvalidSubmission("Attachments can only be added to an active complaint.")
    if complaint.attachments.count() >= settings.CMS_ATTACHMENT_MAX_COUNT:
        raise InvalidSubmission("The complaint has reached its attachment limit.")
    row, _ = _persist_attachment(
        complaint, user_id, uploaded_file, _validate_attachment_file(uploaded_file)
    )
    return row


def _validate_attachment_file(uploaded_file):
    max_bytes = settings.CMS_ATTACHMENT_MAX_BYTES
    if uploaded_file.size > max_bytes:
        raise InvalidSubmission(f"Attachment exceeds the {max_bytes}-byte limit.")
    content = bytearray()
    for chunk in uploaded_file.chunks():
        content.extend(chunk)
        if len(content) > max_bytes:
            raise InvalidSubmission(f"Attachment exceeds the {max_bytes}-byte limit.")
    mime = _sniff_mime(content)
    if mime not in settings.CMS_ATTACHMENT_ALLOWED_TYPES:
        raise InvalidSubmission("Only PDF, JPEG, and PNG attachments are accepted.")
    original_name = pathlib.PurePath(uploaded_file.name.replace("\\", "/")).name
    original_name = original_name[:120] or "attachment"
    return bytes(content), mime, original_name


def _persist_attachment(complaint, user_id, uploaded_file, validated):
    from modules.complaints.models import ComplaintAttachment

    content, mime, original_name = validated
    key = uuid.uuid4().hex + uuid.uuid4().hex
    path = storage.path_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(content)
        row = ComplaintAttachment.objects.create(
            complaint=complaint,
            storage_key=key,
            original_name=original_name,
            content_type=mime,
            byte_size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            uploaded_by_user_id=user_id,
        )
        ComplaintHistory.objects.create(
            complaint=complaint,
            event="attachment_added",
            actor_user_id=user_id,
            actor_kind=sm.COMPLAINANT,
            details=f"Attachment added: {original_name}",
        )
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return row, path


def _sniff_mime(content: bytes | bytearray) -> str:
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return "application/octet-stream"
