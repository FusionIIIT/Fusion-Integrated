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
from modules.leave.domain.entitlement import has_sufficient_balance
from modules.leave.domain.state_machine import Actor, Event, State
from modules.leave.models import (
    EntryReason,
    LeaveRequest,
    LedgerEntry,
    SubstituteNomination,
)
from modules.leave.selectors import balances
from modules.leave.services.workflow import Movement, apply_event


def _refuse_wrong_authority(
    request: LeaveRequest,
    actor_user_id: int,
    actor_designations: frozenset[str] | set[str] | tuple[str, ...],
) -> None:
    """BR-EL-019, BR-EL-020. The named authority decides, not any authority.

    The permission says somebody may sanction leave; the authority rule says
    whose leave. Checking only the permission let any sanctioner act on any
    request at the final stage, so a Dean could sanction leave the rule routed
    to the Registrar and the trail would show it as correctly authorised.
    """
    if request.self_sanction:
        # BR-EL-020. The route exists so that this person's own leave has
        # somewhere to go; anybody else reaching it is the failure.
        if actor_user_id != request.user_id:
            raise ConflictError(
                "This request is on the self-sanction route and is decided by the "
                "applicant alone.",
                code="not_the_self_sanctioner",
            )
        return

    required = request.sanctioning_designation
    if not required:
        return                          # the configuration names nobody in particular
    if required not in set(actor_designations):
        raise ConflictError(
            f"This request is sanctioned by the {required}, which you do not hold.",
            code="not_the_sanctioning_authority",
        )


def _refuse_if_unaffordable(request: LeaveRequest) -> None:
    category = Category(request.category)
    # Lock the person's ledger for this year so two approvals cannot both read
    # the balance before either has written to it.
    LedgerEntry.objects.select_for_update().filter(
        user_id=request.user_id, year=request.starts_on.year, category=category.value
    ).exists()
    held = balances.balance_for(request.user_id, request.starts_on.year, category)
    if not has_sufficient_balance(held, request.requested_days):
        raise ConflictError(
            f"{request.requested_days} day(s) needed but {held.available} left in "
            f"{category.value}. Another request has been approved since this one "
            "was made.",
            code="insufficient_balance",
        )


def _route_for(request: LeaveRequest) -> authority.Route:
    """The route the request entered, read back rather than recomputed.

    Recomputing it here used an empty designation and faculty=False regardless
    of the applicant, so a later step could resolve a different rule from the
    one the request was admitted under.
    """
    return authority.Route(
        first_state=State(request.state),
        establishment_step=request.establishment_step,
        sanctioning_designation=request.sanctioning_designation,
        self_sanction=request.self_sanction,
        unit_head_is_final=request.unit_head_is_final,
    )


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
    """EL-UC-003, BR-EL-017. Final for CL and RH; a recommendation otherwise."""
    route = _route_for(request)
    request.unit_head_recommended = approve
    request.save(update_fields=["unit_head_recommended", "updated_at"])

    if not approve:
        if route.unit_head_is_final:
            return apply_event(
                request,
                Event.UNIT_HEAD_REJECT,
                Actor.UNIT_HEAD,
                actor_user_id=actor_user_id,
                remark=remark,
            )
        # BR-EL-017. For SCL, EL, COL and VL the unit head records Recommended
        # or Not Recommended and routes onward; the final refusal is the
        # competent authority's to make. Rejecting here ended the request at a
        # step that has no authority to end it.
        return apply_event(
            request,
            Event.UNIT_HEAD_RECOMMEND,
            Actor.UNIT_HEAD,
            actor_user_id=actor_user_id,
            target=authority.after_unit_head(route),
            remark=f"Not recommended. {remark}".strip(),
        )

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
    *,
    request: LeaveRequest,
    actor_user_id: int,
    approve: bool,
    actor_designations: frozenset[str] | set[str] | tuple[str, ...] = (),
    remark: str = "",
) -> LeaveRequest:
    """EL-UC-005. The last decision, and the only one that moves a balance."""
    _refuse_wrong_authority(request, actor_user_id, actor_designations)
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


@transaction.atomic
def _approve(
    request: LeaveRequest, actor: Actor, actor_user_id: int, event: Event, remark: str
) -> LeaveRequest:
    """Deduct the days and record the approval in one transaction.

    The balance is checked again here, not only at submission. Nothing is held
    while a request is pending, so two requests can each be affordable when
    they are made and unaffordable together -- approve both and the balance
    goes negative with no rule having visibly been broken. The check belongs
    where the days actually move.
    """
    _refuse_if_unaffordable(request)
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
