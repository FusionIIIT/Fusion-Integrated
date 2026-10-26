"""SLA threshold processing for ELM (EL-UC-021).

This is the event-triggered side of the SLA feature. It reads open tasks and
the administrator's configuration, hands both to the pure evaluator in
`domain/sla.py`, and then performs whatever the evaluator decided:

  * BR-EL-032 -- remind the responsible user, and log it (AFR-EL-031.2/.3)
  * BR-EL-033 -- escalate to the configured authority, apply the routing
    change where configured, and log it (AFR-EL-032.2/.3)
  * BR-EL-032/033 suppression -- a task that is no longer pending produces no
    reminder and no escalation (AFR-EL-031.4, AFR-EL-032.4)

Suppressed evaluations are logged with their reason code, because EL-UC-021's
minimal guarantee is a negative and a negative is only auditable if the
decision not to act was written down.
"""
from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.elm.domain.notifications import compose_for_decision
from modules.elm.domain.sla import (
    DEFAULT_THRESHOLD_HOURS,
    InvalidSlaThreshold,
    SlaAction,
    SlaDecision,
    SlaThresholds,
    TaskKind,
    TaskSnapshot,
    evaluate_tasks,
)
from modules.elm.models import SLAConfiguration, SLAEventLog, WorkflowTask
from modules.elm.services.notifications import application_ref, deliver


def _to_thresholds(config: SLAConfiguration) -> SlaThresholds:
    return SlaThresholds(
        task_kind=TaskKind(config.task_kind),
        reminder_hours=float(config.reminder_hours),
        escalation_hours=float(config.escalation_hours),
        escalation_role=config.escalation_role,
        escalation_recipient_id=config.escalation_recipient_id,
        escalation_changes_routing=config.escalation_changes_routing,
        is_active=config.is_active,
    )


def load_threshold_map() -> dict[str, SlaThresholds]:
    """Current configuration, keyed by task kind.

    A kind with no row is absent from the map, and the evaluator treats that
    as `sla_not_configured` rather than falling back to a built-in number --
    BR-EL-038 puts the thresholds under administrator control, so a silent
    default would take the feature out of their hands.
    """
    out: dict[str, SlaThresholds] = {}
    for config in SLAConfiguration.objects.all():
        try:
            out[config.task_kind] = _to_thresholds(config)
        except ValueError:
            # A row for a task kind this build no longer defines. Skip it
            # rather than failing the whole run.
            continue
    return out


def _snapshot(task: WorkflowTask) -> TaskSnapshot:
    return TaskSnapshot(
        task_id=task.id,
        task_kind=task.task_kind,
        assignee_id=task.assignee_id,
        opened_at=task.opened_at,
        is_pending=task.is_pending,
        reminded_at=task.reminded_at,
        escalated_at=task.escalated_at,
    )


def _log(decision: SlaDecision, now: datetime.datetime) -> SLAEventLog:
    return SLAEventLog.objects.create(
        task_id=decision.task_id,
        task_kind=str(decision.task_kind.value),
        action=decision.action.value,
        reason=decision.reason.value,
        recipient_id=decision.recipient_id,
        escalation_role=decision.escalation_role,
        changes_routing=decision.changes_routing,
        hours_elapsed=round(decision.hours_elapsed, 2),
        evaluated_at=now,
    )


def process_sla_thresholds(
    now: datetime.datetime | None = None,
    task_ids: list[int] | None = None,
    log_suppressed: bool = True,
) -> dict[str, int]:
    """Evaluate SLA thresholds and act on the results (EL-UC-021).

    `task_ids` narrows the run to specific tasks, which is how a single
    threshold event is processed; omitting it sweeps every open task, which is
    how a scheduled pass works. Either way the pending check is re-read inside
    the transaction, so a task closed between the scan and the write is not
    reminded.

    Returns counters: reminded, escalated, rerouted, suppressed.
    """
    now = now or timezone.now()
    thresholds = load_threshold_map()

    qs = WorkflowTask.objects.filter(status=WorkflowTask.STATUS_OPEN).select_related(
        "application", "application__leave_type"
    )
    if task_ids:
        qs = qs.filter(id__in=task_ids)

    tasks = list(qs)
    by_id = {t.id: t for t in tasks}
    decisions = evaluate_tasks([_snapshot(t) for t in tasks], thresholds, now)

    counters = {"reminded": 0, "escalated": 0, "rerouted": 0, "suppressed": 0, "evaluated": len(decisions)}

    for decision in decisions:
        task = by_id.get(decision.task_id)
        if task is None:
            continue

        if not decision.is_actionable:
            counters["suppressed"] += 1
            if log_suppressed:
                _log(decision, now)
            continue

        acted = _apply_decision(task, decision, now)
        if acted is None:
            # Lost the race: the task was closed or already actioned between
            # the scan and the write. Nothing is sent.
            counters["suppressed"] += 1
            continue

        if decision.action is SlaAction.REMIND:
            counters["reminded"] += 1
        elif decision.action is SlaAction.ESCALATE:
            counters["escalated"] += 1
            if decision.changes_routing:
                counters["rerouted"] += 1

    return counters


