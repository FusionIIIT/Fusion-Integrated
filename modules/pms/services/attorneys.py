"""Attorney assignment and the attorney's answer (UC-PMS-010, 011; BR-PMS-040..045, 127)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.pms.domain import assignment, validation
from modules.pms.domain import state_machine as sm
from modules.pms.models import AttorneyAssignment
from modules.pms.selectors import candidates, scoping
from modules.pms.selectors import policy as policy_selector
from modules.pms.services import escalations, notifications
from modules.pms.services.base import (
    conflicted,
    inventor_ids,
    lock,
    lock_application,
    move,
    move_record,
    now,
    require,
    ruled,
)
from modules.pms.services.review import refuse_conflicted_admin

P_ASSIGN = "pms.attorney.assign"
P_RESPOND = "pms.attorney_assignment.review"


@ruled
def assign_attorney(*, actor, pk: int, attorney_user_id: int,
                    exception_reason: str = "") -> AttorneyAssignment:
    require(actor, P_ASSIGN)
    app = scoping.applications_for(actor).filter(pk=pk).first()
    if app is not None and conflicted(actor, app):
        refuse_conflicted_admin(actor, app)
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        if app.status not in sm.ATTORNEY_ASSIGNABLE:
            raise ConflictError("An attorney can be assigned only after the Director approves "
                                "the application (BR-PMS-127).", code="not_approved")
        if app.attorney_assignments.filter(status__in=sorted(sm.LIVE_ASSIGNMENT)).exists():
            raise ConflictError("An attorney is already assigned or has an open offer for this "
                                "application.", code="assignment_exists")
        reason = (exception_reason or "").strip()[:2000]
        is_exception = assignment.check_attorney(
            attorney_user_id, candidates.attorney_candidates(), app.domain_code,
            app.applicant_user_id, inventor_ids(app), reason)
        offer = AttorneyAssignment(application=app, attorney_user_id=attorney_user_id,
                                   assigned_by_user_id=actor.user_id, is_exception=is_exception,
                                   exception_reason=reason if is_exception else "")
        move_record(sm.ASSIGNMENT, offer, "offer", sm.PCC_ADMIN, actor, application=app,
                    details={"attorney_user_id": attorney_user_id,
                             "is_exception": is_exception})
        escalations.resolve_open(app, ("no_eligible_attorney",), actor,
                                 "An attorney was assigned.")
        notifications.enqueue(
            topic="attorney.assigned", dedupe_key=f"attorney.offer:{offer.pk}",
            recipient_user_id=attorney_user_id, subject=f"Case offered: {app.reference}",
            body=f"Application {app.reference} '{app.title}' is offered to you. Accept or "
                 f"decline it under Assigned Cases.")
    return offer


@ruled
def respond(*, actor, assignment_id: int, accept: bool, reason: str = "") -> AttorneyAssignment:
    require(actor, P_RESPOND)
    offer = AttorneyAssignment.objects.filter(pk=assignment_id,
                                              attorney_user_id=actor.user_id).first()
    if offer is None:
        raise NotFoundError("No such assignment.", code="not_found")
    with transaction.atomic():
        app = lock_application(offer.application_id)
        offer = AttorneyAssignment.objects.select_for_update().get(pk=assignment_id)
        event = "accept" if accept else "decline"
        sm.ASSIGNMENT.resolve(offer.status, event, sm.ATTORNEY)
        if not accept:
            offer.decline_reason = validation.check_decline_reason(reason)
        offer.responded_at = now()
        move_record(sm.ASSIGNMENT, offer, event, sm.ATTORNEY, actor, application=app,
                    extra_fields=("responded_at", "decline_reason"))
        move(app, "attorney_accepted" if accept else "attorney_declined", sm.SYSTEM, actor,
             details={"assignment_id": offer.pk})
        spec = policy_selector.current()
        if accept:
            notifications.enqueue(
                topic="attorney.accepted", dedupe_key=f"attorney.accepted:{offer.pk}",
                recipient_user_id=app.applicant_user_id,
                subject=f"Attorney assigned: {app.reference}",
                body=f"An attorney accepted your application {app.reference}.")
        else:
            notifications.enqueue_many(
                topic="attorney.declined", key=f"attorney.declined:{offer.pk}",
                recipients=[spec.pcc_contact_user_id],
                subject=f"Attorney declined: {app.reference}",
                body=f"The attorney declined {app.reference}: {offer.decline_reason}\n\n"
                     f"Assign another attorney under Assignments.")
    return offer
