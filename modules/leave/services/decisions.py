"""Every decision on a file (EL-UC-002…006, 010, 011).

Identity, state and balance effects live together on purpose: a sanction
that forgets to move the balance is a silent lie, so `_apply_effect` is
called from exactly the two paths that approve something.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain import states as st
from modules.leave.domain.categories import label_for
from modules.leave.models import (
    LeaveAccountTransaction,
    LeaveRequest,
    LeaveRequestEvent,
    LeaveResumption,
)
from modules.leave.services import (
    authz,
    balances,
    hierarchy,
    notifications,
    workflow,
)
from modules.leave.services.errors import validated

APPROVE = "approve"
REJECT = "reject"
RECOMMEND = "recommended"
NOT_RECOMMEND = "not_recommended"
#: Unit-Head-final categories (BR-EL-016): CL and RH end here.
UNIT_HEAD_FINAL = ("cl", "rh")


def _department(request: LeaveRequest) -> str:
    return hierarchy.department_of(request.user_id)


def _decision_fields(request, *, outcome: str, actor, note: str,
                     reference: str = "") -> None:
    now = timezone.now()
    request.decision = outcome
    request.decided_at = now
    request.decided_by_user_id = getattr(actor, "user_id", None)
    request.decision_note = note
    if reference:
        request.sanction_reference = reference
    request.save(update_fields=["decision", "decided_at", "decided_by_user_id",
                                "decision_note", "updated_at"]
                 + (["sanction_reference"] if reference else []))


def _apply_effect(request: LeaveRequest, actor) -> None:
    """The balance follows the decision (BR-EL-004, 007, 008, 014):

    * new/extension  → deduct what was charged
    * cancellation   → restore the original deduction and retire the base
    """
    if request.kind == LeaveRequest.CANCELLATION:
        base = request.base_request
        if base is None:
            raise ConflictError("This cancellation points at nothing.",
                                code="orphan_cancellation")
        balances.restore(base.user_id, base.category, base.year,
                         base.chargeable_days, request=base,
                         note=f"cancellation #{request.id} of #{base.id}",
                         actor_user_id=getattr(actor, "user_id", None))
        workflow.record_event(
            request, LeaveRequestEvent.BALANCE_EFFECT, actor=actor,
            note=f"+{base.chargeable_days} {base.category.upper()} restored "
                 f"to {base.user_id}")
        frm = base.status
        base.status = st.CANCELLED
        base.save(update_fields=["status", "updated_at"])
        workflow.record_event(base, LeaveRequestEvent.STATUS_CHANGE, frm=frm,
                              to=st.CANCELLED, actor=actor,
                              note=f"cancelled by #{request.id}")
        workflow.close_task(base)
        notifications.notify(
            base.user_id, "leave_cancelled",
            f"Your {label_for(base.category)} leave was cancelled; "
            f"{base.chargeable_days} day(s) returned to your balance.",
            base)
        return

    if request.kind == LeaveRequest.EXTENSION:
        base = request.base_request
        if base is None:
            raise ConflictError("This extension points at nothing.",
                                code="orphan_extension")
        balances.post(base.user_id, base.category, base.year,
                      LeaveAccountTransaction.EXTENSION_DEDUCTION,
                      request.chargeable_days, request=request,
                      note=f"extension #{request.id}",
                      actor_user_id=getattr(actor, "user_id", None))
        workflow.record_event(
            request, LeaveRequestEvent.BALANCE_EFFECT, actor=actor,
            note=f"-{request.chargeable_days} {request.category.upper()} "
                 f"extension")
        base.end_date = request.end_date
        base.chargeable_days = base.chargeable_days + request.chargeable_days
        base.save(update_fields=["end_date", "chargeable_days", "updated_at"])
        workflow.record_event(base, LeaveRequestEvent.NOTE, actor=actor,
                              note=f"extended through "
                                   f"{request.end_date.isoformat()}")
        return

    balances.deduct(request.user_id, request.category, request.year,
                    request.chargeable_days, request=request,
                    note=f"approved #{request.id}",
                    actor_user_id=getattr(actor, "user_id", None))
    workflow.record_event(
        request, LeaveRequestEvent.BALANCE_EFFECT, actor=actor,
        note=f"-{request.chargeable_days} {request.category.upper()}")


def _notify_decision(request: LeaveRequest, actor, *, approved: bool,
                     by: str) -> None:
    verb = "approved" if approved else "rejected"
    notifications.notify(
        request.user_id, "decision",
        f"Your {label_for(request.category)} leave "
        f"({request.start_date.isoformat()}…{request.end_date.isoformat()}) "
        f"was {verb} by {by}.", request)


@transaction.atomic
def substitute_respond(actor, request: LeaveRequest, *,
                       response: str) -> LeaveRequest:
    """BR-EL-015: the consent gate — accept forwards, decline parks the file
    with the applicant (EL-UC-002, EL-UC-019)."""
    authz.require(actor, "leave.substitute.respond")
    authz.require_user(actor, request.substitute_user_id)
    if request.status != st.AWAITING_SUBSTITUTE:
        raise ConflictError(
            "This request is not awaiting a substitute response.",
            code="not_awaiting_substitute")
    if response not in ("accept", "decline"):
        raise BadRequestError("Response must be 'accept' or 'decline'.",
                              code="invalid_response")

    if response == "accept":
        request.substitute_status = "accepted"
        request.save(update_fields=["substitute_status", "updated_at"])
        guards = ("substitute_accepted",)
        if request.is_director_self_sanction:
            to = st.AWAITING_DIRECTOR
            guards = (*guards, "applicant_is_director")
        elif request.unit_head_user_id == request.user_id:
            # Self-approval guard: the applicant is their own unit's head,
            # so the file continues at establishment, never at their desk.
            to = st.AWAITING_ESTABLISHMENT
            establishment = hierarchy.establishment_assignee(
                hierarchy.department_of(request.user_id))
            if establishment is None:
                from core.api.exceptions import ConflictError
                raise ConflictError(
                    "No establishment desk is configured to carry this file.",
                    code="no_establishment_step")
            request.establishment_user_id = establishment
            request.save(update_fields=["establishment_user_id",
                                        "updated_at"])
            guards = (*guards, "applicant_is_unit_head")
        else:
            to = st.AWAITING_UH_REVIEW
        workflow.move(request, to, actor=actor, actor_kind=st.SUBSTITUTE,
                      permission="leave.substitute.respond", guards=guards,
                      note="substitute accepted the charge")
        notifications.notify(
            request.user_id, "substitute_accepted",
            "Your substitute accepted the charge; your request continues in "
            "review.", request)
    else:
        request.substitute_status = "declined"
        request.save(update_fields=["substitute_status", "updated_at"])
        workflow.move(request, st.APPLICANT_ACTION, actor=actor,
                      actor_kind=st.SUBSTITUTE,
                      permission="leave.substitute.respond",
                      guards=("substitute_declined",),
                      note="substitute declined the charge")
        notifications.notify(
            request.user_id, "substitute_declined",
            "Your substitute declined; nominate another so your request can "
            "continue.", request)
    return request


@validated
@transaction.atomic
def unit_head_review(actor, request: LeaveRequest, *, outcome: str,
                     note: str = "", reference: str = "") -> LeaveRequest:
    """EL-UC-003 / BR-EL-016…017. CL and RH end here; higher categories are
    only ever *recommended* at this desk — a recommendation is not a no."""
    authz.require(actor, "leave.request.approve")
    authz.require_user(actor, request.unit_head_user_id)
    if request.status != st.AWAITING_UH_REVIEW:
        raise ConflictError("This request is not awaiting Unit Head review.",
                            code="not_awaiting_review")
    now = timezone.now()
    request.unit_head_at = now
    request.unit_head_note = note
    request.unit_head_outcome = outcome

    if request.category in UNIT_HEAD_FINAL:
        if outcome not in (APPROVE, REJECT):
            raise BadRequestError(
                "Casual and Restricted leave take approve or reject at this "
                "desk.", code="invalid_outcome")
        request.save(update_fields=["unit_head_outcome", "unit_head_at",
                                    "unit_head_note", "updated_at"])
        _decision_fields(request, outcome=outcome, actor=actor, note=note,
                         reference=reference)
        workflow.move(request, st.APPROVED if outcome == APPROVE
                      else st.REJECTED,
                      actor=actor, actor_kind=st.UNIT_HEAD,
                      permission="leave.request.approve",
                      guards=("unit_head_final", f"outcome_{outcome}"),
                      note=note)
        if outcome == APPROVE:
            _apply_effect(request, actor)
        _notify_decision(request, actor, approved=outcome == APPROVE,
                         by="your Unit Head")
        return request

    if outcome not in (RECOMMEND, NOT_RECOMMEND):
        raise BadRequestError(
            "This category takes 'recommended' or 'not_recommended' at the "
            "Unit Head desk.", code="invalid_outcome")
    request.save(update_fields=["unit_head_outcome", "unit_head_at",
                                "unit_head_note", "updated_at"])
    department = _department(request)
    establishment = hierarchy.establishment_assignee(department)
    if establishment:
        to, guards = st.AWAITING_ESTABLISHMENT, ("higher_sanction",
                                                 "establishment_configured")
        request.establishment_user_id = establishment
        request.save(update_fields=["establishment_user_id", "updated_at"])
    else:
        to, guards = st.AWAITING_FINAL, ("higher_sanction",
                                         "no_establishment_step")
        request.authority_user_id = hierarchy.require_authority(
            request.category, department)
        request.save(update_fields=["authority_user_id", "updated_at"])
    workflow.move(request, to, actor=actor, actor_kind=st.UNIT_HEAD,
                  permission="leave.request.approve", guards=guards,
                  note=f"Unit Head: {outcome}")
    return request


@transaction.atomic
def establishment_route(actor, request: LeaveRequest, *,
                        note: str = "") -> LeaveRequest:
    """EL-UC-004 / BR-EL-019: verify the record and forward it — no
    approve/reject at this desk."""
    authz.require(actor, "leave.request.route")
    authz.require_user(actor, request.establishment_user_id)
    if request.status != st.AWAITING_ESTABLISHMENT:
        raise ConflictError("This request is not awaiting establishment "
                            "routing.", code="not_awaiting_establishment")
    request.establishment_at = timezone.now()
    request.establishment_note = note
    request.authority_user_id = hierarchy.require_authority(
        request.category, _department(request))
    request.save(update_fields=["establishment_at", "establishment_note",
                                "authority_user_id", "updated_at"])
    workflow.move(request, st.AWAITING_FINAL, actor=actor,
                  actor_kind=st.ESTABLISHMENT,
                  permission="leave.request.route", guards=(), note=note)
    return request


@validated
@transaction.atomic
def sanction(actor, request: LeaveRequest, *, outcome: str, note: str = "",
             reference: str = "") -> LeaveRequest:
    """EL-UC-005 / BR-EL-020: the final word, including the Director
    sanctioning their own file (BR-EL-020)."""
    authz.require(actor, "leave.request.sanction")
    if outcome not in (APPROVE, REJECT):
        raise BadRequestError("A sanction is an approve or a reject.",
                              code="invalid_outcome")

    if request.status == st.AWAITING_DIRECTOR:
        authz.require_applicant(actor, request)
        guards = ("applicant_is_director", f"outcome_{outcome}")
        by = "self-sanction (Director)"
    elif request.status == st.AWAITING_FINAL:
        authz.require_user(actor, request.authority_user_id)
        guards = (f"outcome_{outcome}",)
        by = "the sanctioning authority"
    else:
        raise ConflictError(
            "This request is not awaiting a final sanction.",
            code="not_awaiting_sanction")

    _decision_fields(request, outcome=outcome, actor=actor, note=note,
                     reference=reference)
    workflow.move(request, st.APPROVED if outcome == APPROVE
                  else st.REJECTED,
                  actor=actor, actor_kind=st.AUTHORITY,
                  permission="leave.request.sanction", guards=guards,
                  note=note)
    if outcome == APPROVE:
        _apply_effect(request, actor)
    _notify_decision(request, actor, approved=outcome == APPROVE, by=by)
    return request


@transaction.atomic
def review_resumption(actor, resumption: LeaveResumption, *,
                      note: str = "") -> LeaveResumption:
    """EL-UC-011 / BR-EL-026: the balance follows the actual period — a
    refund when they returned early, extra consumption when they did not."""
    authz.require(actor, "leave.request.sanction")
    request = resumption.request
    if resumption.status != LeaveResumption.PENDING:
        raise ConflictError("This resumption has already been reviewed.",
                            code="already_reviewed")
    reviewer = request.authority_user_id or request.unit_head_user_id
    if reviewer is None:
        raise ConflictError("No reviewer is assigned to this resumption.",
                            code="no_reviewer")
    authz.require_user(actor, reviewer)

    approved, actual = resumption.approved_end_date, resumption.actual_date
    if actual == approved:
        resumption.status = LeaveResumption.NO_ADJUSTMENT
        resumption.adjustment_days = 0
    elif actual < approved:
        days = (approved - actual).days
        resumption.status = LeaveResumption.EARLY
        resumption.adjustment_days = -days
        balances.refund(request.user_id, request.category, request.year, days,
                        request=request,
                        note=f"resumption #{resumption.id}: {days}d early",
                        actor_user_id=getattr(actor, "user_id", None))
    else:
        days = (actual - approved).days
        resumption.status = LeaveResumption.LATE
        resumption.adjustment_days = days
        # An approved leave kept on with permission consumes balance; it may
        # legitimately run the balance into negatives rather than refuse the
        # record of what was actually taken.
        balances.post(request.user_id, request.category, request.year,
                      LeaveAccountTransaction.EXTENSION_DEDUCTION, days,
                      request=request,
                      note=f"resumption #{resumption.id}: {days}d late",
                      actor_user_id=getattr(actor, "user_id", None))

    now = timezone.now()
    resumption.reviewed_by_user_id = getattr(actor, "user_id", None)
    resumption.reviewed_at = now
    resumption.review_note = note
    resumption.save(update_fields=["status", "adjustment_days",
                                   "reviewed_by_user_id", "reviewed_at",
                                   "review_note", "updated_at"])
    request.actual_end_date = actual
    request.save(update_fields=["actual_end_date", "updated_at"])
    workflow.record_event(
        request, LeaveRequestEvent.DECISION, actor=actor,
        note=f"resumption {resumption.status}: approved end {approved}, "
             f"actual {actual}, adjustment {resumption.adjustment_days}")
    workflow.record_event(
        request, LeaveRequestEvent.BALANCE_EFFECT, actor=actor,
        note=f"{resumption.adjustment_days:+} {request.category.upper()} "
             f"from resumption")
    workflow.close_task(request)
    notifications.notify(
        request.user_id, "resumption_reviewed",
        f"Your resumption was reviewed ({resumption.get_status_display()}); "
        f"balance adjusted by {resumption.adjustment_days:+} day(s).",
        request)
    return resumption
