"""The processing lanes: the substitute's answer, the Unit Head's review, the
Establishment's routing, the final sanction, and the resumption review.

Each of these is one `move()` plus the effect the decision has. The effect is
the interesting half, and it is deliberately not in the state machine: a table
that knew about ledgers would stop being a table you can read.

    new leave approved          deduct the days (CFR-EL-016.3)
    new leave rejected          tell the employee; the account is untouched
    cancellation approved       mark the leave Cancelled, restore the days
    cancellation rejected       the original approved leave stands
    extension approved          post ONLY the increment; the leave keeps its base
    extension rejected          the original approved leave stands
    resumption reviewed         normal: nothing; early: credit back; late: debit
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, ValidationError
from modules.leave.domain import categories as cat
from modules.leave.domain.guards import Facts
from modules.leave.domain.state_machine import (
    KIND_CANCELLATION,
    KIND_EXTENSION,
    KIND_NEW,
)
from modules.leave.models import LeavePolicy, LeaveRequest, LeaveTask
from modules.leave.selectors import leave as leave_selectors
from modules.leave.services import accounts, notifications, workflow

log = logging.getLogger("fusion.leave.decisions")

P_RESPOND = "leave.substitute.respond"
P_REVIEW = "leave.request.review"
P_ROUTE = "leave.request.route"
P_APPROVE = "leave.request.approve"
P_RESUMPTION_REVIEW = "leave.resumption.review"

#: What each lane may record.
UNIT_HEAD_FINAL_DECISIONS = ("approve", "reject")
RECOMMENDATIONS = ("recommended", "not_recommended")
FINAL_DECISIONS = ("approve", "reject")
RESUMPTION_OUTCOMES = ("normal", "early", "late")


def _policy() -> LeavePolicy:
    policy = LeavePolicy.current()
    if policy is None:
        raise ValidationError("Leave has not been configured yet.",
                              code="policy_missing")
    return policy


def _in_my_lane(request: LeaveRequest, principal, *, stage: str) -> None:
    """Is this actually this person's work?

    The permission says a Unit Head may review; the task says WHICH Unit Head,
    and for which request. Role-addressed stages — Establishment, and the final
    sanctioning authority — have no single assignee, so there the permission is
    the whole answer. That is a documented widening rather than an oversight.
    """
    task = LeaveTask.objects.filter(request=request, status="pending",
                                    stage=stage).first()
    if task is None:
        raise ConflictError("This request is not waiting at that stage.",
                            code="not_at_stage")
    if task.assignee_user_id and task.assignee_user_id != principal.user_id:
        raise ConflictError("That request is assigned to someone else.",
                            code="not_your_task")


def _facts(request: LeaveRequest, **kw) -> Facts:
    base = {"kind": request.kind, "category_code": request.category,
            "employee_kind": cat.STAFF,
            "roles": tuple(request.applicant_roles or ()),
            "establishment_configured": request.establishment_first,
            "substitute_required": bool(request.substitute_user_id)}
    base.update(kw)
    return Facts(**base)


def _tell(request: LeaveRequest, subject: str, body: str = "") -> None:
    notifications.notify(
        topic="leave.decided", dedupe_key=f"leave.decided:{request.pk}",
        recipient_user_id=request.user_id, subject=subject, body=body,
        request=request)


def _apply_effects(request: LeaveRequest) -> None:
    """What the decision MEANS. A recommendation is not here on purpose:
    intermediate decisions are recorded and stay inspectable, and the baseline
    is explicit that they do not notify (CFR-EL-016.4)."""
    policy = _policy()

    if request.decision == "approve":
        if request.kind == KIND_NEW:
            accounts.post(user_id=request.user_id, year_label=policy.year_label,
                          category=request.category, days=-request.days,
                          kind="approval",
                          note=f"Approved {request.get_category_display()}",
                          request=request)
            _tell(request, "Your leave has been approved",
                  f"{request.get_category_display()} from {request.from_date} "
                  f"to {request.to_date}.")
            return

        if request.kind == KIND_CANCELLATION and request.parent_id:
            parent = request.parent
            parent.status = "cancelled"
            parent.save(update_fields=["status", "updated_at"])
            accounts.post(user_id=parent.user_id, year_label=policy.year_label,
                          category=parent.category, days=parent.days,
                          kind="cancellation_reversal",
                          note=f"Cancellation of leave from {parent.from_date}",
                          request=parent)
            _tell(request, "Your cancellation has been approved",
                  f"{parent.get_category_display()} from {parent.from_date} is "
                  f"cancelled and the days are back on your account.")
            return

        if request.kind == KIND_EXTENSION and request.parent_id:
            parent = request.parent
            parent.to_date = request.to_date
            parent.save(update_fields=["to_date", "updated_at"])
            accounts.post(user_id=request.user_id, year_label=policy.year_label,
                          category=request.category, days=-request.days,
                          kind="extension_post",
                          note=f"Extension to {request.to_date}", request=request)
            _tell(request, "Your extension has been approved",
                  f"Your leave now runs to {request.to_date}.")
        return

    if request.decision == "reject":
        if request.kind == KIND_CANCELLATION:
            _tell(request, "Your cancellation was not approved",
                  "The approved leave stands unchanged.")
        elif request.kind == KIND_EXTENSION:
            _tell(request, "Your extension was not approved",
                  "The original approved leave stands unchanged.")
        else:
            _tell(request, "Your leave has been rejected",
                  request.decision_remarks or "No reason was recorded.")


def respond_as_substitute(*, principal, request_id: int,
                           accept: bool) -> LeaveRequest:
    """EL-UC-002. Accept releases the consent gate; a decline does not."""
    policy = _policy()
    request = leave_selectors.substitute_request_by_id(principal, request_id)
    if request is None:
        raise NotFoundError("No such request.", code="not_found")

    decision = "accept" if accept else "decline"
    request = workflow.move(
        request=request, principal=principal, permission=P_RESPOND,
        facts=_facts(request, decision=decision),
        decision=decision, policy=policy)

    request.substitute_response = "accepted" if accept else "declined"
    request.substitute_responded_at = timezone.now()
    request.save(update_fields=["substitute_response",
                                "substitute_responded_at", "updated_at"])

    notifications.notify(
        topic="leave.substitute_responded",
        dedupe_key=f"leave.substitute.{decision}:{request.pk}",
        recipient_user_id=request.user_id,
        subject="Your substitute accepted" if accept
                else "Your substitute declined",
        body=("Your request is now with the next authority." if accept
              else "Nominate another eligible substitute, or withdraw the "
                   "request."),
        request=request)
    return request


def review_at_unit_head(*, principal, request_id: int, decision: str,
                        remarks: str = "") -> LeaveRequest:
    """EL-UC-003. Final for CL/RH; a recommendation for everything else — and
    Not Recommended is not a rejection (BR-EL-017)."""
    policy = _policy()
    if decision not in UNIT_HEAD_FINAL_DECISIONS + RECOMMENDATIONS:
        raise ValidationError(
            "A Unit Head may approve, reject, recommend or not recommend.",
            code="unknown_decision")
    request = leave_selectors.request_by_id(principal, request_id)
    if request is None:
        raise NotFoundError("No such request.", code="not_found")
    _in_my_lane(request, principal, stage="unit_head")

    moved = workflow.move(
        request=request, principal=principal, permission=P_REVIEW,
        facts=_facts(request, decision=_decision_word(decision)),
        decision=decision, remarks=remarks, policy=policy)
    _apply_effects(moved)
    return moved


def route_at_establishment(*, principal, request_id: int,
                           remarks: str = "") -> LeaveRequest:
    """EL-UC-004. Verification and forwarding — not a sanction."""
    policy = _policy()
    request = leave_selectors.request_by_id(principal, request_id)
    if request is None:
        raise NotFoundError("No such request.", code="not_found")
    _in_my_lane(request, principal, stage="establishment")

    return workflow.move(
        request=request, principal=principal, permission=P_ROUTE,
        facts=_facts(request, routing_context_valid=True),
        decision="routed", remarks=remarks, policy=policy)


def decide_final(*, principal, request_id: int, decision: str,
                 remarks: str = "") -> LeaveRequest:
    """EL-UC-005, including the Director self-sanction path (BR-EL-020)."""
    policy = _policy()
    if decision not in FINAL_DECISIONS:
        raise ValidationError("A final authority may approve or reject.",
                              code="unknown_decision")
    request = leave_selectors.request_by_id(principal, request_id)
    if request is None:
        raise NotFoundError("No such request.", code="not_found")
    _in_my_lane(request, principal,
                stage="self_sanction" if request.self_sanction else "final")

    moved = workflow.move(
        request=request, principal=principal, permission=P_APPROVE,
        facts=_facts(request, decision=decision),
        decision=decision, remarks=remarks, policy=policy)
    _apply_effects(moved)
    return moved


def review_resumption(*, principal, request_id: int, outcome: str,
                      remarks: str = "") -> LeaveRequest:
    """EL-UC-011. Normal, early or late — and only the latter two move a
    balance (BR-EL-028)."""
    policy = _policy()
    if outcome not in RESUMPTION_OUTCOMES:
        raise ValidationError(
            "A resumption is reviewed as normal, early or late.",
            code="unknown_outcome")
    request = leave_selectors.request_by_id(principal, request_id)
    if request is None:
        raise NotFoundError("No such request.", code="not_found")
    _in_my_lane(request, principal, stage="final")

    moved = workflow.move(
        request=request, principal=principal, permission=P_RESUMPTION_REVIEW,
        facts=_facts(request), decision="approve", remarks=remarks,
        policy=policy)

    parent = moved.parent
    if parent is not None:
        difference = (moved.from_date - parent.to_date).days
        if difference:
            parent.to_date = moved.from_date
            parent.save(update_fields=["to_date", "updated_at"])
            accounts.post(
                user_id=parent.user_id, year_label=policy.year_label,
                category=parent.category, days=Decimal(-difference),
                kind="resumption_adjustment",
                note=("Resumed earlier than the approved end date"
                      if difference < 0
                      else "Resumed later than the approved end date"),
                request=parent)
        notifications.notify(
            topic="leave.resumption_reviewed",
            dedupe_key=f"leave.resumption:{moved.pk}",
            recipient_user_id=moved.user_id,
            subject="Your resumption has been reviewed",
            body=remarks or f"Reviewed as a {outcome} resumption.",
            request=moved)
    return moved


def _decision_word(decision: str) -> str:
    """A recommendation and an approval are the same edge in the table; the
    guard only cares that the decision was positive."""
    if decision in ("approve", "recommended"):
        return "approve"
    if decision in ("reject", "not_recommended"):
        return "reject"
    return ""
