"""What happens to leave after it is approved.

Cancellation before it starts, extension while it runs, and resumption when it
ends. BR-EL-023 to BR-EL-028.

Approved leave is never edited in place. Cancelling returns the whole charge,
extending adds only the incremental days, and resuming early returns the
unused tail. Each is a separate ledger entry, so the history of a leave reads
as a sequence of events rather than a final figure.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain import authority
from modules.leave.domain.categories import RESUMABLE, Category
from modules.leave.domain.counting import (
    TailPolicy,
    actual_days_on_early_return,
    chargeable_days,
)
from modules.leave.domain.state_machine import Actor, Event, State
from modules.leave.models import (
    AuthorityRule,
    EntryReason,
    LeaveRequest,
    SubstituteNomination,
)
from modules.leave.selectors import balances
from modules.leave.selectors import policy as policy_selector
from modules.leave.services.workflow import Movement, apply_event

ZERO = Decimal("0")


def _route(request: LeaveRequest) -> authority.Route:
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


# -- Cancellation, before the leave starts -------------------------------------


def request_cancellation(
    *, request: LeaveRequest, actor_user_id: int, remark: str = ""
) -> LeaveRequest:
    """BR-EL-023. Only before the first day, and it follows the same hierarchy."""
    if request.user_id != actor_user_id:
        raise ConflictError(
            "Only the applicant may ask for a cancellation.", code="not_applicant"
        )
    return apply_event(
        request,
        Event.REQUEST_CANCELLATION,
        Actor.EMPLOYEE,
        actor_user_id=actor_user_id,
        remark=remark,
    )


def decide_cancellation_unit_head(
    *, request: LeaveRequest, actor_user_id: int, approve: bool, remark: str = ""
) -> LeaveRequest:
    if not approve:
        return apply_event(
            request,
            Event.CANCELLATION_REFUSE,
            Actor.UNIT_HEAD,
            actor_user_id=actor_user_id,
            remark=remark,
        )
    route = _route(request)
    target = authority.after_unit_head_for_cancellation(route)
    if target is State.CANCELLED:
        return _release(request, Actor.UNIT_HEAD, actor_user_id, remark)
    return apply_event(
        request,
        Event.CANCELLATION_ROUTE,
        Actor.UNIT_HEAD,
        actor_user_id=actor_user_id,
        target=target,
        remark=remark,
    )


def route_cancellation(
    *, request: LeaveRequest, actor_user_id: int, remark: str = ""
) -> LeaveRequest:
    return apply_event(
        request,
        Event.CANCELLATION_ROUTE,
        Actor.ESTABLISHMENT,
        actor_user_id=actor_user_id,
        remark=remark,
    )


def decide_cancellation_final(
    *, request: LeaveRequest, actor_user_id: int, approve: bool, remark: str = ""
) -> LeaveRequest:
    if not approve:
        return apply_event(
            request,
            Event.CANCELLATION_REFUSE,
            Actor.SANCTIONING_AUTHORITY,
            actor_user_id=actor_user_id,
            remark=remark,
        )
    return _release(request, Actor.SANCTIONING_AUTHORITY, actor_user_id, remark)


def _release(
    request: LeaveRequest, actor: Actor, actor_user_id: int, remark: str
) -> LeaveRequest:
    """Cancel and return the whole charge in one transaction."""
    return apply_event(
        request,
        Event.CANCELLATION_APPROVE,
        actor,
        actor_user_id=actor_user_id,
        remark=remark,
        movements=[
            Movement(
                category=request.category,
                days=request.requested_days,
                reason=EntryReason.CANCELLED,
                note="cancelled before it began",
            )
        ],
    )


# -- Extension, while the leave runs -------------------------------------------


@transaction.atomic
def request_extension(
    *,
    request: LeaveRequest,
    actor_user_id: int,
    new_end: date,
    substitute_user_id: int | None = None,
    remark: str = "",
) -> LeaveRequest:
    """BR-EL-025. Additional time on leave already running.

    Only earned, commuted and vacation leave may be extended, and only the
    incremental days are charged; the original approval is left as it stands.
    """
    if request.user_id != actor_user_id:
        raise ConflictError("Only the applicant may extend.", code="not_applicant")
    category = Category(request.category)
    if category not in RESUMABLE:
        raise BadRequestError(
            f"{category.value} cannot be extended.", code="not_extendable"
        )
    if new_end <= request.ends_on:
        raise BadRequestError(
            "An extension must end after the approved leave.", code="extension_not_longer"
        )

    calendar = policy_selector.effective_calendar(request.starts_on.year)
    closed = policy_selector.closed_days(calendar)
    # SRS-EL-075. Charge the difference, not the whole new span.
    whole = chargeable_days(category, request.starts_on, new_end, closed)
    extra = whole - request.requested_days
    if extra <= ZERO:
        raise BadRequestError("The extension adds no days.", code="no_additional_days")

    balance = balances.balance_for(actor_user_id, request.starts_on.year, category)
    if extra > balance.available:
        raise ConflictError(
            f"{extra} additional day(s) requested but {balance.available} available.",
            code="insufficient_balance",
        )

    if substitute_user_id is not None:
        SubstituteNomination.objects.create(
            request=request, substitute_user_id=substitute_user_id
        )
    target = (
        State.EXTENSION_AWAITING_SUBSTITUTE
        if substitute_user_id is not None
        else State.EXTENSION_AWAITING_UNIT_HEAD
    )
    request.actual_days = extra
    request.save(update_fields=["actual_days", "updated_at"])
    return apply_event(
        request,
        Event.REQUEST_EXTENSION,
        Actor.EMPLOYEE,
        actor_user_id=actor_user_id,
        target=target,
        remark=f"extend to {new_end}. {remark}".strip(),
    )


def recommend_extension(
    *, request: LeaveRequest, actor_user_id: int, remark: str = ""
) -> LeaveRequest:
    route = _route(request)
    target = (
        State.EXTENSION_AWAITING_ESTABLISHMENT
        if route.establishment_step
        else State.EXTENSION_AWAITING_FINAL
    )
    return apply_event(
        request,
        Event.UNIT_HEAD_RECOMMEND,
        Actor.UNIT_HEAD,
        actor_user_id=actor_user_id,
        target=target,
        remark=remark,
    )


def route_extension(
    *, request: LeaveRequest, actor_user_id: int, remark: str = ""
) -> LeaveRequest:
    return apply_event(
        request, Event.ROUTE, Actor.ESTABLISHMENT, actor_user_id=actor_user_id, remark=remark
    )


def decide_extension(
    *, request: LeaveRequest, actor_user_id: int, approve: bool, new_end: date | None = None,
    remark: str = "",
) -> LeaveRequest:
    """BW-EL-07 and BW-EL-08. Either way the leave carries on running."""
    if not approve:
        request.actual_days = None
        request.save(update_fields=["actual_days", "updated_at"])
        return apply_event(
            request,
            Event.EXTENSION_REFUSE,
            Actor.SANCTIONING_AUTHORITY,
            actor_user_id=actor_user_id,
            remark=remark,
        )

    extra = request.actual_days or ZERO
    updated = apply_event(
        request,
        Event.EXTENSION_GRANT,
        Actor.SANCTIONING_AUTHORITY,
        actor_user_id=actor_user_id,
        remark=remark,
        movements=[
            Movement(
                category=request.category,
                days=-extra,
                reason=EntryReason.CONSUMED,
                note="extension granted",
            )
        ],
    )
    if new_end is not None:
        updated.ends_on = new_end
    updated.requested_days = updated.requested_days + extra
    updated.actual_days = None
    updated.save(update_fields=["ends_on", "requested_days", "actual_days", "updated_at"])
    return updated


# -- Resumption ----------------------------------------------------------------


def begin(*, request: LeaveRequest) -> LeaveRequest:
    """The scheduler marks leave as running on its first day."""
    return apply_event(request, Event.START, Actor.SCHEDULER)


def await_resumption(*, request: LeaveRequest) -> LeaveRequest:
    """The scheduler marks the approved end reached. BW-EL-09."""
    return apply_event(request, Event.REACH_END_DATE, Actor.SCHEDULER)


def submit_resumption(
    *, request: LeaveRequest, actor_user_id: int, resumed_on: date, remark: str = ""
) -> LeaveRequest:
    """EL-UC-010. The employee reports being back."""
    if request.user_id != actor_user_id:
        raise ConflictError("Only the applicant may report resumption.", code="not_applicant")
    if resumed_on < request.starts_on:
        raise BadRequestError(
            "Resumption cannot precede the leave.", code="resumption_before_start"
        )
    request.resumed_on = resumed_on
    request.save(update_fields=["resumed_on", "updated_at"])
    return apply_event(
        request,
        Event.SUBMIT_RESUMPTION,
        Actor.EMPLOYEE,
        actor_user_id=actor_user_id,
        remark=remark,
    )


def query_resumption(
    *, request: LeaveRequest, actor_user_id: int, remark: str
) -> LeaveRequest:
    """BW-EL-09. Verification may ask for more before closing."""
    return apply_event(
        request,
        Event.RESUMPTION_QUERY,
        Actor.ESTABLISHMENT,
        actor_user_id=actor_user_id,
        remark=remark,
    )


def verify_resumption(
    *, request: LeaveRequest, actor_user_id: int, remark: str = ""
) -> LeaveRequest:
    """BR-EL-027, BR-EL-028. Close the leave and return anything unused.

    SRS-EL-086 is the reason the restoration happens here and not when the
    employee reports: nothing is returned until the return is verified.
    """
    category = Category(request.category)
    resumed_on = request.resumed_on
    movements: list[Movement] = []
    actual = request.requested_days

    if resumed_on is not None and category in RESUMABLE and resumed_on <= request.ends_on:
        policy = policy_selector.effective_policy(request.starts_on)
        calendar = policy_selector.effective_calendar(request.starts_on.year)
        tail = TailPolicy(policy.early_return_tail)
        actual = actual_days_on_early_return(
            category,
            request.starts_on,
            request.ends_on,
            resumed_on,
            policy_selector.closed_days(calendar),
            tail,
        )
        restored = request.requested_days - actual
        if restored > ZERO:
            movements.append(
                Movement(
                    category=request.category,
                    days=restored,
                    reason=EntryReason.RESTORED,
                    note=f"resumed {resumed_on}, {tail.value.lower().replace('_', ' ')}",
                )
            )

    updated = apply_event(
        request,
        Event.VERIFY_RESUMPTION,
        Actor.ESTABLISHMENT,
        actor_user_id=actor_user_id,
        remark=remark,
        movements=movements or None,
    )
    updated.actual_days = actual
    updated.save(update_fields=["actual_days", "updated_at"])
    return updated
