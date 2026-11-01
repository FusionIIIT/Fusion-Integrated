"""Idempotent processing of event-triggered IAA use cases."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.iaa.domain import state_machine as sm
from modules.iaa.models import (
    ActionHistory, Anomaly, ApprovalStep, AutomaticAnomalyEvent,
    AutomaticAnomalyRule,
)
from modules.iaa.services.records import _notify


@transaction.atomic
def escalate_overdue(*, now=None, limit=200):
    now = now or timezone.now()
    steps = list(ApprovalStep.objects.select_for_update(skip_locked=True).filter(
        status="Pending", due_at__isnull=False, due_at__lte=now
    ).order_by("due_at", "id")[:limit])
    escalated = 0
    for step in steps:
        model = ("request" if step.record_type == "request" else "ta_claim")
        from modules.iaa.models import ExpenseVoucherRequest, TravelAllowanceClaim
        record_model = ExpenseVoucherRequest if model == "request" else TravelAllowanceClaim
        record = record_model.objects.select_for_update().filter(pk=step.record_id).first()
        if record is None or record.status not in ("Finance Validated", "Approval Pending"):
            step.status = "Superseded"; step.save(update_fields=("status",)); continue
        following = ApprovalStep.objects.filter(
            record_type=step.record_type, record_id=step.record_id,
            status="Queued", level__gt=step.level).order_by("level", "id").first()
        if following:
            next_user, next_role, next_level = following.assigned_user_id, following.authority_role, following.level
            following.status = "Escalated"
            following.due_at = (now + timezone.timedelta(seconds=following.timeout_seconds)
                                if following.timeout_seconds else None)
            following.escalated_from_id = step.pk
            following.save(update_fields=("status", "due_at", "escalated_from_id"))
        else:
            used = set(ApprovalStep.objects.filter(
                record_type=step.record_type, record_id=step.record_id
            ).values_list("authority_role", flat=True))
            next_role = next((r for r in step.escalation_roles if r not in used), None)
            if next_role is None:
                # Keep the pending action visible; there is no configured next
                # eligible authority and no transition may be invented.
                ActionHistory.objects.create(
                    record_type=step.record_type, record_id=step.record_id,
                    source_status=record.status, destination_status=record.status,
                    action="escalation_route_unavailable", actor_role=sm.SYSTEM,
                    details={"approval_step_id": step.pk})
                continue
            from modules.iaa.services.records import _eligible_users
            creator_id = getattr(record, "created_by_id", None) or getattr(record, "claimant_user_id", None)
            users = _eligible_users(next_role, record.department, exclude=(creator_id,))
            if not users:
                continue
            next_user, next_level = users[0], step.level
            ApprovalStep.objects.create(
                record_type=step.record_type, record_id=step.record_id,
                level=next_level, authority_role=next_role,
                assigned_user_id=next_user, status="Escalated",
                due_at=(now + timezone.timedelta(seconds=step.timeout_seconds)
                        if step.timeout_seconds else None),
                escalated_from_id=step.pk, timeout_seconds=step.timeout_seconds,
                escalation_roles=step.escalation_roles)
        source = record.status
        try:
            transition = sm.validate_transition(model, source, "Escalated", sm.SYSTEM,
                                                values={"overdue": True})
        except (sm.InvalidTransition, sm.ActorNotAllowed, sm.GuardFailed):
            continue
        step.status = "Superseded"; step.resolved_at = now
        step.save(update_fields=("status", "resolved_at"))
        record.status = transition.destination
        record.current_approval_level = next_level
        record.updated_at = now
        record.save(update_fields=("status", "current_approval_level", "updated_at"))
        ActionHistory.objects.create(
            record_type=model, record_id=record.pk, source_status=source,
            destination_status="Escalated", action="approval_escalated",
            actor_role=sm.SYSTEM, details={"from_step_id": step.pk,
                                          "assigned_user_id": next_user,
                                          "authority_role": next_role})
        _notify(next_user, next_role, "approval_escalated", "Approval escalated",
                "An overdue IAA approval has been assigned to you.", model, record.pk)
        escalated += 1
    return escalated


@transaction.atomic
def process_automatic_anomalies(*, limit=200, now=None):
    now = now or timezone.now()
    events = list(AutomaticAnomalyEvent.objects.select_for_update(skip_locked=True)
                  .filter(processed_at__isnull=True).order_by("created_at", "id")[:limit])
    processed = 0
    for event in events:
        rule = AutomaticAnomalyRule.objects.filter(
            condition=event.condition, is_active=True).first()
        if rule is None:
            continue
        anomaly = Anomaly.objects.filter(
            record_type=event.record_type, record_id=event.record_id,
            category=rule.category, created_by_id__isnull=True).first()
        if anomaly is None:
            anomaly = Anomaly.objects.create(
                record_type=event.record_type, record_id=event.record_id,
                category=rule.category,
                description=rule.description or "Configured budget insufficiency condition.",
                resolver_role=rule.resolver_role,
                assigned_user_id=rule.assigned_user_id,
                created_by_role=sm.SYSTEM)
        ActionHistory.objects.create(
            record_type="anomaly", record_id=anomaly.pk,
            destination_status="Open", action="automatic_anomaly_created",
            actor_role=sm.SYSTEM,
            details={"condition": event.condition,
                     "target_type": event.record_type,
                     "target_id": event.record_id,
                     "context": event.context})
        if rule.assigned_user_id:
            _notify(rule.assigned_user_id, rule.resolver_role,
                    "anomaly_created", "Material anomaly requires review",
                    anomaly.description, "anomaly", anomaly.pk)
        event.processed_at = now
        event.save(update_fields=("processed_at",))
        processed += 1
    return processed
