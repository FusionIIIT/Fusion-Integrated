"""UC-DEPT-007 Submit Feedback, UC-DEPT-008 Initial Review and Disposition,
UC-DEPT-014 HOD oversight."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.dept.domain import state_machine as sm
from modules.dept.models import Feedback, FeedbackEvent
from modules.dept.selectors import scoping
from modules.dept.services._errors import require, translated


@transaction.atomic
def submit(*, actor, subject: str, body: str) -> Feedback:
    require(actor, "dept.feedback.create")                        # BR-DEPT-008
    if not (subject or "").strip() or not (body or "").strip():
        raise ConflictError("Feedback needs a subject and a message.",
                            code="content_required")
    feedback = Feedback.objects.create(
        submitted_by_user_id=actor.user_id, submitted_by_role=actor.kind,
        subject=subject.strip(), body=body)
    FeedbackEvent.objects.create(feedback=feedback, to_status=sm.NEW,
                                 actor_user_id=actor.user_id)
    return feedback


def _locked(actor, feedback_id: int) -> Feedback:
    """Looked up through the actor's scope, so a feedback item they may not see
    (a New one, for the HOD) is a 404 rather than a 403 (BR-DEPT-017)."""
    visible = scoping.feedback_for(actor).values("pk")
    feedback = (Feedback.objects.select_for_update()
                .filter(pk=feedback_id, pk__in=visible).first())
    if feedback is None:
        raise NotFoundError("No such feedback.")
    return feedback


@transaction.atomic
def move(*, feedback_id: int, actor, to_status: str, category: str = "",
         note: str = "") -> Feedback:
    feedback = _locked(actor, feedback_id)
    with translated():
        sm.validate_transition(sm.FEEDBACK_TRANSITIONS, feedback.status,
                               to_status, actor.permissions)
    if to_status == sm.UNDER_REVIEW and not (category or "").strip():
        raise ConflictError("Initial review must categorise the feedback.",
                            code="category_required")     # BR-DEPT-018
    if to_status in sm.FEEDBACK_TERMINAL and not (note or "").strip():
        raise ConflictError("Say how this was resolved or why it was closed.",
                            code="note_required")

    frm = feedback.status
    feedback.status = to_status
    if category:
        feedback.category = category.strip()
    if to_status in sm.FEEDBACK_TERMINAL:
        feedback.resolution_note = note
    feedback.save()
    FeedbackEvent.objects.create(feedback=feedback, from_status=frm,
                                 to_status=to_status,
                                 actor_user_id=actor.user_id, note=note)
    return feedback