def _apply_decision(
    task: WorkflowTask,
    decision: SlaDecision,
    now: datetime.datetime,
) -> SLAEventLog | None:
    """Send, reroute and log one actionable decision, atomically.

    The stamp update is written as a conditional queryset UPDATE: it matches
    only while the task is still OPEN and still unstamped for this action. If
    two passes overlap, the second matches zero rows and returns None, so a
    recipient cannot receive the same reminder twice.
    """
    with transaction.atomic():
        guard = {"id": task.id, "status": WorkflowTask.STATUS_OPEN}
        fields: dict[str, object] = {"updated_at": now}

        if decision.action is SlaAction.REMIND:
            guard["reminded_at__isnull"] = True
            fields["reminded_at"] = now
        else:
            guard["escalated_at__isnull"] = True
            fields["escalated_at"] = now
            fields["escalated_to_id"] = decision.recipient_id
            if decision.changes_routing and decision.recipient_id:
                # BR-EL-033: where the configured escalation changes
                # routing/responsibility, apply it. The clock restarts for the
                # new owner, so the reminder stamp is cleared.
                fields["assignee_id"] = decision.recipient_id
                fields["opened_at"] = now
                fields["reminded_at"] = None

        updated = WorkflowTask.objects.filter(**guard).update(**fields)
        if not updated:
            return None

        recipient_id = decision.recipient_id
        if recipient_id:
            message = compose_for_decision(
                decision=decision,
                recipient_id=recipient_id,
                application_ref=application_ref(task.application),
                original_assignee_ref=(
                    f"user {decision.original_assignee_id}" if decision.original_assignee_id else ""
                ),
            )
            if message is not None:
                deliver(message, task_id=task.id)

        # Logged whether or not a recipient was configured, so an escalation
        # that could not be addressed is visible instead of silent.
        return _log(decision, now)


def configure_thresholds(
    actor,
    task_kind: str,
    reminder_hours: float,
    escalation_hours: float,
    escalation_role: str = "",
    escalation_recipient_id: int | None = None,
    escalation_changes_routing: bool = False,
    is_active: bool = True,
) -> SLAConfiguration:
    """Create or update the thresholds for one task kind (EL-UC-018, BR-EL-038).

    Validation runs in the domain before anything is written, so UC-018's
    failure guarantee holds: an invalid configuration is not applied.
    """
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    if hasattr(actor, "has_permission") and not actor.has_permission("leave_elm.sla.manage"):
        raise PermissionDeniedError(
            "This action needs leave_elm.sla.manage.", code="permission_denied"
        )

    try:
        kind = TaskKind(task_kind)
    except ValueError:
        raise BadRequestError(
            f"Unknown actionable task kind '{task_kind}'.", code="unknown_task_kind"
        ) from None

    candidate = SlaThresholds(
        task_kind=kind,
        reminder_hours=float(reminder_hours),
        escalation_hours=float(escalation_hours),
        escalation_role=escalation_role,
        escalation_recipient_id=escalation_recipient_id,
        escalation_changes_routing=escalation_changes_routing,
        is_active=is_active,
    )
    try:
        candidate.validate()
    except InvalidSlaThreshold as exc:
        raise BadRequestError(str(exc), code="invalid_sla_threshold") from exc

    config, _ = SLAConfiguration.objects.update_or_create(
        task_kind=kind.value,
        defaults={
            "reminder_hours": candidate.reminder_hours,
            "escalation_hours": candidate.escalation_hours,
            "escalation_role": candidate.escalation_role,
            "escalation_recipient_id": candidate.escalation_recipient_id,
            "escalation_changes_routing": candidate.escalation_changes_routing,
            "is_active": candidate.is_active,
            "updated_by_id": user_id,
        },
    )
    return config


def seed_default_thresholds() -> int:
    """Populate any unconfigured task kind with its seed thresholds.

    Idempotent, and never overwrites an administrator's value. Exists so the
    feature is not dark on a fresh install; BR-EL-038 still governs the
    numbers once an administrator touches them.
    """
    created = 0
    existing = set(SLAConfiguration.objects.values_list("task_kind", flat=True))
    for kind, (reminder, escalation) in DEFAULT_THRESHOLD_HOURS.items():
        if kind.value in existing:
            continue
        SLAConfiguration.objects.create(
            task_kind=kind.value,
            reminder_hours=reminder,
            escalation_hours=escalation,
            escalation_role="",
            escalation_recipient_id=None,
            escalation_changes_routing=False,
            is_active=True,
        )
        created += 1
    return created
