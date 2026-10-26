"""Notification composition for ELM.

Pure Python: no Django, no DRF, no Celery (ADR-0003 domain purity).

Covers the message half of:
  * BR-EL-035 -- notify the assignee when an actionable task is assigned
    (CFR-EL-030 / AFR-EL-030.1)
  * BR-EL-032 -- the reminder issued to the responsible user
  * BR-EL-033 -- the escalation issued to the configured authority

Delivery is deliberately not modelled here. This module decides *what* is
said; `services/notifications.py` decides where it is written. That split is
what lets the wording be unit-tested without a database.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from modules.elm.domain.sla import SlaAction, SlaDecision, TaskKind


class NotificationKind(str, Enum):
    TASK_ASSIGNED = "TASK_ASSIGNED"
    SLA_REMINDER = "SLA_REMINDER"
    SLA_ESCALATION = "SLA_ESCALATION"
    DECISION_RECORDED = "DECISION_RECORDED"


#: Human-readable label per actionable task kind. Used in every message, so a
#: recipient sees what is being asked of them rather than an enum name.
TASK_LABELS: dict[TaskKind, str] = {
    TaskKind.SUBSTITUTE_RESPONSE: "substitute responsibility request",
    TaskKind.UNIT_HEAD_REVIEW: "leave request awaiting your Unit Head review",
    TaskKind.ESTABLISHMENT_ROUTING: "leave request awaiting establishment routing",
    TaskKind.SANCTION_DECISION: "leave request awaiting your sanction decision",
    TaskKind.DIRECTOR_SELF_SANCTION: "own leave request awaiting self-sanction",
    TaskKind.CANCELLATION_UNIT_HEAD: "leave cancellation request awaiting your review",
    TaskKind.CANCELLATION_SANCTION: "leave cancellation request awaiting sanction",
    TaskKind.EXTENSION_UNIT_HEAD: "leave extension request awaiting your review",
    TaskKind.EXTENSION_SANCTION: "leave extension request awaiting sanction",
    TaskKind.RESUMPTION_REVIEW: "duty resumption report awaiting your review",
}

#: Where a recipient should go to act on each kind. Kept beside the labels so a
#: new task kind cannot ship with a message but no way to act on it.
TASK_LINKS: dict[TaskKind, str] = {
    TaskKind.SUBSTITUTE_RESPONSE: "/leave/substitute",
    TaskKind.UNIT_HEAD_REVIEW: "/leave/approvals",
    TaskKind.ESTABLISHMENT_ROUTING: "/leave/approvals",
    TaskKind.SANCTION_DECISION: "/leave/approvals",
    TaskKind.DIRECTOR_SELF_SANCTION: "/leave/mine",
    TaskKind.CANCELLATION_UNIT_HEAD: "/leave/approvals",
    TaskKind.CANCELLATION_SANCTION: "/leave/approvals",
    TaskKind.EXTENSION_UNIT_HEAD: "/leave/approvals",
    TaskKind.EXTENSION_SANCTION: "/leave/approvals",
    TaskKind.RESUMPTION_REVIEW: "/leave/approvals",
}


@dataclass(frozen=True)
class NotificationMessage:
    """A composed, ready-to-persist notification."""

    kind: NotificationKind
    recipient_id: int
    subject: str
    body: str
    link: str
    task_kind: str = ""


def task_label(kind: str | TaskKind) -> str:
    """Label for a task kind, falling back to a readable form of the enum.

    A missing label must not raise: a notification with a clumsy noun is
    better than a workflow transition that blows up because someone added a
    task kind and forgot the dictionary entry.
    """
    try:
        return TASK_LABELS[TaskKind(kind)]
    except (KeyError, ValueError):
        return str(kind).replace("_", " ").lower()


def task_link(kind: str | TaskKind) -> str:
    try:
        return TASK_LINKS[TaskKind(kind)]
    except (KeyError, ValueError):
        return "/leave/mine"


def _ref(application_ref: str, task_kind: str | TaskKind) -> str:
    return application_ref or f"a {task_label(task_kind)}"


def compose_assignment(
    recipient_id: int,
    task_kind: str | TaskKind,
    application_ref: str = "",
    applicant_name: str = "",
) -> NotificationMessage:
    """BR-EL-035: an actionable task has just been assigned to `recipient_id`."""
    label = task_label(task_kind)
    who = f" from {applicant_name}" if applicant_name else ""
    return NotificationMessage(
        kind=NotificationKind.TASK_ASSIGNED,
        recipient_id=recipient_id,
        subject=f"Action required: {label}",
        body=(
            f"You have been assigned {_ref(application_ref, task_kind)}{who}. "
            "It is waiting on your response."
        ),
        link=task_link(task_kind),
        task_kind=str(TaskKind(task_kind).value) if _is_known(task_kind) else str(task_kind),
    )


def compose_reminder(
    recipient_id: int,
    task_kind: str | TaskKind,
    hours_elapsed: float,
    application_ref: str = "",
) -> NotificationMessage:
    """BR-EL-032: the task is still pending at its reminder threshold."""
    label = task_label(task_kind)
    return NotificationMessage(
        kind=NotificationKind.SLA_REMINDER,
        recipient_id=recipient_id,
        subject=f"Reminder: {label} is still pending",
        body=(
            f"{_ref(application_ref, task_kind).capitalize()} has been waiting on you for "
            f"{hours_elapsed:.0f} hours and is still pending. Please act on it."
        ),
        link=task_link(task_kind),
        task_kind=str(TaskKind(task_kind).value) if _is_known(task_kind) else str(task_kind),
    )


def compose_escalation(
    recipient_id: int,
    task_kind: str | TaskKind,
    hours_elapsed: float,
    application_ref: str = "",
    original_assignee_ref: str = "",
    changes_routing: bool = False,
) -> NotificationMessage:
    """BR-EL-033: the task is still pending past its escalation threshold.

    The wording distinguishes the two configured escalation shapes, because a
    recipient who has actually been given the task needs to know that, while a
    recipient merely being informed must not think they now own it.
    """
    label = task_label(task_kind)
    held_by = f" assigned to {original_assignee_ref}" if original_assignee_ref else ""
    if changes_routing:
        tail = "Responsibility for this task has been routed to you."
    else:
        tail = "This is an escalation notice; responsibility has not been reassigned."
    return NotificationMessage(
        kind=NotificationKind.SLA_ESCALATION,
        recipient_id=recipient_id,
        subject=f"Escalation: overdue {label}",
        body=(
            f"{_ref(application_ref, task_kind).capitalize()}{held_by} has been pending for "
            f"{hours_elapsed:.0f} hours, past its escalation threshold. {tail}"
        ),
        link=task_link(task_kind),
        task_kind=str(TaskKind(task_kind).value) if _is_known(task_kind) else str(task_kind),
    )


def compose_for_decision(
    decision: SlaDecision,
    recipient_id: int,
    application_ref: str = "",
    original_assignee_ref: str = "",
) -> NotificationMessage | None:
    """Turn an SlaDecision into a message, or None when nothing is to be sent.

    Returning None for a non-actionable decision is what makes the pending-only
    guard (BR-EL-032/033) hold end to end: a suppressed evaluation cannot
    accidentally produce a message downstream.
    """
    if decision.action is SlaAction.REMIND:
        return compose_reminder(
            recipient_id=recipient_id,
            task_kind=decision.task_kind,
            hours_elapsed=decision.hours_elapsed,
            application_ref=application_ref,
        )
    if decision.action is SlaAction.ESCALATE:
        return compose_escalation(
            recipient_id=recipient_id,
            task_kind=decision.task_kind,
            hours_elapsed=decision.hours_elapsed,
            application_ref=application_ref,
            original_assignee_ref=original_assignee_ref,
            changes_routing=decision.changes_routing,
        )
    return None


def _is_known(kind: str | TaskKind) -> bool:
    try:
        TaskKind(kind)
    except ValueError:
        return False
    return True
