"""Review, sanction, withdrawal and the substitute's answer.

The balance moves at one point only: final approval. Nothing is deducted while
a request is pending, so a withdrawal or a rejection needs no reversal and
cannot leave a balance short.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain import authority
from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import Actor, Event, State
from modules.leave.models import AuthorityRule, EntryReason, LeaveRequest, SubstituteNomination
from modules.leave.services.workflow import Movement, apply_event


def _route_for(request: LeaveRequest) -> authority.Route:
    category = Category(request.category)
    rows = AuthorityRule.objects.filter(
        policy_id=request.policy_id, category=request.category
    )
    candidates = [
        authority.AuthorityCandidate(
            category=Category(r.category),
            unit=r.unit,
            designation=r.designation,
            applies_to_faculty=r.applies_to_faculty,
            establishment_step=r.establishment_step,
            sanctioning_designation=r.sanctioning_designation,
            self_sanction=r.self_sanction,
            specificity=r.specificity,
        )
        for r in rows
    ]
    rule = authority.select_rule(candidates, category, request.unit, "", False)
    return authority.route_for(rule, category, substitute_required=False)


@transaction.atomic
def substitute_responds(
    *, request: LeaveRequest, substitute_user_id: int, accepted: bool, remark: str = ""
) -> LeaveRequest:
    """EL-UC-002, BR-EL-015. Routing waits on this answer."""
    nomination = (
        SubstituteNomination.objects.select_for_update()
        .filter(
            request=request,
            substitute_user_id=substitute_user_id,
            response=SubstituteNomination.Response.PENDING,
        )
        .first()
    )
    if nomination is None:
        raise NotFoundError("No pending nomination for you on this request.")

    nomination.response = (
        SubstituteNomination.Response.ACCEPTED
        if accepted
        else SubstituteNomination.Response.DECLINED
    )
    nomination.responded_at = timezone.now()
    nomination.remark = remark
    nomination.save(update_fields=["response", "responded_at", "remark", "updated_at"])

    event = Event.SUBSTITUTE_ACCEPT if accepted else Event.SUBSTITUTE_DECLINE
    return apply_event(
        request, event, Actor.SUBSTITUTE, actor_user_id=substitute_user_id, remark=remark
    )


def unit_head_decides(
    *, request: LeaveRequest, actor_user_id: int, approve: bool, remark: str = ""
) -> LeaveRequest:
    """EL-UC-003. Final for CL and RH; a recommendation for everything else."""
    if not approve:
        return apply_event(
            request,
            Event.UNIT_HEAD_REJECT,
            Actor.UNIT_HEAD,
            actor_user_id=actor_user_id,
            remark=remark,
        )

    route = _route_for(request)
    if route.unit_head_is_final:
        return _approve(request, Actor.UNIT_HEAD, actor_user_id, Event.UNIT_HEAD_APPROVE, remark)
    return apply_event(
        request,
        Event.UNIT_HEAD_RECOMMEND,
        Actor.UNIT_HEAD,
        actor_user_id=actor_user_id,
        target=authority.after_unit_head(route),
        remark=remark,
    )


def establishment_routes(
    *, request: LeaveRequest, actor_user_id: int, remark: str = ""
) -> LeaveRequest:
    """EL-UC-004. The establishment resolves the competent authority."""
    return apply_event(
        request,
        Event.ROUTE,
        Actor.ESTABLISHMENT,
        actor_user_id=actor_user_id,
        remark=remark,
    )


def sanction(
    *, request: LeaveRequest, actor_user_id: int, approve: bool, remark: str = ""
) -> LeaveRequest:
    """EL-UC-005. The last decision, and the only one that moves a balance."""
    if not approve:
        return apply_event(
            request,
            Event.REFUSE,
            Actor.SANCTIONING_AUTHORITY,
            actor_user_id=actor_user_id,
            remark=remark,
        )
    return _approve(
        request, Actor.SANCTIONING_AUTHORITY, actor_user_id, Event.SANCTION, remark
    )


def _approve(
    request: LeaveRequest, actor: Actor, actor_user_id: int, event: Event, remark: str
) -> LeaveRequest:
    """Deduct the days and record the approval in one transaction."""
    return apply_event(
        request,
        event,
        actor,
        actor_user_id=actor_user_id,
        remark=remark,
        movements=[
            Movement(
                category=request.category,
                days=-request.requested_days,
                reason=EntryReason.CONSUMED,
                note=f"approved {request.starts_on} to {request.ends_on}",
            )
        ],
    )


def withdraw(*, request: LeaveRequest, actor_user_id: int, remark: str = "") -> LeaveRequest:
    """EL-UC-007, BR-EL-022. Immediate, and only while pending."""
    if request.user_id != actor_user_id:
        raise ConflictError("Only the applicant may withdraw a request.", code="not_applicant")
    return apply_event(
        request, Event.WITHDRAW, Actor.EMPLOYEE, actor_user_id=actor_user_id, remark=remark
    )


def renominate(
    *, request: LeaveRequest, actor_user_id: int, substitute_user_id: int
) -> LeaveRequest:
    """EL-UC-006. A fresh substitute after the first declined."""
    if substitute_user_id == request.user_id:
        raise ConflictError(
            "An employee cannot stand in for themselves.", code="substitute_is_applicant"
        )
    previous = request.nominations.order_by("-id").first()
    SubstituteNomination.objects.create(
        request=request,
        substitute_user_id=substitute_user_id,
        supersedes_id=previous.pk if previous else None,
    )
    target = (
        State.EXTENSION_AWAITING_SUBSTITUTE
        if request.state == State.EXTENSION_APPLICANT_ACTION_REQUIRED.value
        else State.AWAITING_SUBSTITUTE
    )
    return apply_event(
        request,
        Event.RENOMINATE,
        Actor.EMPLOYEE,
        actor_user_id=actor_user_id,
        target=target,
    )
