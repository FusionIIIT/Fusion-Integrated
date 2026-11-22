"""Course Grades and Evaluation domain logic and data structures (CFR-LMS-010, BR-LMS-015, BR-LMS-016, BR-LMS-017, BR-LMS-018, BR-LMS-019)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


class GradeDomainError(Exception):
    """Base error for grade domain violations."""


class GradeValidationError(GradeDomainError):
    """Raised when grade values fail business rules."""


class GradePermissionDenied(GradeDomainError):
    """Raised when an actor lacks authority for a grading action."""


@dataclass(frozen=True)
class GradeInputDTO:
    """Input payload for recording or updating a submission grade (UC-LMS-012, BR-LMS-015)."""

    submission_id: int
    score: Decimal
    feedback: str
    grader_id: int
    grader_role: str


@dataclass(frozen=True)
class GradeReleaseDTO:
    """Input payload for releasing grades to students (UC-LMS-013, BR-LMS-017)."""

    assignment_id: int
    actor_id: int
    actor_role: str
    submission_id: Optional[int] = None


def validate_grader_authority(actor_role: str) -> None:
    """Validate that actor is Faculty or TA permitted to grade (BR-LMS-015).

    Faculty ('instructor') and TAs ('ta') are authorized to grade submissions.
    Students ('student') and Observers ('observer') are strictly forbidden.
    """
    if actor_role not in ("instructor", "ta"):
        raise GradePermissionDenied("Only faculty and teaching assistants may grade submissions.")


def validate_release_authority(actor_role: str) -> None:
    """Validate that actor is Faculty permitted to release grades (BR-LMS-017).

    Under the current baseline, only Faculty ('instructor') can release grades.
    TAs ('ta') are explicitly prohibited from releasing grades (UC-LMS-013).
    """
    if actor_role != "instructor":
        raise GradePermissionDenied("Only faculty members are authorized to release grades to students.")


def validate_grade_score(score: Decimal, max_points: Decimal) -> None:
    """Validate that score is non-negative and does not exceed maximum points possible."""
    if score < Decimal("0.00"):
        raise GradeValidationError("Grade score cannot be negative.")
    if max_points is not None and max_points > Decimal("0.00") and score > max_points:
        raise GradeValidationError(f"Grade score {score} cannot exceed maximum points {max_points}.")


def validate_grade_viewer(
    actor_role: str,
    actor_id: int,
    submission_student_id: int,
    is_released: bool,
) -> bool:
    """Check whether actor may view the grade/feedback (BR-LMS-003, BR-LMS-016, BR-LMS-018).

    - Observers ('observer'): ALWAYS False (BR-LMS-003, CFR-LMS-015).
    - Faculty ('instructor') & TAs ('ta'): ALWAYS True.
    - Students ('student'): True ONLY if own submission AND grade has been released (BR-LMS-016, BR-LMS-018).
    """
    if actor_role == "observer":
        return False
    if actor_role in ("instructor", "ta"):
        return True
    if actor_role == "student":
        return actor_id == submission_student_id and is_released
    return False
