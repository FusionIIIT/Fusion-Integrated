"""SLA thresholds and the pending-only decision (BR-EL-032, BR-EL-033, BR-EL-038)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from modules.leave.domain import state_machine as sm

RESUMPTION_REVIEW = "resumption_review"
STEPS = (sm.SUBSTITUTE, sm.UNIT_HEAD, sm.ESTABLISHMENT, sm.AUTHORITY, sm.DIRECTOR,
         RESUMPTION_REVIEW)

NOTIFY, REASSIGN = "notify", "reassign"
ACTIONS = (NOTIFY, REASSIGN)

REMIND, ESCALATE, NOTHING = "remind", "escalate", "nothing"


@dataclass(frozen=True)
class Rule:
    step: str
    reminder_hours: int
    escalation_hours: int
    action: str = NOTIFY
    escalate_to: str = ""


def validate(rules: list[Rule], *, may_act: dict[str, frozenset[str]]) -> list[str]:
    """`may_act` maps each step to the designations that hold its permission."""
    problems: list[str] = []
    seen: set[str] = set()
    for r in rules:
        if r.step not in STEPS:
            problems.append(f"{r.step!r} is not a workflow step.")
            continue
        if r.step in seen:
            problems.append(f"{r.step}: configured twice.")
        seen.add(r.step)
        if r.reminder_hours <= 0:
            problems.append(f"{r.step}: the reminder threshold must be at least one hour.")
        if r.escalation_hours <= r.reminder_hours:
            problems.append(f"{r.step}: escalation must come after the reminder.")
        if r.action not in ACTIONS:
            problems.append(f"{r.step}: the escalation action must be notify or reassign.")
        if r.action == REASSIGN:
            if r.step in (sm.SUBSTITUTE, sm.DIRECTOR):
                problems.append(f"{r.step}: this task belongs to one person and cannot be "
                                f"reassigned; use notify.")
            elif r.escalate_to not in may_act.get(r.step, frozenset()):
                problems.append(f"{r.step}: {r.escalate_to or 'nobody'!r} cannot act on this "
                                f"step, so reassigning to them would strand the task.")
        if r.action == NOTIFY and r.step != sm.SUBSTITUTE and not r.escalate_to:
            problems.append(f"{r.step}: name the authority to notify on escalation.")
    return problems


def due(rule: Rule, *, opened_at: datetime, now: datetime, reminded: bool,
        escalated: bool) -> str:
    """What the threshold event asks for now; the caller checks the task is still pending."""
    if not escalated and now >= opened_at + timedelta(hours=rule.escalation_hours):
        return ESCALATE
    if not reminded and now >= opened_at + timedelta(hours=rule.reminder_hours):
        return REMIND
    return NOTHING
