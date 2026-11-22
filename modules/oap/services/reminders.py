"""Pending-action reminders (OA-UC-92). Silent until an institute policy exists."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from modules.oap.domain import assistantship as asd
from modules.oap.domain import state_machines as sm
from modules.oap.models import AssistantshipClaim, Notification, ReminderPolicy
from modules.oap.services import notifications


def current_policy(now=None):
    now = now or timezone.now()
    return (
        ReminderPolicy.objects.filter(effective_from__lte=now).order_by("-effective_from").first()
    )


def send_due_reminders(now=None) -> dict[str, object]:
    now = now or timezone.now()
    policy = current_policy(now)
    if policy is None:
        return {"sent": 0, "reason": "no reminder policy has been set"}
    cutoff = now - timedelta(hours=policy.after_hours)
    sent = 0
    claims = AssistantshipClaim.objects.filter(
        status__in=[sm.CLAIM_AWAITING_DUAL, sm.CLAIM_AWAITING_OTHER], created_at__lte=cutoff
    )
    for claim in claims:
        recorded = list(claim.verifications.values_list("role", flat=True))
        supervisors = [
            claim.thesis_supervisor_user_id if role == asd.THESIS else claim.ta_supervisor_user_id
            for role in asd.pending_roles(recorded)
        ]
        subject = f"Reminder: assistantship claim #{claim.pk} awaits your verification"
        already = set(
            Notification.objects.filter(
                recipient_user_id__in=supervisors, subject=subject, created_at__gte=cutoff
            ).values_list("recipient_user_id", flat=True)
        )
        due = [s for s in supervisors if s not in already]
        if due:
            notifications.notify(due, subject, "Please verify this claim in the OAP module.")
            sent += len(set(due))
    return {"sent": sent, "reason": "ok"}
