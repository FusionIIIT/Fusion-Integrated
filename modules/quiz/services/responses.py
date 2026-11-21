"""Attempt-scoped, revision-checked Student response persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.quiz.domain.attempts import deadline_reached
from modules.quiz.domain.errors import AttemptEligibilityError
from modules.quiz.models import Response
from modules.quiz.selectors import attempt_for_student, student_attempt_presentation_rows
from modules.quiz.services.authz import require_permission
from modules.quiz.services.events import record_audit_event


@dataclass(frozen=True)
class ResponseSaved:
    """Safe acknowledgement for the Student's own answer write."""

    attempt_question_id: int
    revision: int
    saved_at: datetime


def _student_user_id(actor: object) -> int:
    user_id = getattr(actor, "user_id", None)
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise PermissionDeniedError("An authenticated Student is required.", code="actor_required")
    return user_id


@transaction.atomic
def save_response(
    *,
    attempt_id: int,
    attempt_question_id: int,
    actor: object,
    answer_payload: Any,
    expected_revision: int,
) -> ResponseSaved:
    """Save only an owned, active attempt item using optimistic revision control."""

    require_permission(actor, "quiz.response.update")
    student_user_id = _student_user_id(actor)
    if (
        isinstance(expected_revision, bool)
        or not isinstance(expected_revision, int)
        or expected_revision < 0
    ):
        raise ConflictError(
            "Refresh the attempt and use its current response revision.", code="bad_revision"
        )

    attempt = (
        attempt_for_student(attempt_id=attempt_id, student_user_id=student_user_id)
        .select_for_update(of=("self",))
        .first()
    )
    if attempt is None:
        raise NotFoundError("No such Student attempt.")
    if attempt.status != "in_progress":
        raise ConflictError("A submitted attempt cannot be changed.", code="attempt_submitted")

    now = timezone.now()
    try:
        if deadline_reached(deadline_at=attempt.deadline_at, server_now=now):
            raise ConflictError("The attempt deadline has passed.", code="attempt_deadline_passed")
    except AttemptEligibilityError as exc:
        raise ConflictError(str(exc), code=exc.code) from exc

    item_exists = (
        student_attempt_presentation_rows(
            attempt_id=attempt.pk,
            student_user_id=student_user_id,
        )
        .filter(id=attempt_question_id)
        .exists()
    )
    if not item_exists:
        raise NotFoundError("No such question in this Student attempt.")

    next_revision = expected_revision + 1
    if expected_revision == 0:
        try:
            with transaction.atomic():
                Response.objects.create(
                    attempt_question_id=attempt_question_id,
                    answer_payload=answer_payload,
                    saved_at=now,
                    revision=next_revision,
                )
        except IntegrityError as exc:
            raise ConflictError(
                "Another response save completed first; reload the latest answer.",
                code="response_revision_conflict",
            ) from exc
    else:
        updated = Response.objects.filter(
            attempt_question_id=attempt_question_id,
            revision=expected_revision,
        ).update(
            answer_payload=answer_payload,
            saved_at=now,
            revision=F("revision") + 1,
            updated_at=now,
        )
        if updated != 1:
            raise ConflictError(
                "Another response save completed first; reload the latest answer.",
                code="response_revision_conflict",
            )

    record_audit_event(
        actor_user_id=student_user_id,
        actor_kind="Student",
        action="attempt.response_saved",
        aggregate_type="attempt",
        aggregate_id=attempt.pk,
        occurred_at=now,
        context={"attempt_question_id": attempt_question_id, "revision": next_revision},
    )
    return ResponseSaved(attempt_question_id, next_revision, now)
