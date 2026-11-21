"""Draft Quiz authoring operations."""

from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import DomainError as ServiceDomainError
from core.api.exceptions import NotFoundError, PermissionDeniedError
from modules.quiz.domain.errors import DefinitionValidationError
from modules.quiz.domain.quiz_definition import (
    DefinitionAction,
    QuizDefinition,
    validate_quiz_definition,
)
from modules.quiz.models import Quiz
from modules.quiz.selectors import quiz_for_courses
from modules.quiz.services.authz import require_permission
from modules.quiz.services.events import record_audit_event


def _user_id(actor: object) -> int:
    """Read the authenticated scalar identity supplied by the API boundary."""

    user_id = getattr(actor, "user_id", None)
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise PermissionDeniedError(
            "An authenticated Quiz actor is required.", code="actor_required"
        )
    return user_id


def _validate_draft(definition: QuizDefinition) -> None:
    try:
        validate_quiz_definition(definition, action=DefinitionAction.DRAFT_SAVE)
    except DefinitionValidationError as exc:
        raise ServiceDomainError(
            "Correct the invalid Quiz fields before saving.",
            code=exc.code,
            details=[{"field": field, "message": message} for field, message in exc.issues],
        ) from exc


@transaction.atomic
def create_draft(
    *,
    actor: object,
    authorized_course_ids: Iterable[int],
    definition: QuizDefinition,
    description: str | None = None,
    instructions: str | None = None,
) -> Quiz:
    """Create a Draft in a course authorized by trusted caller-supplied scope facts."""

    require_permission(actor, "quiz.quiz.create")
    creator_id = _user_id(actor)
    _validate_draft(definition)
    if definition.course_id is None:
        raise ServiceDomainError(
            "Choose an authorized course for this Quiz draft.", code="course_required"
        )
    if definition.course_id not in frozenset(authorized_course_ids):
        raise PermissionDeniedError(
            "You cannot author Quizzes for that course.", code="course_scope"
        )

    quiz = Quiz.objects.create(
        course_id=definition.course_id,
        created_by_user_id=creator_id,
        title=definition.title or "",
        description=description or "",
        instructions=instructions or "",
        duration_seconds=definition.duration_seconds,
        maximum_marks=definition.maximum_marks,
        passing_marks=definition.passing_marks,
        permitted_attempts=definition.permitted_attempts,
        start_at=definition.start_at,
        close_at=definition.close_at,
    )
    record_audit_event(
        actor_user_id=creator_id,
        actor_kind="Professor",
        action="quiz.draft_created",
        aggregate_type="quiz",
        aggregate_id=quiz.pk,
        occurred_at=timezone.now(),
        context={"course_id": quiz.course_id},
    )
    return quiz


@transaction.atomic
def update_draft(
    *,
    public_id: object,
    actor: object,
    authorized_course_ids: Iterable[int],
    definition: QuizDefinition,
    description: str | None = None,
    instructions: str | None = None,
) -> Quiz:
    """Update an authorized Draft only; scheduled/active content is immutable here."""

    require_permission(actor, "quiz.quiz.update")
    actor_id = _user_id(actor)
    _validate_draft(definition)
    course_ids = frozenset(authorized_course_ids)
    quiz = quiz_for_courses(public_id=public_id, course_ids=course_ids).select_for_update().first()
    if quiz is None:
        raise NotFoundError("No Quiz exists in the supplied course scope.")
    if quiz.status != "draft":
        raise ServiceDomainError("Only a Draft Quiz can be edited.", code="quiz_not_editable")
    if definition.course_id is None or definition.course_id not in course_ids:
        raise PermissionDeniedError(
            "Choose a course in your authorized scope.", code="course_scope"
        )

    quiz.course_id = definition.course_id
    quiz.title = definition.title or ""
    quiz.duration_seconds = definition.duration_seconds
    quiz.maximum_marks = definition.maximum_marks
    quiz.passing_marks = definition.passing_marks
    quiz.permitted_attempts = definition.permitted_attempts
    quiz.start_at = definition.start_at
    quiz.close_at = definition.close_at
    update_fields = [
        "course_id",
        "title",
        "duration_seconds",
        "maximum_marks",
        "passing_marks",
        "permitted_attempts",
        "start_at",
        "close_at",
        "updated_at",
    ]
    changed_fields = [
        "title",
        "duration_seconds",
        "maximum_marks",
        "passing_marks",
        "permitted_attempts",
        "start_at",
        "close_at",
    ]
    if description is not None:
        quiz.description = description
        update_fields.append("description")
        changed_fields.append("description")
    if instructions is not None:
        quiz.instructions = instructions
        update_fields.append("instructions")
        changed_fields.append("instructions")
    quiz.save(update_fields=update_fields)
    record_audit_event(
        actor_user_id=actor_id,
        actor_kind="Professor",
        action="quiz.draft_updated",
        aggregate_type="quiz",
        aggregate_id=quiz.pk,
        occurred_at=timezone.now(),
        context={
            "course_id": quiz.course_id,
            "changed_fields": changed_fields,
        },
    )
    return quiz
