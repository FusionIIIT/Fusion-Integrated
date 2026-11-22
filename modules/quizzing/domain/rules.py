"""Domain rules for quizzing schedule, navigation, autograding, and release."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any


class DomainRuleError(ValueError):
    """Domain business rule validation error."""


def validate_quiz_schedule(start_time: datetime, end_time: datetime, duration_minutes: int) -> None:
    if end_time <= start_time:
        raise DomainRuleError("End time must be strictly after start time. Please adjust schedule dates.")
    if duration_minutes <= 0:
        raise DomainRuleError("Duration must be greater than zero minutes. Please adjust duration.")


def validate_attempt_window(quiz_status: str, start_time: datetime, end_time: datetime, now: datetime) -> None:
    if quiz_status != "PUBLISHED":
        raise DomainRuleError("Quiz is not currently open for attempts. Please contact your instructor.")
    if now < start_time:
        raise DomainRuleError("Quiz start time has not been reached yet. Please wait until opening time.")
    if now > end_time:
        raise DomainRuleError("Quiz end time has passed. New attempts are no longer permitted.")


def validate_attempt_limit(existing_attempts_count: int, max_attempts: int) -> None:
    if existing_attempts_count >= max_attempts:
        raise DomainRuleError(
            f"You have reached the maximum allowed attempts ({max_attempts}) for this quiz."
        )


def is_attempt_expired(started_at: datetime, duration_minutes: int, end_time: datetime, now: datetime) -> bool:
    attempt_deadline = started_at + timedelta(minutes=duration_minutes)
    return now > end_time or now > attempt_deadline


def validate_linear_navigation(current_order: int, last_completed_order: int) -> None:
    if current_order < last_completed_order:
        raise DomainRuleError(
            "Back-navigation is restricted in linear mode. Please proceed forward to answer questions."
        )


def validate_submission_completeness(answered_count: int, total_count: int, allow_unanswered: bool) -> None:
    if not allow_unanswered and answered_count < total_count:
        unanswered = total_count - answered_count
        raise DomainRuleError(
            f"All questions are mandatory. You still have {unanswered} unanswered question(s)."
        )


def calculate_autograded_score(
    question_type: str,
    correct_answer: dict[str, Any],
    default_marks: Decimal,
    negative_marks: Decimal,
    submitted_answer: dict[str, Any] | None,
) -> Decimal:
    if not submitted_answer:
        return Decimal("0.0")

    marks = Decimal(str(default_marks))
    neg = Decimal(str(negative_marks)) if negative_marks else Decimal("0.0")

    if question_type in {"MCQ_SINGLE", "TRUE_FALSE"}:
        val = str(submitted_answer.get("choice", submitted_answer.get("value", ""))).strip().lower()
        target = str(correct_answer.get("choice", correct_answer.get("value", ""))).strip().lower()
        if not val:
            return Decimal("0.0")
        return marks if val == target else -neg

    if question_type == "MCQ_MULTI":
        submitted_choices = set(submitted_answer.get("choices", []))
        correct_choices = set(correct_answer.get("choices", []))
        if not submitted_choices:
            return Decimal("0.0")
        return marks if submitted_choices == correct_choices else -neg

    if question_type == "SHORT_ANSWER":
        ans = str(submitted_answer.get("text", "")).strip().lower()
        target = str(correct_answer.get("model_answer", "")).strip().lower()
        if not ans:
            return Decimal("0.0")
        if ans == target or (target and target in ans):
            return marks
        return -neg if neg > 0 else Decimal("0.0")

    return Decimal("0.0")


def determine_pass_fail(total_score: Decimal, passing_marks: Decimal) -> bool:
    return total_score >= passing_marks


def check_integrity_threshold(violation_count: int, threshold: int = 3) -> bool:
    return violation_count >= threshold


def can_release_grades(pending_review_count: int) -> bool:
    return pending_review_count == 0
