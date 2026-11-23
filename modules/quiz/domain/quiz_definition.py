"""Pure validation for quiz definitions and publication windows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from modules.quiz.domain.errors import DefinitionValidationError


class DefinitionAction(StrEnum):
    DRAFT_SAVE = "draft_save"
    PUBLISH_NOW = "publish_now"
    SCHEDULE = "schedule"


@dataclass(frozen=True)
class QuizDefinition:
    """Policy-neutral fields needed to validate a Quiz definition."""

    title: str | None = None
    course_id: int | None = None
    duration_seconds: int | None = None
    maximum_marks: Decimal | None = None
    passing_marks: Decimal | None = None
    permitted_attempts: int | None = None
    start_at: datetime | None = None
    close_at: datetime | None = None


def is_aware(value: object) -> bool:
    """Return whether a datetime has a usable UTC offset."""

    return (
        isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None
    )


def _finite_decimal(value: Decimal) -> bool:
    return isinstance(value, Decimal) and value.is_finite()


def validate_quiz_definition(
    definition: QuizDefinition,
    *,
    action: DefinitionAction,
    now: datetime | None = None,
) -> None:
    """Validate a draft or a complete immediate/future publication definition.

    Drafts may omit configuration. Publication requires a complete availability
    window. Passing-mark upper-bound policy is intentionally not assumed because
    the blueprint leaves confirmation of the common mark scale open.
    """

    issues: list[tuple[str, str]] = []
    if now is not None and not is_aware(now):
        issues.append(("now", "must be timezone-aware"))
    for field_name in ("start_at", "close_at"):
        value = getattr(definition, field_name)
        if value is not None and not is_aware(value):
            issues.append((field_name, "must be timezone-aware"))

    if definition.title is not None:
        if not isinstance(definition.title, str):
            issues.append(("title", "must be a string when supplied"))
        else:
            if not definition.title.strip():
                issues.append(("title", "must not be blank when supplied"))
            if len(definition.title) > 250:
                issues.append(("title", "must be at most 250 characters"))

    if definition.course_id is not None and (
        isinstance(definition.course_id, bool)
        or not isinstance(definition.course_id, int)
        or definition.course_id <= 0
    ):
        issues.append(("course_id", "must be a positive scalar identifier"))
    if definition.duration_seconds is not None and (
        isinstance(definition.duration_seconds, bool)
        or not isinstance(definition.duration_seconds, int)
        or definition.duration_seconds <= 0
    ):
        issues.append(("duration_seconds", "must be positive"))
    if definition.maximum_marks is not None and (
        not _finite_decimal(definition.maximum_marks) or definition.maximum_marks <= 0
    ):
        issues.append(("maximum_marks", "must be a finite positive Decimal"))
    if definition.passing_marks is not None and (
        not _finite_decimal(definition.passing_marks) or definition.passing_marks < 0
    ):
        issues.append(("passing_marks", "must be a finite non-negative Decimal"))
    if definition.permitted_attempts is not None and (
        isinstance(definition.permitted_attempts, bool)
        or not isinstance(definition.permitted_attempts, int)
        or definition.permitted_attempts <= 0
    ):
        issues.append(("permitted_attempts", "must be positive"))

    if (
        definition.start_at is not None
        and definition.close_at is not None
        and is_aware(definition.start_at)
        and is_aware(definition.close_at)
        and definition.close_at <= definition.start_at
    ):
        issues.append(("close_at", "must be later than start_at"))

    if action is not DefinitionAction.DRAFT_SAVE:
        if now is None or not is_aware(now):
            issues.append(("now", "a timezone-aware server time is required"))
        required = (
            "title",
            "course_id",
            "duration_seconds",
            "maximum_marks",
            "passing_marks",
            "permitted_attempts",
            "start_at",
            "close_at",
        )
        issues.extend(
            (field_name, "is required before publication")
            for field_name in required
            if getattr(definition, field_name) is None
        )
        window_is_valid = (
            definition.start_at is not None
            and definition.close_at is not None
            and now is not None
            and is_aware(definition.start_at)
            and is_aware(definition.close_at)
            and is_aware(now)
            and definition.close_at > definition.start_at
        )
        if window_is_valid:
            if action is DefinitionAction.PUBLISH_NOW:
                if not definition.start_at <= now < definition.close_at:
                    issues.append(
                        ("start_at", "immediate publication must be within the open window")
                    )
            elif action is DefinitionAction.SCHEDULE and definition.start_at <= now:
                issues.append(("start_at", "scheduled start must be in the future"))

    if issues:
        raise DefinitionValidationError(tuple(issues))
