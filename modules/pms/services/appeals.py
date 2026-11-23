"""Appeals against a rejection (UC-PMS-022, 023; BR-PMS-092..095; ruling C8, Q-1, Q-4)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.pms.domain import appeals as ap
from modules.pms.domain import assignment, calendar, validation
from modules.pms.domain import state_machine as sm
from modules.pms.models import Appeal
from modules.pms.selectors import candidates, scoping
from modules.pms.selectors import policy as policy_selector
from modules.pms.services import audit, notifications
from modules.pms.services.applications import notify_office
from modules.pms.services.base import (
    conflicted,
    inventor_ids,
    lock,
    lock_application,
    move,
    move_record,
    now,
    owner_only,
    require,
    ruled,
    today,
)

P_FILE = "pms.appeal.create"
P_ASSIGN = "pms.review.assign"
P_DECIDE = "pms.appeal.review"


@ruled
def file_appeal(*, actor, pk: int, grounds: str, justification: str) -> Appeal:
    require(actor, P_FILE)
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        owner_only(actor, app)
        sm.APPLICATION.resolve(app.status, "appeal", sm.APPLICANT)
        ap.check_open(today(), app.appeal_due_on, app.revision_due_on)
        g, j = validation.check_appeal_grounds(grounds, justification)
        rejected = (app.review_cycles.filter(status="decided", decision="reject")
                    .order_by("-cycle_no").first())
        appeal = Appeal.objects.create(application=app, rejected_cycle=rejected, grounds=g,
                                       justification=j)
        # Ruling B7: an open appeal stops the 60-day clock.
        app.revision_due_on = None
        move(app, "appeal", sm.APPLICANT, actor, details={"appeal_id": appeal.pk},
             extra_fields=("revision_due_on",))
        notify_office(policy_selector.current(), "appeal.filed", f"appeal:{appeal.pk}",
                      f"Appeal filed on {app.reference}",
                      f"An appeal was filed against the rejection of {app.reference}. Assign "
                      f"a Director other than the one who rejected it.")
    return appeal


@ruled
def assign_appeal(*, actor, appeal_id: int, director_user_id: int) -> Appeal:
    """Blueprint Q-1: an eligible Director other than the one who rejected the application."""
    require(actor, P_ASSIGN)
    appeal = scoping.appeals_for(actor).filter(pk=appeal_id).first()
    if appeal is None:
        raise NotFoundError("No such appeal.", code="not_found")
    with transaction.atomic():
        app = lock_application(appeal.application_id)
        appeal = Appeal.objects.select_for_update().get(pk=appeal_id)
        if conflicted(actor, app):
            raise PermissionDeniedError("You are the applicant or an inventor on this "
                                        "application, so you cannot assign its appeal.",
                                        code="pcc_admin_conflicted")
        if appeal.status != sm.APPEAL_OPEN:
            raise ConflictError("This appeal has already been decided.", code="appeal_closed")
        if director_user_id == appeal.rejected_cycle.director_user_id:
            raise ConflictError("Choose a Director other than the one who rejected the "
                                "application.", code="appeal_same_director")
        assignment.check_director(director_user_id, candidates.director_candidates(),
                                  app.domain_code, app.applicant_user_id, inventor_ids(app))
        appeal.director_user_id = director_user_id
        appeal.save(update_fields=["director_user_id", "updated_at"])
        audit.record(actor, "appeal.assigned", application=app, obj=appeal,
                     details={"director_user_id": director_user_id})
        notifications.enqueue(
            topic="appeal.assigned",
            dedupe_key=f"appeal.assigned:{appeal.pk}:{director_user_id}",
            recipient_user_id=director_user_id, subject=f"Appeal to review: {app.reference}",
            body=f"The appeal against the rejection of {app.reference} is assigned to you.")
    return appeal


@ruled
def decide_appeal(*, actor, appeal_id: int, outcome: str, modified_decision: str | None,
                  note: str) -> Appeal:
    require(actor, P_DECIDE)
    appeal = scoping.appeals_for(actor).filter(pk=appeal_id).first()
    if appeal is None:
        raise NotFoundError("No such appeal.", code="not_found")
    with transaction.atomic():
        app = lock_application(appeal.application_id)
        appeal = Appeal.objects.select_for_update().get(pk=appeal_id)
        sm.APPEAL.resolve(appeal.status, outcome, sm.DIRECTOR)
        if appeal.director_user_id != actor.user_id:
            raise PermissionDeniedError("Only the Director assigned to this appeal can "
                                        "decide it.", code="not_assigned")
        if conflicted(actor, app):
            raise PermissionDeniedError("You are listed as an inventor on this application, "
                                        "so you cannot decide its appeal.",
                                        code="director_conflicted")
        event = ap.application_event(outcome, modified_decision)
        text = validation.check_justification(note)
        appeal.outcome = outcome
        appeal.modified_decision = modified_decision if outcome == ap.MODIFY else ""
        appeal.outcome_note, appeal.decided_at = text, now()
        move_record(sm.APPEAL, appeal, outcome, sm.DIRECTOR, actor, application=app,
                    extra_fields=("outcome", "modified_decision", "outcome_note", "decided_at"))
        decided = today()
        app.decided_on = decided
        app.revision_due_on = (calendar.revision_due(decided)
                               if event in ("appeal_remanded", "appeal_modified_revise")
                               else None)
        app.appeal_due_on = None
        move(app, event, sm.SYSTEM, actor, details={"appeal_id": appeal.pk},
             extra_fields=("decided_on", "revision_due_on", "appeal_due_on"))
        words = {"uphold": "upheld the rejection", "remand": "remanded it for amendment",
                 "modify": "modified the decision"}[outcome]
        notifications.enqueue(
            topic="appeal.decided", dedupe_key=f"appeal.decided:{appeal.pk}",
            recipient_user_id=app.applicant_user_id,
            subject=f"Appeal decided: {app.reference}",
            body=f"The Director {words}.\n\n{text}"
                 + (f"\n\nRevise and resubmit by {app.revision_due_on.isoformat()}."
                    if app.revision_due_on else ""))
    return appeal
