"""Every write that moves a leave request (CW-EL-01, CW-EL-02, CW-EL-03).

One transactional choke point per state change: the row is locked, the
transition table names the permission and the guards, the audit row and the
ledger effect all land in one transaction. Two paths into the same state is how
rules drift apart, so there is only the one.
"""
from __future__ import annotations

import logging
from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.domain.errors import RuleViolation
from modules.leave.models import (
    LeaveRequest,
    LeaveRequestTransition,
    SubstituteAssignment,
)
from modules.leave.selectors import config as config_selector
from modules.leave.services import accounts as account_service
from modules.leave.services import authz, facts, guards, notifications

log = logging.getLogger("fusion.leave.requests")

#: Which step each waiting state parks the request at, and under what name.
STEP_BY_STATUS = {
    sm.AWAITING_SUBSTITUTE: "substitute",
    sm.EXTENSION_AWAITING_SUBSTITUTE: "substitute",
    sm.APPLICANT_ACTION_REQUIRED: "applicant",
    sm.EXTENSION_APPLICANT_ACTION_REQUIRED: "applicant",
    sm.AWAITING_UNIT_HEAD: "unit_head",
    sm.CANCELLATION_AWAITING_UNIT_HEAD: "unit_head",
    sm.EXTENSION_AWAITING_UNIT_HEAD: "unit_head",
    sm.AWAITING_ESTABLISHMENT: "establishment",
    sm.CANCELLATION_AWAITING_ESTABLISHMENT: "establishment",
    sm.EXTENSION_AWAITING_ESTABLISHMENT: "establishment",
    sm.AWAITING_FINAL_SANCTION: "final_authority",
    sm.CANCELLATION_AWAITING_FINAL: "final_authority",
    sm.EXTENSION_AWAITING_FINAL: "final_authority",
    sm.AWAITING_DIRECTOR_SELF_SANCTION: "self_sanction",
    sm.RESUMPTION_REVIEW_PENDING: "final_authority",
}


def resolve_or_raise(frm: str, event: str, kind: str) -> sm.Transition:
    """`sm.resolve` with its refusals translated, so an illegal move is a 409."""
    try:
        return sm.resolve(frm, event, kind)
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"A {frm} request has no {event} action available to it.",
            code="invalid_transition",
            details=[{"from": exc.frm, "event": exc.event,
                      "allowed": sm.allowed_events(exc.frm, kind)}]) from exc
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError(
            "Your role cannot make that change.", code="actor_not_allowed",
            details=[{"from": exc.frm, "event": exc.event,
                      "actor": exc.actor_kind}]) from exc


def _step_for(row: LeaveRequest, status: str) -> tuple[str, str]:
    """The step kind and the designation expected to act next."""
    kind = STEP_BY_STATUS.get(status, "")
    if not kind:
        return "", ""
    if kind == "self_sanction":
        return kind, config_selector.current_policy().self_sanction_designation
    if kind == "substitute":
        # The nominee is a person, so the queue is theirs by id, not by office.
        return kind, ""
    path = facts.path_for(row)
    if kind == "unit_head":
        return kind, path.first_designation
    if kind == "establishment":
        return kind, path.establishment_designation
    if kind == "final_authority":
        return kind, (path.final_designation or path.first_designation)
    return kind, ""


@transaction.atomic
def transition(*, request_id: int, event: str, actor=None, reason: str = "",
               recommendation: str = "", context: dict | None = None,
               scope=None) -> LeaveRequest:
    """Move one request. `scope` makes an out-of-scope row a 404, not a 403."""
    context = dict(context or {})
    qs = scope if scope is not None else LeaveRequest.objects.all()
    row = (qs.select_for_update().select_related("parent")
           .filter(pk=request_id).first())
    if row is None:
        raise NotFoundError("No such leave request.")

    kind = authz.actor_kind(actor, row=row)
    edge = resolve_or_raise(row.status, event, kind)

    if actor is not None and not authz.has(actor, edge.permission):
        raise PermissionDeniedError(f"This action needs {edge.permission}.",
                                    code="permission_denied")

    for guard in edge.guards:
        guards.check(guard, row=row, actor=actor, reason=reason, context=context)

    frm = row.status
    row.status = edge.to
    if recommendation:
        row.unit_head_recommendation = recommendation
        row.unit_head_recommendation_reason = reason
    step_kind, step_designation = _step_for(row, edge.to)
    row.current_step_kind = step_kind
    row.current_step_designation = step_designation

    _apply_effects(row=row, edge=edge, frm=frm, actor=actor, reason=reason,
                   event=event)

    row.save()
    LeaveRequestTransition.objects.create(
        request=row, from_status=frm, to_status=row.status, event=event,
        actor_user_id=getattr(actor, "user_id", None),
        actor_kind=kind,
        actor_designation=getattr(actor, "active_role", "") or "",
        recommendation=recommendation or "", reason=reason,
    )
    _notify(row=row, event=event, frm=frm, actor=actor)
    log.info("leave.request.%s id=%s %s->%s actor=%s", event, row.pk, frm,
             row.status, getattr(actor, "user_id", None))
    return row


