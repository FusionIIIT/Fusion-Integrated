"""Services executing business workflows for the Complaint Management System."""
import datetime
from typing import Any, List, Optional
from django.db import transaction
from django.utils import timezone

from modules.complaints.domain.errors import (
    ActiveRoleConstraintError,
    ComplaintAlreadyEscalated,
    ComplaintNotClosed,
    ComplaintNotResolved,
    ComplaintPermissionDenied,
    ComplaintValidationError,
)
from modules.complaints.domain.state_machine import (
    ClosureVerification,
    ComplaintPriority,
    ComplaintStatus,
    EscalationType,
    ReopeningStatus,
    validate_transition,
)
from modules.complaints.models import (
    CmsRoleAssignment,
    Complaint,
    ComplaintAnnouncement,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintFeedback,
    ComplaintTransition,
)


def _generate_complaint_id() -> str:
    """Generate a unique human-readable complaint identifier, e.g. CMP-20261101-0001."""
    today_str = timezone.now().strftime("%Y%m%d")
    prefix = f"CMP-{today_str}-"
    last = (
        Complaint.objects.filter(complaint_id__startswith=prefix)
        .order_by("-complaint_id")
        .first()
    )
    if last:
        try:
            seq = int(last.complaint_id.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _calculate_sla_deadline(priority: str, category: ComplaintCategory) -> datetime.datetime:
    """Calculate deadline based on priority and category defaults."""
    now = timezone.now()
    hours_map = {
        ComplaintPriority.HIGH.value: 24,
        ComplaintPriority.MEDIUM.value: 48,
        ComplaintPriority.LOW.value: 72,
    }
    hours = hours_map.get(priority, category.default_sla_hours or 48)
    return now + datetime.timedelta(hours=hours)


@transaction.atomic
def submit_complaint(
    *,
    complainant_user_id: int,
    category_id: int,
    location: str,
    description: str,
    priority: str = ComplaintPriority.MEDIUM.value,
    verification_required: str = ClosureVerification.NONE.value,
    attachments: Optional[List[Any]] = None,
) -> Complaint:
    """UC-CMS-001: Submit Complaint."""
    if not description or not description.strip():
        raise ComplaintValidationError("Complaint description is mandatory.")
    if not location or not location.strip():
        raise ComplaintValidationError("Complaint location is mandatory.")

    try:
        category = ComplaintCategory.objects.get(pk=category_id, is_active=True)
    except ComplaintCategory.DoesNotExist as exc:
        raise ComplaintValidationError("Valid active complaint category is required.") from exc

    if priority not in [p.value for p in ComplaintPriority]:
        priority = ComplaintPriority.MEDIUM.value
    if verification_required not in [v.value for v in ClosureVerification]:
        verification_required = ClosureVerification.NONE.value

    complaint_id = _generate_complaint_id()
    sla_deadline = _calculate_sla_deadline(priority, category)

    complaint = Complaint.objects.create(
        complaint_id=complaint_id,
        complainant_user_id=complainant_user_id,
        category=category,
        location=location.strip(),
        description=description.strip(),
        status=ComplaintStatus.SUBMITTED.value,
        priority=priority,
        verification_required=verification_required,
        sla_deadline=sla_deadline,
    )

    # Save attachments if provided
    if attachments:
        for f in attachments:
            ComplaintAttachment.objects.create(
                complaint=complaint,
                file=f,
                file_name=getattr(f, "name", "attachment"),
                file_size=getattr(f, "size", 0),
                uploaded_by_user_id=complainant_user_id,
            )

    # Audit transition
    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status="",
        to_status=ComplaintStatus.SUBMITTED.value,
        actor_user_id=complainant_user_id,
        actor_role="complainant",
        remarks="Complaint submitted by user.",
    )

    return complaint


