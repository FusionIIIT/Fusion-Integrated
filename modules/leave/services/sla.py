"""The SLA sweep (EL-UC-021, BR-EL-032, BR-EL-033, BR-EL-038).

Both thresholds are one-shot and both are guarded on the task still being
pending, so a request decided five minutes ago is never reminded or escalated.
A notification-only escalation logs and notifies; when the configured threshold
names a designation the sweep also re-routes the task, which is the
cross-cutting System transition XTP-EL-01 and is performed under the system
permission leave.request.assign.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.leave.domain import sla as sla_domain
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest, LeaveRequestTransition
from modules.leave.selectors import config as config_selector
from modules.leave.selectors import sla as sla_selector
from modules.leave.services import notifications

log = logging.getLogger("fusion.leave.sla")


@transaction.atomic
def sweep(*, now=None) -> dict:
    """One pass over every actionable task. Safe to re-run."""
    now = now or timezone.now()
    report = {"reminded": 0, "escalated": 0, "rerouted": 0, "skipped": 0}
    for task in sla_selector.waiting(now=now):
        thresholds = config_selector.thresholds(task.task_class)
        if thresholds is None:
            report["skipped"] += 1
            continue

        row = LeaveRequest.objects.select_for_update().filter(pk=task.request_id) \
            .first()
        if row is None:
            continue
        # Re-read the status under the lock: the task may have moved since the scan.
        if not sm.is_pending(row.status):
            report["skipped"] += 1
            continue

        due = sla_domain.events(
            thresholds=thresholds, age_hours=task.age_hours, pending=True,
            reminded=sla_selector.notified(_key("reminder", task)),
            escalated=sla_selector.notified(_key("escalation", task)),
        )
        for action in due:
            if action == sla_domain.REMIND:
                _remind(task=task, row=row)
                report["reminded"] += 1
            else:
                rerouted = _escalate(task=task, row=row, now=now)
                report["escalated"] += 1
                report["rerouted"] += 1 if rerouted else 0

    log.info("leave.sla.sweep %s", report)
    return report


def _key(prefix: str, task) -> str:
    return f"sla-{prefix}:{task.request_id}:{task.status}"


def _remind(*, task, row: LeaveRequest) -> None:
    """BR-EL-032: remind the responsible user, and log it."""
    notifications.enqueue(
        topic="sla.reminder",
        dedupe_key=_key("reminder", task),
        recipient_user_id=row.user_id,
        subject="Your leave request is still waiting",
        body=(f"The {task.task_class.replace('_', ' ')} step on your request from "
              f"{row.start_date} to {row.end_date} has been waiting "
              f"{int(task.age_hours)} hours."),
        payload={"request_id": row.pk, "task_class": task.task_class},
    )


def _escalate(*, task, row: LeaveRequest, now) -> bool:
    """BR-EL-033: notify the configured authority, and re-route where configured."""
    threshold = _threshold_row(task.task_class)
    rerouted = False
    if threshold is not None and threshold.escalation_designation:
        frm, row.current_step_designation = row.current_step_designation, \
            threshold.escalation_designation
        row.save(update_fields=["current_step_designation", "updated_at"])
        LeaveRequestTransition.objects.create(
            request=row, from_status=row.status, to_status=row.status,
            event="escalate", actor_kind="system",
            actor_designation=threshold.escalation_designation,
            reason=(f"SLA escalation after {int(task.age_hours)} hours; routing now "
                    f"points at {threshold.escalation_designation} "
                    f"(was {frm or 'unassigned'})"),
        )
        rerouted = True

    notifications.enqueue(
        topic="sla.escalation",
        dedupe_key=_key("escalation", task),
        recipient_user_id=row.user_id,
        subject="Your leave request has been escalated",
        body=(f"The {task.task_class.replace('_', ' ')} step on your request from "
              f"{row.start_date} to {row.end_date} passed its escalation threshold."),
        payload={"request_id": row.pk, "task_class": task.task_class,
                 "rerouted": rerouted},
    )
    return rerouted


def _threshold_row(task_class: str):
    from modules.leave.models import SlaThreshold

    return SlaThreshold.objects.filter(task_class=task_class).first()


def escalate_one(*, request_id: int, designation: str, actor_user_id: int | None = None
                 ) -> LeaveRequest:
    """A manual escalation, for an operator who cannot wait for the sweep."""
    row = LeaveRequest.objects.filter(pk=request_id).first()
    if row is None:
        raise NotFoundError("No such leave request.")
    if not sm.is_pending(row.status):
        raise NotFoundError("That request is not waiting on anybody.")
    row.current_step_designation = designation
    row.save(update_fields=["current_step_designation", "updated_at"])
    return row
