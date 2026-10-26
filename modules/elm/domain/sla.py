"""SLA threshold evaluation for ELM actionable workflow tasks.

Pure Python: no Django, no DRF, no Celery (ADR-0003 domain purity).

Implements the decision half of:
  * BR-EL-032 -- reminder on a still-pending task (CFR-EL-031, AFR-EL-031.1-.4)
  * BR-EL-033 -- escalation on a still-pending task (CFR-EL-032, AFR-EL-032.1-.4)
  * BR-EL-038 -- configurable thresholds govern the evaluation (CFR-EL-029)

The pending-only guard is the whole point of these rules: a task that has
already been acted on must produce NO reminder and NO escalation when its
threshold is crossed. That is expressed here as an explicit decision with a
reason code rather than as an early `return None`, so the service layer can
log why nothing was issued (EL-UC-021 failure/minimal guarantee).
"""
from __future__ import annotations

import datetime
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum


class InvalidSlaThreshold(ValueError):
    """Raised when a threshold configuration is not internally consistent."""


class TaskKind(str, Enum):
    """The actionable workflow tasks ELM can place on a user.

    One kind per queue a human can be waiting in. Kinds -- not individual
    applications -- are what an administrator configures thresholds for
    (EL-UC-018 M2: "thresholds for applicable actionable task classes").
    """

    SUBSTITUTE_RESPONSE = "SUBSTITUTE_RESPONSE"
    UNIT_HEAD_REVIEW = "UNIT_HEAD_REVIEW"
    ESTABLISHMENT_ROUTING = "ESTABLISHMENT_ROUTING"
    SANCTION_DECISION = "SANCTION_DECISION"
    DIRECTOR_SELF_SANCTION = "DIRECTOR_SELF_SANCTION"
    CANCELLATION_UNIT_HEAD = "CANCELLATION_UNIT_HEAD"
    CANCELLATION_SANCTION = "CANCELLATION_SANCTION"
    EXTENSION_UNIT_HEAD = "EXTENSION_UNIT_HEAD"
    EXTENSION_SANCTION = "EXTENSION_SANCTION"
    RESUMPTION_REVIEW = "RESUMPTION_REVIEW"


class SlaAction(str, Enum):
    NONE = "NONE"
    REMIND = "REMIND"
    ESCALATE = "ESCALATE"


class SlaReason(str, Enum):
    """Why a decision came out the way it did. Logged verbatim."""

    NOT_PENDING = "task_not_pending"
    NOT_CONFIGURED = "sla_not_configured"
    CONFIG_INACTIVE = "sla_config_inactive"
    BELOW_REMINDER = "below_reminder_threshold"
    REMINDER_DUE = "reminder_threshold_reached"
    REMINDER_ALREADY_SENT = "reminder_already_issued"
    ESCALATION_DUE = "escalation_threshold_passed"
    ESCALATION_ALREADY_SENT = "escalation_already_issued"


@dataclass(frozen=True)
class SlaThresholds:
    """Administrator-configured thresholds for one task kind (BR-EL-038).

    `escalation_changes_routing` records the distinction BR-EL-033 draws
    formally: a notification-only escalation creates no workflow transition,
    whereas an escalation configured to move responsibility does, and only
    then does the cross-cutting trace to CW-EL-01..04 apply.
    """

    task_kind: TaskKind
    reminder_hours: float
    escalation_hours: float
    escalation_role: str = ""
    escalation_recipient_id: int | None = None
    escalation_changes_routing: bool = False
    is_active: bool = True

    def validate(self) -> None:
        """Reject a configuration EL-UC-018 M3 would have to refuse.

        UC-018 failure guarantee: "Invalid or unauthorized threshold changes
        are not applied."
        """
        if self.reminder_hours <= 0:
            raise InvalidSlaThreshold("Reminder threshold must be greater than zero hours.")
        if self.escalation_hours <= 0:
            raise InvalidSlaThreshold("Escalation threshold must be greater than zero hours.")
        if self.escalation_hours <= self.reminder_hours:
            raise InvalidSlaThreshold(
                "Escalation threshold must be strictly later than the reminder threshold "
                f"(got reminder={self.reminder_hours}h, escalation={self.escalation_hours}h)."
            )
        if self.escalation_changes_routing and not self.escalation_recipient_id:
            raise InvalidSlaThreshold(
                "A routing-changing escalation must name the user it routes responsibility to; "
                "a role label alone cannot be resolved to an assignee."
            )


@dataclass(frozen=True)
class TaskSnapshot:
    """A point-in-time read of one actionable task.

    `is_pending` is supplied by the caller rather than derived here: whether a
    task is still open is a persistence question, and the domain stays free of
    it. Everything else is arithmetic on timestamps.
    """

    task_id: int
    task_kind: TaskKind
    assignee_id: int
    opened_at: datetime.datetime
    is_pending: bool
    reminded_at: datetime.datetime | None = None
    escalated_at: datetime.datetime | None = None


@dataclass(frozen=True)
class SlaDecision:
    """What the service layer should do about one task, and why."""

    task_id: int
    task_kind: TaskKind
    action: SlaAction
    reason: SlaReason
    recipient_id: int | None = None
    original_assignee_id: int | None = None
    escalation_role: str = ""
    changes_routing: bool = False
    hours_elapsed: float = 0.0

    @property
    def is_actionable(self) -> bool:
        return self.action is not SlaAction.NONE