@transaction.atomic
def assign_and_prioritize_complaint(
    *,
    complaint: Complaint,
    actor_user_id: int,
    worker_id: Optional[int] = None,
    worker_name: str = "",
    priority: Optional[str] = None,
    category_id: Optional[int] = None,
    remarks: str = "",
) -> Complaint:
    """UC-CMS-004: Assign, Categorize, and Prioritize Complaint."""
    update_fields = ["updated_at"]

    if worker_id is not None:
        complaint.assigned_worker_id = worker_id
        update_fields.append("assigned_worker_id")
    if worker_name:
        complaint.assigned_worker_name = worker_name
        update_fields.append("assigned_worker_name")

    if priority and priority in [p.value for p in ComplaintPriority]:
        complaint.priority = priority
        complaint.sla_deadline = _calculate_sla_deadline(priority, complaint.category)
        update_fields.extend(["priority", "sla_deadline"])

    if category_id:
        try:
            category = ComplaintCategory.objects.get(pk=category_id, is_active=True)
            complaint.category = category
            update_fields.append("category")
        except ComplaintCategory.DoesNotExist as exc:
            raise ComplaintValidationError("Specified category does not exist.") from exc

    complaint.save(update_fields=update_fields)

    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=complaint.status,
        to_status=complaint.status,
        actor_user_id=actor_user_id,
        actor_role="complaint_handler",
        remarks=remarks or f"Handling setup updated: Worker='{worker_name}', Priority='{complaint.priority}'.",
    )
    return complaint


@transaction.atomic
def update_complaint_progress(
    *,
    complaint: Complaint,
    actor_user_id: int,
    progress_notes: str,
) -> Complaint:
    """UC-CMS-005: Update Complaint Progress."""
    if not progress_notes or not progress_notes.strip():
        raise ComplaintValidationError("Progress notes cannot be empty.")

    old_status = complaint.status
    update_fields = ["updated_at"]

    # If submitted, progress update advances status to in_progress per STT
    if complaint.status == ComplaintStatus.SUBMITTED.value:
        validate_transition(complaint.status, ComplaintStatus.IN_PROGRESS.value)
        complaint.status = ComplaintStatus.IN_PROGRESS.value
        update_fields.append("status")

    complaint.save(update_fields=update_fields)

    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=old_status,
        to_status=complaint.status,
        actor_user_id=actor_user_id,
        actor_role="complaint_handler",
        remarks=progress_notes.strip(),
    )
    return complaint


@transaction.atomic
def resolve_complaint(
    *,
    complaint: Complaint,
    actor_user_id: int,
    resolution_details: str,
) -> Complaint:
    """UC-CMS-006: Resolve Complaint."""
    if not resolution_details or not resolution_details.strip():
        raise ComplaintValidationError("Resolution details are mandatory to resolve a complaint.")

    now = timezone.now()
    old_status = complaint.status

    # If no verification required, resolving directly closes it; otherwise moves to resolved
    target_status = (
        ComplaintStatus.CLOSED.value
        if complaint.verification_required == ClosureVerification.NONE.value
        else ComplaintStatus.RESOLVED.value
    )

    validate_transition(old_status, ComplaintStatus.RESOLVED.value)
    if target_status == ComplaintStatus.CLOSED.value:
        validate_transition(ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value)

    complaint.status = target_status
    complaint.resolution_details = resolution_details.strip()
    complaint.resolved_at = now
    update_fields = ["status", "resolution_details", "resolved_at", "updated_at"]

    if target_status == ComplaintStatus.CLOSED.value:
        complaint.closed_at = now
        update_fields.append("closed_at")

    complaint.save(update_fields=update_fields)

    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=old_status,
        to_status=target_status,
        actor_user_id=actor_user_id,
        actor_role="complaint_handler",
        remarks=f"Resolved: {resolution_details.strip()}",
    )
    return complaint


