"""Confidential feedback (CW-DEPT-02): submit, initial review, disposition, HOD notes."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.department.domain import rules
from modules.department.domain import state_machine as sm
from modules.department.domain.roles import DEPT_ADMIN, ActorContext
from modules.department.models import Feedback, FeedbackNote
from modules.department.selectors import scoping
from modules.department.selectors.actors import current_holders
from modules.department.services import notifications
from modules.department.services.common import get_scoped, own_department, translated

TERMINAL = (sm.FEEDBACK_RESOLVED, sm.FEEDBACK_CLOSED)


@transaction.atomic
def submit(ctx: ActorContext, *, subject: str, body: str) -> Feedback:
    """UC-DEPT-007: BR-DEPT-008, BR-DEPT-017, AFR-DEPT-044."""
    dept = own_department(ctx)
    with translated():
        sm.resolve("feedback", sm.NONE, sm.FEEDBACK_NEW, ctx.role)
        if not (subject or "").strip() or not (body or "").strip():
            raise rules.RuleViolation(
                "feedback_incomplete", "Give your feedback a subject and some text."
            )
    fb = Feedback.objects.create(
        department=dept,
        submitter_id=ctx.user_id,
        submitter_kind=ctx.role,
        subject=subject.strip(),
        body=body.strip(),
    )
    notifications.enqueue(
        topic="feedback.created",
        key=str(fb.pk),
        recipients=current_holders([dept.pk], DEPT_ADMIN).values(),
        subject=f"[{dept.code}] New feedback #{fb.pk}",
        body="New feedback is waiting for initial review.",
    )
    return fb


def _dispose(ctx: ActorContext, fb: Feedback, outcome: str, note: str) -> None:
    with translated():
        sm.resolve("feedback", fb.status, outcome, ctx.role)
    fb.status, fb.disposed_by, fb.disposed_at = outcome, ctx.user_id, timezone.now()
    fb.resolution_note = note
    notifications.enqueue(
        topic="feedback.disposed",
        key=str(fb.pk),
        recipients=[fb.submitter_id],
        subject=f"Your feedback #{fb.pk} was marked {outcome}",
        body=note or f"Your feedback was marked {outcome}.",
    )


@transaction.atomic
def review(
    ctx: ActorContext,
    feedback_id: int,
    *,
    category: str = "",
    disposition: str = "",
    note: str = "",
) -> Feedback:
    """UC-DEPT-008: BR-DEPT-018 first, then AFR-DEPT-021's optional closure in the same step."""
    fb = get_scoped(scoping.feedback_for(ctx), feedback_id, lock=True, what="feedback")
    with translated():
        rules.check_category(category)
        sm.resolve("feedback", fb.status, sm.FEEDBACK_UNDER_REVIEW, ctx.role)
        if disposition and disposition not in TERMINAL:
            raise rules.RuleViolation(
                "invalid_disposition", "Disposition must be resolved or closed."
            )
    fb.status, fb.category = sm.FEEDBACK_UNDER_REVIEW, category
    fb.reviewed_by, fb.reviewed_at = ctx.user_id, timezone.now()
    if disposition:
        _dispose(ctx, fb, disposition, note)
    fb.save()
    return fb


@transaction.atomic
def dispose(ctx: ActorContext, feedback_id: int, *, outcome: str, note: str = "") -> Feedback:
    """BR-DEPT-009, AFR-DEPT-022, AFR-DEPT-045."""
    fb = get_scoped(scoping.feedback_for(ctx), feedback_id, lock=True, what="feedback")
    if outcome not in TERMINAL:
        raise ConflictError(
            "Feedback can only be marked resolved or closed.", code="invalid_transition"
        )
    _dispose(ctx, fb, outcome, note)
    fb.save()
    return fb


@transaction.atomic
def add_note(ctx: ActorContext, feedback_id: int, *, body: str) -> FeedbackNote:
    """UC-DEPT-014: oversight without changing the status."""
    fb = get_scoped(scoping.feedback_for(ctx), feedback_id, lock=True, what="feedback")
    if fb.status == sm.FEEDBACK_NEW:
        raise ConflictError(
            "Feedback must have its initial review before oversight notes.",
            code="awaiting_initial_review",
        )
    if not (body or "").strip():
        with translated():
            raise rules.RuleViolation("note_empty", "Write the note before saving it.")
    return FeedbackNote.objects.create(feedback=fb, author_id=ctx.user_id, body=body.strip())