def hours_between(earlier: datetime.datetime, later: datetime.datetime) -> float:
    """Elapsed hours, never negative.

    A clock skew or a task stamped slightly in the future must not read as a
    large positive age and fire an escalation, so the floor is zero.
    """
    delta = (later - earlier).total_seconds() / 3600.0
    return delta if delta > 0 else 0.0


def evaluate_task(
    task: TaskSnapshot,
    thresholds: SlaThresholds | None,
    now: datetime.datetime,
) -> SlaDecision:
    """Decide the SLA action for a single task at `now`.

    Order of checks matters and follows EL-UC-021's main success scenario:

    1. Pending check first (step 2). A non-pending task is never reminded or
       escalated, whatever its age -- BR-EL-032/033 suppression, AFR-EL-031.4
       and AFR-EL-032.4.
    2. Escalation before reminder (steps 3-4). A task that has sat long enough
       to be escalated must escalate on this pass even if its reminder was
       never issued; emitting a stale reminder instead would delay the
       escalation by a whole cycle.
    3. Each action fires at most once per task, so repeated threshold events
       for the same task do not spam the recipient.
    """
    kind = TaskKind(task.task_kind)

    if not task.is_pending:
        return SlaDecision(
            task_id=task.task_id,
            task_kind=kind,
            action=SlaAction.NONE,
            reason=SlaReason.NOT_PENDING,
        )

    if thresholds is None:
        return SlaDecision(
            task_id=task.task_id,
            task_kind=kind,
            action=SlaAction.NONE,
            reason=SlaReason.NOT_CONFIGURED,
        )

    if not thresholds.is_active:
        return SlaDecision(
            task_id=task.task_id,
            task_kind=kind,
            action=SlaAction.NONE,
            reason=SlaReason.CONFIG_INACTIVE,
        )

    elapsed = hours_between(task.opened_at, now)

    if elapsed >= thresholds.escalation_hours:
        if task.escalated_at is not None:
            return SlaDecision(
                task_id=task.task_id,
                task_kind=kind,
                action=SlaAction.NONE,
                reason=SlaReason.ESCALATION_ALREADY_SENT,
                hours_elapsed=elapsed,
            )
        return SlaDecision(
            task_id=task.task_id,
            task_kind=kind,
            action=SlaAction.ESCALATE,
            reason=SlaReason.ESCALATION_DUE,
            # The escalation is addressed to the configured authority, not to
            # the assignee who has already failed to act on it.
            recipient_id=thresholds.escalation_recipient_id,
            original_assignee_id=task.assignee_id,
            escalation_role=thresholds.escalation_role,
            changes_routing=thresholds.escalation_changes_routing,
            hours_elapsed=elapsed,
        )

    if elapsed >= thresholds.reminder_hours:
        if task.reminded_at is not None:
            return SlaDecision(
                task_id=task.task_id,
                task_kind=kind,
                action=SlaAction.NONE,
                reason=SlaReason.REMINDER_ALREADY_SENT,
                hours_elapsed=elapsed,
            )
        return SlaDecision(
            task_id=task.task_id,
            task_kind=kind,
            action=SlaAction.REMIND,
            reason=SlaReason.REMINDER_DUE,
            recipient_id=task.assignee_id,
            original_assignee_id=task.assignee_id,
            hours_elapsed=elapsed,
        )

    return SlaDecision(
        task_id=task.task_id,
        task_kind=kind,
        action=SlaAction.NONE,
        reason=SlaReason.BELOW_REMINDER,
        hours_elapsed=elapsed,
    )


def evaluate_tasks(
    tasks: Iterable[TaskSnapshot],
    thresholds_by_kind: Mapping[str, SlaThresholds],
    now: datetime.datetime,
) -> list[SlaDecision]:
    """Evaluate a batch of tasks against a configuration map.

    Returns a decision for every task given, actionable or not, so the caller
    can log suppressed evaluations as well as issued ones.
    """
    decisions: list[SlaDecision] = []
    for task in tasks:
        key = TaskKind(task.task_kind).value
        decisions.append(evaluate_task(task, thresholds_by_kind.get(key), now))
    return decisions


def actionable(decisions: Iterable[SlaDecision]) -> list[SlaDecision]:
    """Filter helper: only the decisions that require an outbound action."""
    return [d for d in decisions if d.is_actionable]


DEFAULT_THRESHOLD_HOURS: dict[TaskKind, tuple[float, float]] = {
    TaskKind.SUBSTITUTE_RESPONSE: (24.0, 48.0),
    TaskKind.UNIT_HEAD_REVIEW: (48.0, 96.0),
    TaskKind.ESTABLISHMENT_ROUTING: (48.0, 96.0),
    TaskKind.SANCTION_DECISION: (72.0, 144.0),
    TaskKind.DIRECTOR_SELF_SANCTION: (72.0, 144.0),
    TaskKind.CANCELLATION_UNIT_HEAD: (24.0, 48.0),
    TaskKind.CANCELLATION_SANCTION: (48.0, 96.0),
    TaskKind.EXTENSION_UNIT_HEAD: (24.0, 48.0),
    TaskKind.EXTENSION_SANCTION: (48.0, 96.0),
    TaskKind.RESUMPTION_REVIEW: (72.0, 168.0),
}
"""Seed values only. BR-EL-038 requires these to be administrator-configurable,
so nothing in the evaluation path reads this map -- it exists to populate the
SLA configuration table on first run so the feature is not dark on install."""