@transaction.atomic
def reject_complaint(
    *,
    complaint: Complaint,
    actor_user_id: int,
    rejection_reason: str,
) -> Complaint:
    """UC-CMS-006: Reject Complaint."""
    if not rejection_reason or not rejection_reason.strip():
        raise ComplaintValidationError("Rejection reason is mandatory.")

    now = timezone.now()
    old_status = complaint.status

    validate_transition(old_status, ComplaintStatus.REJECTED.value)

    complaint.status = ComplaintStatus.REJECTED.value
    complaint.rejection_reason = rejection_reason.strip()
    complaint.rejected_at = now
    complaint.save(update_fields=["status", "rejection_reason", "rejected_at", "updated_at"])

    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=old_status,
        to_status=ComplaintStatus.REJECTED.value,
        actor_user_id=actor_user_id,
        actor_role="complaint_handler",
        remarks=f"Rejected: {rejection_reason.strip()}",
    )
    return complaint


@transaction.atomic
def verify_and_close_complaint(
    *,
    complaint: Complaint,
    actor_user_id: int,
    actor_role: str,
    remarks: str = "",
) -> Complaint:
    """UC-CMS-007 / UC-CMS-019: Verify Resolved Complaint for Closure."""
    if complaint.status != ComplaintStatus.RESOLVED.value:
        raise ComplaintNotResolved("Only complaints in 'resolved' status can be verified for closure.")

    if complaint.verification_required == ClosureVerification.USER.value:
        if complaint.complainant_user_id != actor_user_id:
            raise ComplaintPermissionDenied("Only the original complainant can verify this resolution.")
    elif complaint.verification_required == ClosureVerification.SUPERVISOR.value:
        if actor_role not in ("complaint_supervisor", "admin"):
            raise ComplaintPermissionDenied("Supervisor role is required to verify this closure.")

    now = timezone.now()
    validate_transition(complaint.status, ComplaintStatus.CLOSED.value)

    complaint.status = ComplaintStatus.CLOSED.value
    complaint.closed_at = now
    complaint.save(update_fields=["status", "closed_at", "updated_at"])

    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=ComplaintStatus.RESOLVED.value,
        to_status=ComplaintStatus.CLOSED.value,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        remarks=remarks or "Resolution verified and complaint closed.",
    )
    return complaint


@transaction.atomic
def request_reopening(
    *,
    complaint: Complaint,
    complainant_user_id: int,
    reopening_reason: str,
) -> Complaint:
    """UC-CMS-008: Request Complaint Reopening."""
    if complaint.status != ComplaintStatus.CLOSED.value:
        raise ComplaintNotClosed("Only closed complaints can be requested for reopening.")
    if complaint.complainant_user_id != complainant_user_id:
        raise ComplaintPermissionDenied("Only the original complainant can request reopening.")
    if not reopening_reason or not reopening_reason.strip():
        raise ComplaintValidationError("Reason for reopening request is mandatory.")

    complaint.reopening_status = ReopeningStatus.PENDING.value
    complaint.reopening_reason = reopening_reason.strip()
    complaint.save(update_fields=["reopening_status", "reopening_reason", "updated_at"])

    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=complaint.status,
        to_status=complaint.status,
        actor_user_id=complainant_user_id,
        actor_role="complainant",
        remarks=f"Reopening requested: {reopening_reason.strip()}",
    )
    return complaint


