"""Transactional Quiz lifecycle operations."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from core.api.exceptions import DomainError as ServiceDomainError
from modules.quiz.domain.errors import (
    ActorNotAllowed,
    DefinitionValidationError,
    GuardFailed,
    InvalidTransition,
)
from modules.quiz.domain.quiz_definition import (
    DefinitionAction,
    QuizDefinition,
    validate_quiz_definition,
)
from modules.quiz.domain.state_machine import QuizEvent, transition_quiz
from modules.quiz.domain.types import DomainActor, QuizStatus
from modules.quiz.models import Quiz
from modules.quiz.selectors import quiz_for_courses
from modules.quiz.services.authz import require_permission
from modules.quiz.services.events import enqueue_internal_event, record_audit_event


def _definition(quiz: Quiz) -> QuizDefinition:
    return QuizDefinition(
        title=quiz.title,
        course_id=quiz.course_id,
        duration_seconds=quiz.duration_seconds,
        maximum_marks=quiz.maximum_marks,
        passing_marks=quiz.passing_marks,
        permitted_attempts=quiz.permitted_attempts,
        start_at=quiz.start_at,
        close_at=quiz.close_at,
    )


@transaction.atomic
def publish_quiz(
    *,
    public_id: UUID,
    actor: object,
    authorized_course_ids: Iterable[int],
    action: DefinitionAction,
) -> Quiz:
    """Publish now or schedule an authorized Draft under a row lock."""

    require_permission(actor, "quiz.quiz.publish")
    actor_user_id = getattr(actor, "user_id", None)
    if isinstance(actor_user_id, bool) or not isinstance(actor_user_id, int) or actor_user_id <= 0:
        raise PermissionDeniedError(
            "An authenticated Professor is required.", code="actor_required"
        )
    if action not in {DefinitionAction.PUBLISH_NOW, DefinitionAction.SCHEDULE}:
        raise ServiceDomainError(
            "Choose publish-now or schedule action.", code="bad_lifecycle_action"
        )

    quiz = (
        quiz_for_courses(public_id=public_id, course_ids=frozenset(authorized_course_ids))
        .select_for_update()
        .first()
    )
    if quiz is None:
        raise NotFoundError("No Quiz exists in the supplied course scope.")

    now = timezone.now()
    try:
        validate_quiz_definition(_definition(quiz), action=action, now=now)
    except DefinitionValidationError as exc:
        raise ServiceDomainError(
            "Correct the Quiz fields before publishing or scheduling.",
            code=exc.code,
            details=[{"field": field, "message": message} for field, message in exc.issues],
        ) from exc

    event = QuizEvent.PUBLISH_NOW if action is DefinitionAction.PUBLISH_NOW else QuizEvent.SCHEDULE
    try:
        next_status = transition_quiz(
            QuizStatus(quiz.status.title()),
            event,
            DomainActor.PROFESSOR,
            guard_results={
                "valid_for_publication": True,
                "within_availability_window": action is DefinitionAction.PUBLISH_NOW,
                "start_is_future": action is DefinitionAction.SCHEDULE,
            },
        )
    except ActorNotAllowed as exc:
        raise PermissionDeniedError(
            "A Professor is required for this Quiz transition.", code="actor_not_allowed"
        ) from exc
    except GuardFailed as exc:
        raise ConflictError(str(exc), code=exc.code) from exc
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code=exc.code) from exc

    quiz.status = next_status.value.lower()
    quiz.save(update_fields=["status", "updated_at"])
    action_name = "quiz.published" if event is QuizEvent.PUBLISH_NOW else "quiz.scheduled"
    record_audit_event(
        actor_user_id=actor_user_id,
        actor_kind="Professor",
        action=action_name,
        aggregate_type="quiz",
        aggregate_id=quiz.pk,
        occurred_at=now,
        context={"status": quiz.status},
    )
    enqueue_internal_event(
        event_type=action_name,
        aggregate_type="quiz",
        aggregate_id=quiz.pk,
        dedupe_key=f"{action_name}:{quiz.pk}",
        available_at=now,
        payload={"quiz_public_id": str(quiz.public_id), "status": quiz.status},
    )
    return quiz


@transaction.atomic
def process_quiz_boundary(*, quiz_id: int) -> bool:
    """Apply one due system boundary transition; stale invocations are no-ops."""

    quiz = Quiz.objects.select_for_update(of=("self",)).filter(pk=quiz_id).first()
    if quiz is None:
        return False

    now = timezone.now()
    current = {
        "scheduled": QuizStatus.SCHEDULED,
        "available": QuizStatus.AVAILABLE,
    }.get(quiz.status)
    if current is QuizStatus.SCHEDULED:
        if quiz.start_at is None or now < quiz.start_at:
            return False
        if quiz.close_at is None or now >= quiz.close_at:
            # The state machine has no Scheduled -> Closed edge. Preserve the
            # persisted state for this unresolved boundary case.
            return False
        event = QuizEvent.START_BOUNDARY
        guards = {"start_boundary_reached": True, "before_close": True}
        action = "quiz.activated"
    elif current is QuizStatus.AVAILABLE:
        if quiz.close_at is None or now < quiz.close_at:
            return False
        event = QuizEvent.CLOSE_BOUNDARY
        guards = {"close_boundary_reached": True}
        action = "quiz.closed"
    else:
        return False

    try:
        next_status = transition_quiz(
            current,
            event,
            DomainActor.SYSTEM,
            guard_results=guards,
        )
    except (ActorNotAllowed, GuardFailed, InvalidTransition) as exc:
        raise ConflictError(str(exc), code=exc.code) from exc

    quiz.status = next_status.value.lower()
    quiz.save(update_fields=["status", "updated_at"])
    record_audit_event(
        actor_user_id=None,
        actor_kind="System",
        action=action,
        aggregate_type="quiz",
        aggregate_id=quiz.pk,
        occurred_at=now,
        context={"status": quiz.status},
    )
    enqueue_internal_event(
        event_type=action,
        aggregate_type="quiz",
        aggregate_id=quiz.pk,
        dedupe_key=f"{action}:{quiz.pk}",
        available_at=now,
        payload={"quiz_public_id": str(quiz.public_id), "status": quiz.status},
    )
    return True
