"""Director assignment and the review decision (UC-PMS-007, 008; BR-PMS-022..031)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.pms.domain import assignment, calendar, validation
from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import Application, ReviewCycle
from modules.pms.selectors import candidates, scoping
from modules.pms.selectors import policy as policy_selector
from modules.pms.services import escalations, notifications
from modules.pms.services.base import (
    conflicted,
    inventor_ids,
    lock,
    move,
    now,
    require,
    ruled,
    today,
)

P_ASSIGN = "pms.review.assign"
P_DECIDE = "pms.review.approve"
DECISION_EVENTS = {"approve": "approve", "reject": "reject",
                   "needs_revision": "request_revision"}


def refuse_conflicted_admin(actor, app: Application) -> None:
    """BR-PMS-027 / blueprint Q-6: refuse, and leave an escalation saying why."""
    if conflicted(actor, app):
        escalations.raise_case("conflicted_admin", app, app.pk,
                               note="PCC_ADMIN is the applicant or an inventor.")
        raise PermissionDeniedError(
            "You are the applicant or an inventor on this application, so you cannot act on "
            "it as PCC_ADMIN. It has been recorded for another office holder.",
            code="pcc_admin_conflicted")


def assign(app: Application, director_user_id: int, *, actor, actor_kind: str) -> ReviewCycle:
    """Open a review cycle; the caller holds the application lock (BW-PMS-01, 02)."""
    event = "reassign_director" if app.status == sm.UNDER_REVIEW else "assign_director"
    sm.APPLICATION.resolve(app.status, event, actor_kind)
    open_cycle = app.review_cycles.select_for_update().filter(status="open").first()
    if (event == "reassign_director" and open_cycle is not None
            and open_cycle.due_on >= today()
            and candidates.is_active_director(open_cycle.director_user_id)):
        raise ConflictError("The current Director's review period has not ended. "
                                "Reassign only after the deadline is missed or the Director "
                                "leaves the roster.", code="review_still_open")
    assignment.check_director(director_user_id, candidates.director_candidates(),
                              app.domain_code, app.applicant_user_id, inventor_ids(app))
    if open_cycle is not None:
        open_cycle.status = "reassigned"
        open_cycle.save(update_fields=["status", "updated_at"])
    spec = policy_selector.current()
    start = today()
    last = app.review_cycles.order_by("-cycle_no").values_list("cycle_no", flat=True).first()
    cycle = ReviewCycle.objects.create(
        application=app, cycle_no=(last or 0) + 1, director_user_id=director_user_id,
        assigned_by_user_id=getattr(actor, "user_id", None), assigned_on=start,
        due_on=calendar.review_due(start, spec.holidays))
    move(app, event, actor_kind, actor, details={"director_user_id": director_user_id,
                                                 "cycle_no": cycle.cycle_no})
    escalations.resolve_open(app, ("no_eligible_director", "missed_review"), actor,
                             "A Director was assigned.")
    notifications.enqueue(
        topic="review.assigned", dedupe_key=f"review.assigned:{cycle.pk}",
        recipient_user_id=director_user_id,
        subject=f"Review assigned: {app.reference}",
        body=f"Application {app.reference} '{app.title}' is assigned to you for review. "
             f"Decide by {cycle.due_on.isoformat()} (15 business days).")
    notifications.enqueue(
        topic="application.status", dedupe_key=f"review.assigned.applicant:{cycle.pk}",
        recipient_user_id=app.applicant_user_id,
        subject=f"{app.reference} is under review",
        body=f"Your application {app.reference} is now under review by a Director.")
    return cycle


@ruled
def assign_director(*, actor, pk: int, director_user_id: int) -> ReviewCycle:
    require(actor, P_ASSIGN)
    app = scoping.applications_for(actor).filter(pk=pk).first()
    if app is not None and conflicted(actor, app):
        refuse_conflicted_admin(actor, app)
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        return assign(app, director_user_id, actor=actor, actor_kind=sm.PCC_ADMIN)


@ruled
def decide(*, actor, pk: int, decision: str, justification: str) -> ReviewCycle:
    """BR-PMS-029..031; refusals in order: state, assignee, conflict, deadline, wording."""
    require(actor, P_DECIDE)
    event = DECISION_EVENTS.get(decision)
    if event is None:
        raise InvalidInput("Choose Approve, Reject or Needs Revision.",
                                      code="invalid_decision")
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        sm.APPLICATION.resolve(app.status, event, sm.DIRECTOR)
        cycle = app.review_cycles.select_for_update().filter(status="open").first()
        if cycle is None or cycle.director_user_id != actor.user_id:
            raise PermissionDeniedError("Only the Director assigned to this review can decide "
                                        "it.", code="not_assigned")
        if conflicted(actor, app):
            raise PermissionDeniedError("You are listed as an inventor on this application, "
                                        "so you cannot review it. Ask PCC_ADMIN to reassign it.",
                                        code="director_conflicted")
        if today() > cycle.due_on:
            raise ConflictError(
                f"The review deadline was {cycle.due_on.isoformat()}, so a decision can no "
                f"longer be recorded. PCC_ADMIN will reassign the review.",
                code="review_deadline_passed")
        text = validation.check_justification(justification)
        cycle.status, cycle.decision, cycle.justification = "decided", decision, text
        cycle.decided_at = now()
        cycle.save(update_fields=["status", "decision", "justification", "decided_at",
                                  "updated_at"])
        decided = today()
        app.decided_on = decided
        app.revision_due_on = None if decision == "approve" else calendar.revision_due(decided)
        app.appeal_due_on = (calendar.appeal_due(decided,
                                                 policy_selector.current().appeal_period_days)
                             if decision == "reject" else None)
        move(app, event, sm.DIRECTOR, actor, details={"cycle_no": cycle.cycle_no},
             extra_fields=("decided_on", "revision_due_on", "appeal_due_on"))
        _notify_decision(app, cycle)
    return cycle


def _notify_decision(app: Application, cycle: ReviewCycle) -> None:
    """PMS-AFR-062, 063, 196: the applicant gets the Director's feedback in full."""
    words = {"approve": "approved", "reject": "rejected",
             "needs_revision": "returned for revision"}[cycle.decision]
    tail = ""
    if cycle.decision != "approve":
        tail = (f"\n\nYou may revise and resubmit by {app.revision_due_on.isoformat()}"
                + (f", or appeal by {app.appeal_due_on.isoformat()}"
                   if app.appeal_due_on else "") + ".")
    notifications.enqueue(
        topic="review.decided", dedupe_key=f"review.decided:{cycle.pk}",
        recipient_user_id=app.applicant_user_id,
        subject=f"{app.reference} {words}",
        body=f"Your application {app.reference} was {words}.\n\nDirector's feedback:\n"
             f"{cycle.justification}{tail}")
    if cycle.decision == "approve":
        spec = policy_selector.current()
        notifications.enqueue_many(
            topic="review.approved", key=f"review.approved.office:{cycle.pk}",
            recipients=[spec.pcc_contact_user_id],
            subject=f"{app.reference} approved: assign an attorney",
            body=f"Application {app.reference} was approved and needs an attorney.")