def _apply_effects(*, row: LeaveRequest, edge: sm.Transition, frm: str,
                   actor, reason: str, event: str) -> None:
    """The consequences of the edge: decision stamps and ledger movements."""
    actor_id = getattr(actor, "user_id", None)
    now = timezone.now()

    if edge.to == sm.APPROVED and event == sm.APPROVE:
        row.days_approved = row.days_requested
        row.finalised_at = now
        row.finalised_by_user_id = actor_id
        row.final_decision_reason = reason
        if not row.approved_days_posted:
            _post_approved_days(row=row, actor_id=actor_id)
    elif edge.to == sm.REJECTED:
        row.finalised_at = now
        row.finalised_by_user_id = actor_id
        row.final_decision_reason = reason
    elif edge.to == sm.CANCELLED:
        _apply_cancellation(row=row, actor_id=actor_id, reason=reason)
    elif edge.to == sm.WITHDRAWN:
        row.finalised_at = now
        row.final_decision_reason = reason or "Withdrawn by the applicant"


def _post_approved_days(*, row: LeaveRequest, actor_id: int | None) -> None:
    """BR-EL-005/009: approval is what consumes the balance, never submission."""
    account_service.debit_for_approval(request=row,
                                       days=row.days_approved or row.days_requested,
                                       actor_user_id=actor_id)
    row.approved_days_posted = True


def _apply_cancellation(*, row: LeaveRequest, actor_id: int | None,
                        reason: str) -> None:
    """BR-EL-023: the approved leave is marked cancelled and its days restored."""
    parent = row.parent
    if parent is None:
        return
    account_service.restore_for_cancellation(request=parent,
                                             days=parent.days_approved
                                             or parent.days_requested,
                                             actor_user_id=actor_id)
    frm = parent.status
    parent.status = sm.CANCELLED
    parent.final_decision_reason = reason
    parent.save(update_fields=["status", "final_decision_reason", "updated_at"])
    LeaveRequestTransition.objects.create(
        request=parent, from_status=frm, to_status=sm.CANCELLED,
        event="cancel_effective", actor_user_id=actor_id, actor_kind="system",
        reason=reason,
    )


def _notify(*, row: LeaveRequest, event: str, frm: str, actor) -> None:
    """BR-EL-035 where a person can be named; the rest is logged as a gap."""
    if row.status == sm.AWAITING_SUBSTITUTE and event == sm.SUBMIT:
        assignment = row.substitute_assignments.filter(state="pending") \
            .order_by("-id").first()
        if assignment is not None:
            notifications.enqueue(
                topic="request.substitute_requested",
                dedupe_key=f"substitute:{assignment.pk}",
                recipient_user_id=assignment.substitute_user_id,
                subject="You are nominated as a substitute",
                body=("A leave request from "
                      f"{row.start_date} to {row.end_date} needs responsibility "
                      "coverage. Accept or decline it in the leave module."),
                payload={"request_id": row.pk},
            )
    if row.status in sm.TERMINAL or row.status == sm.APPROVED:
        notifications.enqueue(
            topic=_decision_topic(row),
            dedupe_key=f"decision:{row.pk}:{row.status}",
            recipient_user_id=row.user_id,
            subject=f"Leave request {row.status.replace('_', ' ')}",
            body=(f"Your {cat.LABELS[row.category]} request for "
                  f"{row.start_date} to {row.end_date} is now "
                  f"{row.status.replace('_', ' ')}."),
            payload={"request_id": row.pk, "status": row.status},
        )


def _decision_topic(row: LeaveRequest) -> str:
    if row.kind == "cancellation":
        return "request.cancelled"
    if row.kind == "extension":
        return "request.extension_decided"
    if row.status == sm.APPROVED:
        return "request.approved"
    if row.status == sm.WITHDRAWN:
        return "request.withdrawn"
    return "request.rejected"


def status_for_new(*, category: str, substitute_required: bool,
                   applicant_role: str = "") -> str:
    """The state a freshly submitted application lands in, from the table."""
    if applicant_role == config_selector.current_policy().self_sanction_designation:
        return sm.AWAITING_DIRECTOR_SELF_SANCTION
    if substitute_required:
        return sm.AWAITING_SUBSTITUTE
    return sm.AWAITING_UNIT_HEAD


