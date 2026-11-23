"""Pure attempt admission and server-time deadline calculations."""

from __future__ import annotations

from datetime import datetime, timedelta

from modules.quiz.domain.errors import AttemptEligibilityError
from modules.quiz.domain.quiz_definition import is_aware
from modules.quiz.domain.types import QuizStatus


def require_attempt_eligibility(
    *,
    student_is_eligible: bool,
    quiz_status: QuizStatus,
    starts_at: datetime | None,
    closes_at: datetime | None,
    attempts_started: int,
    permitted_attempts: int,
    server_now: datetime,
) -> None:
    """Fail closed unless the supplied facts permit a new attempt.

    Academic eligibility is an input from an outer adapter; this function does
    not call an academic service or decide concurrent-active-attempt policy.
    """

    if not is_aware(server_now):
        raise AttemptEligibilityError(
            "invalid_server_time", "A timezone-aware server time is required."
        )
    if not student_is_eligible:
        raise AttemptEligibilityError(
            "student_not_eligible", "The student is not eligible for this quiz."
        )
    if quiz_status is not QuizStatus.AVAILABLE:
        raise AttemptEligibilityError("quiz_not_available", "The quiz is not currently available.")
    if starts_at is None or closes_at is None:
        raise AttemptEligibilityError(
            "availability_window_missing", "The quiz availability window is incomplete."
        )
    if not is_aware(starts_at) or not is_aware(closes_at):
        raise AttemptEligibilityError(
            "invalid_availability_time", "Quiz availability times must be timezone-aware."
        )
    if server_now < starts_at:
        raise AttemptEligibilityError(
            "quiz_not_started", "The quiz is not yet open for new attempts."
        )
    if server_now >= closes_at:
        raise AttemptEligibilityError("quiz_closed", "The quiz is closed to new attempts.")
    if (
        isinstance(attempts_started, bool)
        or not isinstance(attempts_started, int)
        or attempts_started < 0
        or isinstance(permitted_attempts, bool)
        or not isinstance(permitted_attempts, int)
        or permitted_attempts <= 0
    ):
        raise AttemptEligibilityError(
            "invalid_attempt_count", "Attempt counts and limits are invalid."
        )
    if attempts_started >= permitted_attempts:
        raise AttemptEligibilityError(
            "attempt_limit_reached", "No permitted attempts remain for this quiz."
        )


def calculate_attempt_deadline(started_at: datetime, duration_seconds: int) -> datetime:
    """Calculate the immutable deadline from server-recorded start and duration."""

    if not is_aware(started_at):
        raise AttemptEligibilityError(
            "invalid_start_time", "Attempt start time must be timezone-aware."
        )
    if (
        isinstance(duration_seconds, bool)
        or not isinstance(duration_seconds, int)
        or duration_seconds <= 0
    ):
        raise AttemptEligibilityError(
            "invalid_duration", "Attempt duration must be a positive number of seconds."
        )
    return started_at + timedelta(seconds=duration_seconds)


def deadline_reached(*, deadline_at: datetime, server_now: datetime) -> bool:
    """Compare an attempt deadline against explicitly supplied server time."""

    if not is_aware(deadline_at) or not is_aware(server_now):
        raise AttemptEligibilityError(
            "invalid_deadline_time", "Deadline and server time must be timezone-aware."
        )
    return server_now >= deadline_at
