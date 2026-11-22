"""Policy-driven HR-EIS notification creation and official-email handoff."""

from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.directory.contracts import get_users
from modules.hreis.models import (
    ApprovalRouteStep,
    AuditEvent,
    HRPolicyVersion,
    HRRequest,
    Notification,
    OutboxEvent,
)
from modules.hreis.selectors.scoping import notifications_for
from modules.hreis.services.authz import require

_PENDING = frozenset(
    {
        "pending_authority",
        "awaiting_hr_verification",
        "submitted",
        "pending_review",
        "pending_next_appraisal_authority",
    }
)


@transaction.atomic
def mark_notification_read(actor, *, notification_id: int):
    require(actor, "hreis.notification.view")
    row = (
        notifications_for(actor)
        .select_for_update(of=("self",))
        .filter(pk=notification_id)
        .first()
    )
    if row is None:
        raise NotFoundError(
            "Open HR Notifications and choose an available notice.",
            code="notification_not_found",
        )
    if row.read_at is None:
        row.read_at = timezone.now()
        row.save(update_fields=["read_at"])
        AuditEvent.objects.create(
            event_key=f"notification-read:{row.pk}:{actor.user_id}",
            actor_user_id=actor.user_id,
            acting_designation=actor.active_role,
            subject_user_id=actor.user_id,
            action="notification_read",
            resource_kind="notification",
            resource_id=row.pk,
            data={},
        )
    return row


@transaction.atomic
def _enqueue(*, tag: str, user_id: int, title: str, message: str, row=None, policy=None):
    """One-time emission of a dashboard message, audited along with its outbox."""
    notice, created = Notification.objects.get_or_create(
        event_key=f"notification:{tag}",
        defaults={
            "recipient_user_id": user_id,
            "request": row,
            "title": title,
            "message": message,
        },
    )
    if not created:
        return False
    OutboxEvent.objects.create(
        event_key=f"outbox:{tag}",
        event_type="hreis.notification",
        payload={
            "notification_id": notice.pk,
            "recipient_user_id": user_id,
        },
    )
    AuditEvent.objects.create(
        event_key=f"notice-audit:{tag}",
        actor_user_id=None,
        acting_designation="system",
        subject_user_id=user_id,
        action="notification_generated",
        resource_kind="hr_request" if row else "policy",
        resource_id=row.pk if row else policy.pk,
        data={"notification_id": notice.pk, "type": "reminder" if row else "policy_notice"},
    )
    return True


def _current_action(row):
    """Return a currently responsible designation and, when assigned, user IDs."""
    if row.state == "awaiting_hr_verification" or (
        row.family == "appraisal" and row.state == "submitted"
    ):
        return "hradmin", None
    step = ApprovalRouteStep.objects.filter(request=row, position=row.route_step).first()
    if step is None:
        return None, None
    assigned_ids = None
    if row.family == "appraisal" and row.route_step == 0:
        assigned_ids = set(row.appraisal.reviewer_user_ids)
    return step.designation, assigned_ids


def create_pending_action_reminders(*, now=None) -> int:
    """HR-UC-021: generate at most one reminder per unchanged action/recipient."""
    now = now or timezone.now()
    count = 0
    rows = (
        HRRequest.objects.filter(state__in=_PENDING, policy_version__isnull=False)
        .select_related("policy_version", "appraisal")
        .order_by("pk")
    )
    for row in rows.iterator(chunk_size=200):
        config = row.policy_version.parameters.get("conditions", {})
        if not isinstance(config, dict):
            continue
        after_hours = config.get("pending_reminder_after_hours")
        recipients = config.get("reminder_recipients")
        if (
            type(after_hours) is not int
            or after_hours <= 0
            or not isinstance(recipients, dict)
            or (now - row.updated_at).total_seconds() < after_hours * 3600
        ):
            continue
        role, directly_assigned = _current_action(row)
        if not role:
            continue
        selected = recipients.get(role, [])
        if not isinstance(selected, list):
            continue
        for user_id in sorted({uid for uid in selected if type(uid) is int and uid > 0}):
            if user_id == row.user_id or (
                directly_assigned is not None and user_id not in directly_assigned
            ):
                continue
            if _enqueue(
                tag=f"reminder:{row.pk}:{row.version}:{user_id}",
                user_id=user_id,
                row=row,
                title="HR-EIS action reminder",
                message="An HR request awaits your assigned action. Open HR-EIS to review it.",
            ):
                count += 1
    return count