@transaction.atomic
def apply_for_leave(*, actor, category: str, start_date: date, end_date: date,
                    purpose: str, half: str = "", station_leave: dict | None = None,
                    substitute_user_id: int | None = None,
                    evidence_note: str = "") -> LeaveRequest:
    """Create and submit one application (EL-UC-001)."""
    authz.require(actor, "leave.request.create")
    user_id = getattr(actor, "user_id", None)
    is_faculty = facts.is_faculty(user_id)
    account_service.open_year(user_id=user_id, year=start_date.year,
                              is_faculty=is_faculty, actor_user_id=user_id)

    station = station_leave or {}
    row = LeaveRequest.objects.create(
        user_id=user_id, kind="new", category=category, start_date=start_date,
        end_date=end_date, half=half, purpose=purpose,
        applicant_role=getattr(actor, "active_role", "") or "",
        applicant_is_faculty=is_faculty,
        evidence_note=evidence_note,
        substitute_required=_needs_substitute(category),
        station_leave_required=bool(station.get("required")),
        station_leave_place=station.get("place", ""),
        station_leave_start=station.get("start"),
        station_leave_end=station.get("end"),
    )
    if substitute_user_id is not None:
        nominate_substitute(request=row, substitute_user_id=substitute_user_id,
                            actor=actor)
    return transition(request_id=row.pk, event=sm.SUBMIT, actor=actor)


def _needs_substitute(category: str) -> bool:
    """BR-EL-014: whether the current policy asks for responsibility coverage."""
    return category in config_selector.substitute_categories()


def nominate_substitute(*, request: LeaveRequest, substitute_user_id: int,
                        actor) -> SubstituteAssignment:
    """Validate and record one nominee (BR-EL-014)."""
    try:
        facts.check_substitute(row=request, substitute_user_id=substitute_user_id)
    except RuleViolation as exc:
        raise ConflictError(exc.message, code=exc.code,
                            details=exc.details) from exc
    SubstituteAssignment.objects.filter(request=request, state="pending") \
        .update(state="closed")
    return SubstituteAssignment.objects.create(
        request=request, substitute_user_id=substitute_user_id, state="pending")


@transaction.atomic
def request_cancellation(*, actor, request_id: int, reason: str = "") -> LeaveRequest:
    """Ask to cancel an approved leave before it starts (EL-UC-008)."""
    authz.require(actor, "leave.cancellation.create")
    parent = LeaveRequest.objects.filter(pk=request_id,
                                        user_id=getattr(actor, "user_id", None),
                                        kind="new").first()
    if parent is None:
        raise NotFoundError("No such leave request.")
    row = LeaveRequest.objects.create(
        user_id=parent.user_id, kind="cancellation", parent=parent,
        category=parent.category, start_date=parent.start_date,
        end_date=parent.end_date, half=parent.half,
        purpose=reason or f"Cancellation of the leave from {parent.start_date}",
        applicant_role=parent.applicant_role,
        applicant_is_faculty=parent.applicant_is_faculty,
        days_requested=parent.days_approved or parent.days_requested,
    )
    return transition(request_id=row.pk, event=sm.REQUEST_CANCELLATION, actor=actor,
                      reason=reason)


@transaction.atomic
def request_extension(*, actor, request_id: int, start_date: date, end_date: date,
                      purpose: str, substitute_user_id: int | None = None
                      ) -> LeaveRequest:
    """Ask for more time on an ongoing EL/COL/VL (EL-UC-009)."""
    authz.require(actor, "leave.extension.create")
    parent = LeaveRequest.objects.filter(pk=request_id,
                                        user_id=getattr(actor, "user_id", None),
                                        kind="new", status=sm.APPROVED).first()
    if parent is None:
        raise NotFoundError("No such approved leave request.")

    row = LeaveRequest.objects.create(
        user_id=parent.user_id, kind="extension", parent=parent,
        category=parent.category, start_date=start_date, end_date=end_date,
        purpose=purpose,        applicant_role=parent.applicant_role,
        applicant_is_faculty=parent.applicant_is_faculty,
        substitute_required=_needs_substitute(parent.category),
    )
    if substitute_user_id is not None:
        nominate_substitute(request=row, substitute_user_id=substitute_user_id,
                            actor=actor)
    return transition(request_id=row.pk, event=sm.REQUEST_EXTENSION, actor=actor)


def withdraw(*, actor, request_id: int, reason: str = "",
             scope=None) -> LeaveRequest:
    """EL-UC-007: immediate, and only while the request is still pending."""
    authz.require(actor, "leave.request.delete")
    return transition(request_id=request_id, event=sm.WITHDRAW, actor=actor,
                      reason=reason, scope=scope)