@transaction.atomic
def review_reopening_request(
    *,
    complaint: Complaint,
    supervisor_user_id: int,
    approved: bool,
    review_remarks: str = "",
) -> Complaint:
    """UC-CMS-020: Review Complaint Reopening Request."""
    if complaint.reopening_status != ReopeningStatus.PENDING.value:
        raise ComplaintValidationError("Complaint does not have a pending reopening request.")

    old_status = complaint.status

    if approved:
        # BW-CMS-06: Approved reopening returns complaint to in_progress
        validate_transition(old_status, ComplaintStatus.IN_PROGRESS.value)
        complaint.status = ComplaintStatus.IN_PROGRESS.value
        complaint.reopening_status = ReopeningStatus.APPROVED.value
        complaint.reopening_review_remarks = review_remarks.strip()
        complaint.resolved_at = None
        complaint.closed_at = None
        complaint.save(
            update_fields=[
                "status",
                "reopening_status",
                "reopening_review_remarks",
                "resolved_at",
                "closed_at",
                "updated_at",
            ]
        )
        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=old_status,
            to_status=ComplaintStatus.IN_PROGRESS.value,
            actor_user_id=supervisor_user_id,
            actor_role="complaint_supervisor",
            remarks=f"Reopening APPROVED: {review_remarks.strip()}",
        )
    else:
        # BW-CMS-05: Denied reopening remains closed
        complaint.reopening_status = ReopeningStatus.DENIED.value
        complaint.reopening_review_remarks = review_remarks.strip()
        complaint.save(update_fields=["reopening_status", "reopening_review_remarks", "updated_at"])
        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=old_status,
            to_status=old_status,
            actor_user_id=supervisor_user_id,
            actor_role="complaint_supervisor",
            remarks=f"Reopening DENIED: {review_remarks.strip()}",
        )

    return complaint


@transaction.atomic
def escalate_complaint_manually(
    *,
    complaint: Complaint,
    handler_user_id: int,
    remarks: str = "",
) -> Complaint:
    """UC-CMS-011 / BW-CMS-07: Manually Escalate Unresolved Complaint."""
    if complaint.status in (ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value, ComplaintStatus.REJECTED.value):
        raise ComplaintValidationError("Cannot escalate a resolved, closed, or rejected complaint.")
    if complaint.is_escalated:
        raise ComplaintAlreadyEscalated("Complaint is already marked as escalated.")

    complaint.is_escalated = True
    complaint.escalation_type = EscalationType.MANUAL.value
    complaint.escalated_at = timezone.now()
    complaint.escalation_remarks = remarks.strip()
    complaint.save(
        update_fields=[
            "is_escalated",
            "escalation_type",
            "escalated_at",
            "escalation_remarks",
            "updated_at",
        ]
    )

    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=complaint.status,
        to_status=complaint.status,
        actor_user_id=handler_user_id,
        actor_role="complaint_handler",
        remarks=f"Manual Escalation: {remarks.strip()}",
    )
    return complaint


@transaction.atomic
def check_and_escalate_sla_breaches() -> int:
    """UC-CMS-022 / BW-CMS-08: Automatically Escalate Complaint on SLA Breach."""
    now = timezone.now()
    unresolved_statuses = [
        ComplaintStatus.SUBMITTED.value,
        ComplaintStatus.IN_PROGRESS.value,
    ]
    breached_complaints = Complaint.objects.filter(
        status__in=unresolved_statuses,
        is_escalated=False,
        sla_deadline__isnull=False,
        sla_deadline__lt=now,
    )

    escalated_count = 0
    for complaint in breached_complaints:
        complaint.is_escalated = True
        complaint.escalation_type = EscalationType.AUTOMATIC_SLA.value
        complaint.escalated_at = now
        complaint.escalation_remarks = f"Automatic SLA escalation: breached deadline {complaint.sla_deadline}."
        complaint.save(
            update_fields=[
                "is_escalated",
                "escalation_type",
                "escalated_at",
                "escalation_remarks",
                "updated_at",
            ]
        )
        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=complaint.status,
            to_status=complaint.status,
            actor_user_id=None,
            actor_role="system",
            remarks="System automatic SLA escalation triggered.",
        )
        escalated_count += 1

    return escalated_count


