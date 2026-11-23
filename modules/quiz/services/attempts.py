"""Student attempt submission workflows."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.quiz.domain.attempts import deadline_reached
from modules.quiz.domain.errors import (
    ActorNotAllowed,
    AttemptEligibilityError,
    GuardFailed,
    InvalidTransition,
)
from modules.quiz.domain.state_machine import AttemptEvent, transition_attempt
from modules.quiz.domain.types import AttemptStatus, DomainActor
from modules.quiz.models import Attempt, QuizResult
from modules.quiz.selectors import attempt_for_student
from modules.quiz.services.authz import require_permission
from modules.quiz.services.events import enqueue_internal_event, record_audit_event


def _student_user_id(actor: object) -> int:
    user_id = getattr(actor, "user_id", None)
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise PermissionDeniedError("An authenticated Student is required.", code="actor_required")
    return user_id


@transaction.atomic
def submit_attempt(*, attempt_id: int, actor: object) -> Attempt:
    """Manually submit an owned attempt once; retries return its existing state."""

    require_permission(actor, "quiz.attempt.update")
    student_user_id = _student_user_id(actor)
    attempt = (
        attempt_for_student(attempt_id=attempt_id, student_user_id=student_user_id)
        .select_for_update(of=("self",))
        .first()
    )
    if attempt is None:
        raise NotFoundError("No such Student attempt.")
    if attempt.status == "submitted":
        return attempt
    try:
        current_status = {
            "in_progress": AttemptStatus.IN_PROGRESS,
            "submitted": AttemptStatus.SUBMITTED,
        }[attempt.status]
    except KeyError as exc:
        raise ConflictError(
            "The attempt has an unsupported persisted state.", code="invalid_attempt_state"
        ) from exc

    now = timezone.now()
    try:
        before_deadline = not deadline_reached(deadline_at=attempt.deadline_at, server_now=now)
    except AttemptEligibilityError as exc:
        raise ConflictError(str(exc), code=exc.code) from exc
    guards = {
        "owns_attempt": True,
        "before_deadline": before_deadline,
        "submission_confirmed": True,
    }
    try:
        transition_attempt(
            current_status,
            AttemptEvent.MANUAL_SUBMIT,
            DomainActor.STUDENT,
            guard_results=guards,
        )
    except ActorNotAllowed as exc:
        raise PermissionDeniedError(
            "A Student is required to submit this attempt.", code="actor_not_allowed"
        ) from exc
    except (GuardFailed, InvalidTransition) as exc:
        raise ConflictError(str(exc), code=exc.code) from exc

    attempt.status = "submitted"
    attempt.submitted_at = now
    attempt.submission_method = "manual"
    attempt.save(update_fields=["status", "submitted_at", "submission_method", "updated_at"])
    QuizResult.objects.create(attempt=attempt)
    record_audit_event(
        actor_user_id=student_user_id,
        actor_kind="Student",
        action="attempt.submitted",
        aggregate_type="attempt",
        aggregate_id=attempt.pk,
        occurred_at=now,
        context={"submission_method": "manual"},
    )
    enqueue_internal_event(
        event_type="attempt.submitted",
        aggregate_type="attempt",
        aggregate_id=attempt.pk,
        dedupe_key=f"attempt.submitted:{attempt.pk}",
        available_at=now,
        payload={"attempt_id": attempt.pk},
    )
    return attempt


@transaction.atomic
def auto_submit_expired_attempt(*, attempt_id: int) -> bool:
    """System-submit one expired attempt exactly once under its row lock."""

    attempt = Attempt.objects.select_for_update(of=("self",)).filter(pk=attempt_id).first()
    if attempt is None or attempt.status == "submitted":
        return False
    if attempt.status != "in_progress":
        return False

    now = timezone.now()
    try:
        if not deadline_reached(deadline_at=attempt.deadline_at, server_now=now):
            return False
    except AttemptEligibilityError as exc:
        raise ConflictError(str(exc), code=exc.code) from exc

    try:
        next_status = transition_attempt(
            AttemptStatus.IN_PROGRESS,
            AttemptEvent.AUTO_SUBMIT_DEADLINE,
            DomainActor.SYSTEM,
            guard_results={"deadline_reached": True},
        )
    except (ActorNotAllowed, GuardFailed, InvalidTransition) as exc:
        raise ConflictError(str(exc), code=exc.code) from exc

    attempt.status = next_status.value.lower().replace(" ", "_")
    attempt.submitted_at = now
    attempt.submission_method = "time_expiry"
    attempt.save(update_fields=["status", "submitted_at", "submission_method", "updated_at"])
    QuizResult.objects.create(attempt=attempt)
    record_audit_event(
        actor_user_id=None,
        actor_kind="System",
        action="attempt.auto_submitted",
        aggregate_type="attempt",
        aggregate_id=attempt.pk,
        occurred_at=now,
        context={"submission_method": "time_expiry"},
    )
    enqueue_internal_event(
        event_type="attempt.auto_submitted",
        aggregate_type="attempt",
        aggregate_id=attempt.pk,
        dedupe_key=f"attempt.auto_submitted:{attempt.pk}",
        available_at=now,
        payload={"attempt_id": attempt.pk},
    )
    return True