def create_policy_deadline_notifications(*, now=None) -> int:
    """HR-UC-022: notify only for explicitly configured deadline events."""
    now = now or timezone.now()
    count = 0
    for policy in HRPolicyVersion.objects.filter(
        effective_from__lte=now,
    ).order_by("pk"):
        if policy.effective_until and policy.effective_until <= now:
            continue
        config = policy.parameters.get("conditions", {})
        if not isinstance(config, dict):
            continue
        due_at = config.get("policy_notice_at")
        recipients = config.get("policy_notice_recipients")
        if not isinstance(due_at, str) or not isinstance(recipients, list):
            continue
        try:
            notice_at = datetime.fromisoformat(due_at)
        except ValueError:
            continue
        if timezone.is_naive(notice_at) or now < notice_at:
            continue
        for user_id in sorted({uid for uid in recipients if type(uid) is int and uid > 0}):
            if _enqueue(
                tag=f"policy:{policy.pk}:{user_id}",
                user_id=user_id,
                policy=policy,
                title="HR-EIS policy or deadline notice",
                message=(
                    f"A configured {policy.family.upper()} policy or deadline update "
                    "requires your attention in HR-EIS."
                ),
            ):
                count += 1
    return count


def _deliver_one(pk, notices, users):
    with transaction.atomic():
        event = (
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(
                pk=pk,
                event_type="hreis.notification",
                dispatched_at__isnull=True,
                attempts__lt=5,
            )
            .first()
        )
        if event is None:
            return (0, 0)
        tag = f"notification:{event.event_key.removeprefix('outbox:')}"
        notice = notices.get(tag)
        user = users.get(notice.recipient_user_id) if notice else None
        email = (
            (getattr(user, "email", "") or "").strip() if getattr(user, "is_active", True) else ""
        )
        if not email:
            event.attempts += 1
            event.save(update_fields=["attempts"])
            return (0, 1)
        try:
            result = send_mail(
                subject=notice.title,
                message=notice.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:  # noqa: BLE001 - keep a failed outbox row retryable for any mail provider error
            event.attempts += 1
            event.save(update_fields=["attempts"])
            return (0, 1)
        if result != 1:
            event.attempts += 1
            event.save(update_fields=["attempts"])
            return (0, 1)
        event.attempts += 1
        event.dispatched_at = timezone.now()
        event.save(update_fields=["attempts", "dispatched_at"])
        return (1, 0)


def deliver_pending_notifications(*, limit=100) -> tuple[int, int]:
    """Hand durable notifications to the configured Django email backend."""
    if type(limit) is not int or limit < 1:
        raise ValueError("Notification delivery limit must be a positive integer.")
    queued = list(
        OutboxEvent.objects.filter(
            event_type="hreis.notification",
            dispatched_at__isnull=True,
            attempts__lt=5,
        )
        .order_by("queued_at", "pk")
        .values_list("pk", "event_key")[:limit]
    )
    if not queued:
        return (0, 0)

    tags = [
        f"notification:{event_key.removeprefix('outbox:')}"
        for _, event_key in queued
        if event_key.startswith("outbox:")
    ]
    notices = {n.event_key: n for n in Notification.objects.filter(event_key__in=tags)}
    user_ids = sorted({n.recipient_user_id for n in notices.values()})
    try:
        users = get_users(user_ids)
    except Exception:  # noqa: BLE001 - keep a failed outbox row retryable for any mail provider error
        # An unavailable IAM is not evidence that email was delivered.
        return (0, len(queued))

    sent = failed = 0
    for pk, _event_key in queued:
        delivered, retryable = _deliver_one(pk, notices, users)
        sent += delivered
        failed += retryable
    return sent, failed