@transaction.atomic
def check_and_send_sla_reminders() -> int:
    """UC-CMS-021: Trigger Pre-Breach SLA Reminder."""
    now = timezone.now()
    # Check complaints where at least 75% of SLA duration has elapsed and reminder not yet sent
    unresolved_statuses = [
        ComplaintStatus.SUBMITTED.value,
        ComplaintStatus.IN_PROGRESS.value,
    ]
    reminders = Complaint.objects.filter(
        status__in=unresolved_statuses,
        is_escalated=False,
        sla_reminder_sent=False,
        sla_deadline__isnull=False,
        sla_deadline__gt=now,
    )

    reminder_count = 0
    for complaint in reminders:
        total_duration = (complaint.sla_deadline - complaint.created_at).total_seconds()
        elapsed = (now - complaint.created_at).total_seconds()
        if total_duration > 0 and (elapsed / total_duration) >= 0.75:
            complaint.sla_reminder_sent = True
            complaint.save(update_fields=["sla_reminder_sent", "updated_at"])
            ComplaintTransition.objects.create(
                complaint=complaint,
                from_status=complaint.status,
                to_status=complaint.status,
                actor_user_id=None,
                actor_role="system",
                remarks=f"Pre-breach SLA reminder notification triggered (Deadline: {complaint.sla_deadline}).",
            )
            reminder_count += 1

    return reminder_count


@transaction.atomic
def submit_feedback(
    *,
    complaint: Complaint,
    complainant_user_id: int,
    rating: int,
    comments: str = "",
) -> ComplaintFeedback:
    """UC-CMS-009: Submit Feedback."""
    if complaint.status not in (ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value):
        raise ComplaintValidationError("Feedback can only be submitted for resolved or closed complaints.")
    if complaint.complainant_user_id != complainant_user_id:
        raise ComplaintPermissionDenied("Only the complainant can submit feedback.")
    if not (1 <= rating <= 5):
        raise ComplaintValidationError("Rating must be an integer between 1 and 5.")

    if hasattr(complaint, "feedback"):
        raise ComplaintValidationError("Feedback has already been submitted for this complaint.")

    feedback = ComplaintFeedback.objects.create(
        complaint=complaint,
        complainant_user_id=complainant_user_id,
        rating=rating,
        comments=comments.strip(),
    )
    return feedback


@transaction.atomic
def publish_announcement(
    *,
    author_user_id: int,
    author_name: str,
    title: str,
    content: str,
    category_id: Optional[int] = None,
    pinned: bool = False,
) -> ComplaintAnnouncement:
    """UC-CMS-013: Publish Complaint-Related Announcement."""
    if not title or not title.strip():
        raise ComplaintValidationError("Announcement title is mandatory.")
    if not content or not content.strip():
        raise ComplaintValidationError("Announcement content is mandatory.")

    category = None
    if category_id:
        category = ComplaintCategory.objects.filter(pk=category_id, is_active=True).first()

    return ComplaintAnnouncement.objects.create(
        author_user_id=author_user_id,
        author_name=author_name,
        title=title.strip(),
        content=content.strip(),
        category=category,
        pinned=pinned,
        is_active=True,
    )


@transaction.atomic
def assign_cms_role(
    *,
    role_type: str,
    user_id: int,
    assigned_by_user_id: int,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
) -> CmsRoleAssignment:
    """UC-CMS-018: Manage CMS Roles.

    Enforces exactly one active role-holder per role type at a time.
    Mid-cycle reassignment automatically deactivates any existing active role assignment.
    """
    if role_type not in (CmsRoleAssignment.ROLE_HANDLER, CmsRoleAssignment.ROLE_SUPERVISOR):
        raise ComplaintValidationError(f"Invalid role type: {role_type}")
    if end_date <= start_date:
        raise ComplaintValidationError("End date must be after start date.")

    # Deactivate existing active role assignments for this role_type
    CmsRoleAssignment.objects.filter(
        role_type=role_type,
        is_active=True,
    ).update(is_active=False)

    return CmsRoleAssignment.objects.create(
        role_type=role_type,
        user_id=user_id,
        assigned_by_user_id=assigned_by_user_id,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
    )
