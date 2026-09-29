"""SF-EL-002. Reminding the person a request is waiting on, then escalating."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.leave.domain.state_machine import State, is_terminal
from modules.leave.models import LeaveRequest, SlaClock, SlaRule, SubstituteNomination

log = logging.getLogger("fusion.leave.sla")


@dataclass(frozen=True)
class SlaReport:
    reminded: int = 0
    escalated: int = 0
    still_open: int = 0


def _responsible(request: LeaveRequest, state: State) -> int | None:
    """Who the clock is against, where the system can name one person."""
    if state in (State.AWAITING_SUBSTITUTE, State.EXTENSION_AWAITING_SUBSTITUTE):
        pending = SubstituteNomination.objects.filter(
            request=request, response=SubstituteNomination.Response.PENDING
        ).order_by("-id").first()
        return pending.substitute_user_id if pending else None
    if state in (
        State.APPLICANT_ACTION_REQUIRED,
        State.EXTENSION_APPLICANT_ACTION_REQUIRED,
        State.AWAITING_RESUMPTION,
    ):
        return request.user_id
    return None


def on_state_change(
    request: LeaveRequest, target: State, source: State | None = None
) -> SlaClock | None:
    """Stop whatever was running and start the next clock, if the state has one."""
    if source is not None and source is target:
        return SlaClock.objects.filter(
            request=request, state=target.value, stopped_at__isnull=True
        ).first()
    stop(request)
    if is_terminal(target) or request.policy_id is None:
        return None
    rule = SlaRule.objects.filter(
        policy_id=request.policy_id, state=target.value
    ).first()
    if rule is None:
        return None                     # not an SLA-controlled state

    started = timezone.now()
    return SlaClock.objects.create(
        request=request,
        state=target.value,
        assigned_user_id=_responsible(request, target),
        started_at=started,
        remind_at=started + timedelta(hours=rule.remind_after_hours),
        escalate_at=started + timedelta(hours=rule.escalate_after_hours),
    )


def stop(request: LeaveRequest) -> int:
    """Close every clock still running on this request."""
    return SlaClock.objects.filter(request=request, stopped_at__isnull=True).update(
        stopped_at=timezone.now()
    )


@transaction.atomic
def process(now=None) -> SlaReport:
    """One pass over the open clocks. Safe to run as often as you like."""
    now = now or timezone.now()
    open_clocks = SlaClock.objects.select_for_update().filter(stopped_at__isnull=True)

    due = list(
        open_clocks.filter(remind_at__lte=now, reminded_at__isnull=True)
        .select_related("request")
    )
    for clock in due:
        log.info(
            "leave.sla.reminder request=%s state=%s assigned=%s waiting_since=%s",
            clock.request_id, clock.state, clock.assigned_user_id, clock.started_at,
        )
    if due:
        SlaClock.objects.filter(pk__in=[c.pk for c in due]).update(reminded_at=now)

    overdue = list(
        open_clocks.filter(escalate_at__lte=now, escalated_at__isnull=True)
        .select_related("request")
    )
    for clock in overdue:
        log.warning(
            "leave.sla.escalation request=%s state=%s assigned=%s waiting_since=%s",
            clock.request_id, clock.state, clock.assigned_user_id, clock.started_at,
        )
    if overdue:
        SlaClock.objects.filter(pk__in=[c.pk for c in overdue]).update(escalated_at=now)

    return SlaReport(
        reminded=len(due),
        escalated=len(overdue),
        still_open=SlaClock.objects.filter(stopped_at__isnull=True).count(),
    )
