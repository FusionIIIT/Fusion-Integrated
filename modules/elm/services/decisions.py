"""Substitute, Unit Head, Establishment and sanctioning decisions (WF-EL-01).

Nobody decides their own request: the only exception is the Director's
self-sanction, which BR-EL-020 gives its own path.
"""
from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.elm.domain import leave_types as lt
from modules.elm.domain import workflow as wf
from modules.elm.domain.errors import RuleViolation
from modules.elm.models import LeaveApplication
from modules.elm.selectors import queues
from modules.elm.services import balances
from modules.elm.services.common import (
    announce_task,
    enforcing_rules,
    load,
    move,
    notify,
    require_permission,
    require_status,
)

APPROVE, REJECT = "approve", "reject"
RECOMMEND, NOT_RECOMMEND = "recommend", "not_recommend"
RECOMMENDED, NOT_RECOMMENDED = "RECOMMENDED", "NOT_RECOMMENDED"


def establishment_step_enabled() -> bool:
    return bool(getattr(settings, "ELM_ESTABLISHMENT_STEP", True))


def _not_own(principal, application: LeaveApplication) -> None:
    if application.user_id == principal.user_id:
        raise PermissionDeniedError("You cannot decide your own application.")


def _inform_applicant(application: LeaveApplication, topic: str, message: str, key: str) -> None:
    notify(application, topic, message, user_id=application.user_id, key=key)


def _conclude(application: LeaveApplication, *, approved: bool, actor_id: int,
              reason: str, role: str) -> None:
    """The last decision on a request, or on the cancellation of an approved one."""
    cancelling = application.pending_action == "CANCEL"
    target = wf.final_state(approved=approved, cancelling=cancelling)
    with enforcing_rules():
        if approved and not cancelling:
            balances.deduct(application)
    if approved and cancelling:
        balances.restore(application, application.days, "Cancelled before it began")
    application.decided_by = actor_id
    application.decided_at = timezone.now()
    application.decision_reason = reason
    action = {wf.APPROVED: "approved" if not cancelling else "cancellation_refused",
              wf.REJECTED: "rejected", wf.CANCELLED: "cancelled"}[target]
    application.pending_action = ""
    event = move(application, target, action=action, actor_id=actor_id, note=reason,
                 role=role)
    application.save()
    _inform_applicant(application, f"leave.{action}", f"Your leave was {action.replace('_', ' ')}.",
                      f"ev{event.pk}")


@transaction.atomic
def respond_as_substitute(principal, pk: int, *, accept: bool) -> LeaveApplication:
    """BR-EL-015: nothing moves on until the substitute has said yes."""
    application = load(pk)
    require_status(application, wf.AWAITING_SUBSTITUTE)
    if application.substitute_user_id != principal.user_id:
        raise PermissionDeniedError("You were not named as the substitute.")
    if accept:
        target = wf.after_substitute_accepts(application.is_director)
        action = "substitute_accepted"
    else:
        target, action = wf.SUBSTITUTE_DECLINED, "substitute_declined"
    event = move(application, target, action=action, actor_id=principal.user_id,
                 role=wf.SUBSTITUTE)
    application.save()
    if accept:
        announce_task(application, f"ev{event.pk}")
    else:
        _inform_applicant(application, "leave.substitute_declined",
                          "Your substitute declined. Name another or withdraw.", f"ev{event.pk}")
    return application


def _unit_scope(principal, application: LeaveApplication) -> None:
    require_permission(principal, queues.P_REVIEW)
    _not_own(principal, application)
    if not queues.same_unit(principal.user_id, application.user_id):
        raise PermissionDeniedError("This applicant is not in your unit.")


@transaction.atomic
def unit_head_decide(principal, pk: int, *, decision: str, reason: str = "") -> LeaveApplication:
    """BR-EL-016/017: final for CL and RH, a recommendation for everything else."""
    application = load(pk)
    require_status(application, wf.AWAITING_UNIT_HEAD)
    _unit_scope(principal, application)
    final = wf.unit_head_may_decide(application.leave_type)
    with enforcing_rules():
        if final and decision not in (APPROVE, REJECT):
            raise RuleViolation(f"For {application.leave_type} you approve or reject.",
                                "BR-EL-016")
        if not final and decision not in (RECOMMEND, NOT_RECOMMEND):
            raise RuleViolation(
                f"For {application.leave_type} you can only recommend or not recommend; "
                "a higher authority makes the decision.", "BR-EL-017")
    if final:
        _conclude(application, approved=decision == APPROVE, actor_id=principal.user_id,
                  reason=reason, role=wf.UNIT_HEAD)
        return application
    application.unit_head_recommendation = (
        RECOMMENDED if decision == RECOMMEND else NOT_RECOMMENDED)
    target = wf.after_unit_head_recommendation(establishment_step=establishment_step_enabled())
    event = move(application, target, action=decision, actor_id=principal.user_id, note=reason,
                 role=wf.UNIT_HEAD)
    application.save()
    announce_task(application, f"ev{event.pk}")
    return application


@transaction.atomic
def establishment_route(principal, pk: int, *, note: str = "") -> LeaveApplication:
    """BR-EL-019: the Establishment step resolves the sanctioning authority."""
    application = load(pk)
    require_status(application, wf.AWAITING_ESTABLISHMENT)
    require_permission(principal, queues.P_ROUTE)
    _not_own(principal, application)
    event = move(application, wf.AWAITING_FINAL, action="routed", actor_id=principal.user_id,
                 note=note, role=wf.ESTABLISHMENT)
    application.save()
    announce_task(application, f"ev{event.pk}")
    return application


@transaction.atomic
def final_decide(principal, pk: int, *, approve: bool, reason: str = "",
                 special_purpose_admissible: bool | None = None) -> LeaveApplication:
    """BR-EL-018. For SCL the authority, not the applicant, rules on admissibility (BR-EL-004)."""
    application = load(pk)
    require_status(application, wf.AWAITING_FINAL)
    require_permission(principal, queues.P_SANCTION)
    _not_own(principal, application)
    with enforcing_rules():
        if (approve and application.leave_type == lt.SCL and not application.pending_action
                and special_purpose_admissible is not True):
            raise RuleViolation("Confirm that the special purpose is admissible to approve SCL.",
                                "BR-EL-004")
    if application.leave_type == lt.SCL and special_purpose_admissible is not None:
        application.special_purpose_admissible = special_purpose_admissible
    _conclude(application, approved=approve, actor_id=principal.user_id, reason=reason,
              role=wf.SANCTION)
    return application


@transaction.atomic
def director_self_sanction(principal, pk: int, *, reason: str = "") -> LeaveApplication:
    """BR-EL-020: the Director's own leave is sanctioned by the Director, on the record."""
    application = load(pk)
    require_status(application, wf.AWAITING_DIRECTOR)
    require_permission(principal, queues.P_SELF_SANCTION)
    if application.user_id != principal.user_id:
        raise ConflictError("Only the Director who applied can self-sanction.",
                            code="not_the_applicant")
    _conclude(application, approved=True, actor_id=principal.user_id, reason=reason,
              role=wf.DIRECTOR)
    return application
