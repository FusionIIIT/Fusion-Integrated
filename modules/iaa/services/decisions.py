"""Authority decisions and timeout escalation (UC-201/202/203/403, BR-001/005/401)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction

from core.api.exceptions import ConflictError, DomainError, PermissionDeniedError
from modules.iaa.domain import roles, routing
from modules.iaa.domain import state_machine as sm
from modules.iaa.models import ApprovalStep, FinancialRecord
from modules.iaa.selectors import policy as policy_selectors
from modules.iaa.selectors import scoping
from modules.iaa.services import notify, trail
from modules.iaa.services.authz import require, role_of
from modules.iaa.services.common import domain_errors, lock, now

log = logging.getLogger("fusion.iaa.decisions")

P_APPROVE = "iaa.request.approve"
APPROVE = "approve"
REJECT = "reject"
SOD_REMARK = "The creator cannot decide their own item (IAA-BR-001); sent to the next authority."


@dataclass(frozen=True)
class EscalationReport:
    escalated: int
    stuck: int

    def __str__(self) -> str:
        return f"escalated={self.escalated} stuck={self.stuck}"


def _pending_step(record: FinancialRecord) -> ApprovalStep | None:
    return (ApprovalStep.objects.select_for_update()
            .filter(record=record, status=ApprovalStep.PENDING).first())


def _move_to(record: FinancialRecord, step: ApprovalStep, target: routing.Target,
             step_status: str, *, via_escalation: bool, remarks: str = "") -> ApprovalStep:
    step.status, step.remarks = step_status, remarks
    step.save(update_fields=["status", "remarks", "updated_at"])
    record.current_level = target.level
    return ApprovalStep.objects.create(record=record, level=target.level,
                                       designation=target.designation, assigned_at=now(),
                                       via_escalation=via_escalation)


def _reroute_for_sod(actor, record_pk: int) -> str:
    with transaction.atomic():
        record = lock(scoping.records_for(actor), record_pk)
        step = _pending_step(record)
        target = routing.next_authority(record.route_levels, step.level,
                                        record.escalation_designation)
        if target is None:
            raise ConflictError(
                "You created this item, so you cannot decide it, and no other authority is "
                "configured on its route. Ask the IAA System Admin to extend the route.",
                code="segregation_of_duties")
        _move_to(record, step, target, ApprovalStep.REROUTED, via_escalation=False,
                 remarks=SOD_REMARK)
        record.save(update_fields=["current_level", "updated_at"])
        trail.log("record", record.pk, "reroute_sod", actor=actor, frm=record.status,
                  to=record.status, remarks=f"{SOD_REMARK} Now with {target.designation}.")
        notify.to_role(target.designation, "approval_needed",
                       f"#{record.pk} was routed to you for a decision.", "record", record.pk)
    return target.designation


def decide(actor, pk: int, *, decision: str, remarks: str) -> FinancialRecord:
    require(actor, P_APPROVE)
    if decision not in (APPROVE, REJECT):
        raise DomainError("Decision must be 'approve' or 'reject'.", code="invalid_decision")
    if not remarks.strip():
        raise DomainError("Add remarks explaining your decision (IAA-BR-005).",
                          code="remarks_required")
    with transaction.atomic():
        record = lock(scoping.records_for(actor), pk)
        step = _pending_step(record)
        if step is None or step.designation != role_of(actor):
            raise ConflictError("This item is not waiting on your role.", code="not_assigned")
        self_approval = record.user_id == actor.user_id
        if not self_approval:
            return _apply_decision(actor, record, step, decision, remarks)
    # The reroute commits on its own, then the refusal is reported (IAA-BR-001).
    where = _reroute_for_sod(actor, pk)
    raise PermissionDeniedError(
        f"You created this item, so you cannot decide it. It has been sent to {where}.",
        code="segregation_of_duties")


def _apply_decision(actor, record: FinancialRecord, step: ApprovalStep, decision: str,
                    remarks: str) -> FinancialRecord:
    if decision == REJECT:
        event = sm.REJECT
    elif routing.is_final_level(record.route_levels, step.level):
        event = sm.APPROVE_FINAL
    else:
        event = sm.APPROVE_LEVEL
    with domain_errors():
        t = sm.resolve_record(record.kind, record.status, event, roles.APPROVER_ACTOR)
    step.status = ApprovalStep.REJECTED if decision == REJECT else ApprovalStep.APPROVED
    step.decided_by, step.decided_role, step.decided_at = actor.user_id, role_of(actor), now()
    step.remarks = remarks
    step.save()
    if event == sm.APPROVE_LEVEL:
        nxt = step.level + 1
        designation = record.route_levels[nxt]
        record.current_level = nxt
        ApprovalStep.objects.create(record=record, level=nxt, designation=designation,
                                    assigned_at=now())
        notify.to_role(designation, "approval_needed",
                       f"#{record.pk} was approved at the previous level and needs your "
                       f"decision.", "record", record.pk)
    record.status = t.to
    record.save()
    trail.log("record", record.pk, event, actor=actor, frm=t.frm, to=t.to, remarks=remarks)
    notify.to_user(record.user_id, t.to,
                   f"#{record.pk} is now {t.to.replace('_', ' ')}: {remarks}", "record", record.pk)
    if t.to == sm.APPROVED:
        notify.to_role(roles.FINANCE, "ready_to_record",
                       f"#{record.pk} is approved and ready to be recorded.", "record", record.pk)
    return record


def escalate_overdue(at=None) -> EscalationReport:
    at = at or now()
    version = policy_selectors.current_version(at)
    if version is None:
        log.warning("iaa.escalation.skipped reason=policy_missing")
        return EscalationReport(0, 0)
    cutoff = at - timedelta(hours=version.approval_timeout_hours)
    due = list(ApprovalStep.objects.filter(status=ApprovalStep.PENDING, assigned_at__lt=cutoff,
                                           via_escalation=False)
               .values_list("record_id", flat=True))
    escalated = stuck = 0
    for record_id in due:
        outcome = _escalate_one(record_id, cutoff)
        escalated += outcome == "escalated"
        stuck += outcome == "stuck"
    return EscalationReport(escalated, stuck)


@transaction.atomic
def _escalate_one(record_id: int, cutoff) -> str:
    record = FinancialRecord.objects.select_for_update().get(pk=record_id)
    step = _pending_step(record)
    # Re-checked under the lock: a decision may have landed since the sweep began.
    if step is None or step.assigned_at >= cutoff or step.via_escalation:
        return "skipped"
    if sm.ESCALATE not in sm.record_events(record.kind, record.status, roles.SYSTEM):
        return "skipped"
    target = routing.next_authority(record.route_levels, step.level,
                                    record.escalation_designation)
    if target is None:
        log.warning("iaa.escalation.stuck record=%s level=%s", record.pk, step.level)
        return "stuck"
    t = sm.resolve_record(record.kind, record.status, sm.ESCALATE, roles.SYSTEM)
    _move_to(record, step, target, ApprovalStep.ESCALATED, via_escalation=True,
             remarks="Exceeded the configured approval time limit (IAA-BR-401).")
    record.status = t.to
    record.save()
    trail.log("record", record.pk, "escalate", frm=t.frm, to=t.to,
              remarks=f"Overdue at {step.designation}; escalated to {target.designation}.")
    notify.to_role(target.designation, "escalated",
                   f"#{record.pk} was escalated to you because it was overdue.",
                   "record", record.pk)
    notify.to_user(record.user_id, "escalated",
                   f"#{record.pk} was escalated to {target.designation}.", "record", record.pk)
    return "escalated"
