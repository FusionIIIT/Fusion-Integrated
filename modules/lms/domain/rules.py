"""Pure-Python business rules for LMS (Course Management).

Implements BR-LMS-001 through BR-LMS-019. Strictly NO Django or database imports.
"""
from datetime import datetime
from decimal import Decimal

from .entities import AssignmentStatus, CourseRole, GradeStatus, MaterialStatus, SubmissionStatus, SubmissionType
from .errors import (
    CourseAccessDenied,
    GradeNotReleasedError,
    InvalidAssignmentState,
    InvalidMaterialState,
    ObserverAccessViolation,
    SubmissionOwnershipError,
    SubmissionTypeError,
    TAAuthoringRestriction,
    UnauthorizedGradingError,
)


def validate_course_access(is_member: bool, user_id: int, course_code: str) -> None:
    """BR-LMS-001 & BR-LMS-002: Access restricted to enrolled or linked users."""
    if not is_member:
        raise CourseAccessDenied(
            f"User {user_id} is not enrolled in or linked to course workspace '{course_code}'."
        )


def validate_observer_restriction(role: str, action: str) -> None:
    """BR-LMS-003: Observers have read-only access and cannot see student data."""
    if role == CourseRole.OBSERVER.value:
        restricted_actions = {"view_submission", "view_student_grades", "submit", "grade", "edit"}
        if action in restricted_actions:
            raise ObserverAccessViolation(
                f"Observers are prohibited from '{action}' and accessing student-specific data."
            )


def validate_ta_permission(action: str, can_post_announcements: bool = False) -> None:
    """BR-LMS-004: TAs cannot author assignments or materials, but can grade."""
    forbidden_for_ta = {
        "create_assignment",
        "edit_assignment",
        "delete_assignment",
        "create_material",
        "edit_material",
        "delete_material",
        "edit_course_structure",
    }
    if action in forbidden_for_ta:
        raise TAAuthoringRestriction(f"Teaching Assistants cannot perform '{action}'.")

    if action == "post_announcement" and not can_post_announcements:
        raise TAAuthoringRestriction(
            "This TA has not been granted announcement posting permissions for this course."
        )


def validate_material_visibility(status: str, role: str) -> bool:
    """BR-LMS-005 & BR-LMS-006: Non-faculty can only view published materials."""
    if role == CourseRole.FACULTY.value:
        return True
    return status == MaterialStatus.PUBLISHED.value


def validate_assignment_configuration(
    title: str,
    points_possible: Decimal,
    submission_type: str,
    due_date: datetime,
) -> None:
    """BR-LMS-009: Validate required assignment configuration fields."""
    if not title or not title.strip():
        raise InvalidAssignmentState("Assignment title cannot be empty.")
    if points_possible <= 0:
        raise InvalidAssignmentState("Points possible must be greater than zero.")
    valid_sub_types = {t.value for t in SubmissionType}
    if submission_type not in valid_sub_types:
        raise InvalidAssignmentState(f"Invalid submission type: '{submission_type}'. Must be one of {valid_sub_types}.")


def validate_submission_eligibility(
    assignment_status: str,
    current_time: datetime,
    release_date: datetime | None = None,
) -> None:
    """BR-LMS-010 & BR-LMS-011: Assignment must be published and release date reached."""
    if assignment_status == AssignmentStatus.DRAFT.value:
        raise InvalidAssignmentState("Cannot submit to an assignment that is still in Draft state.")
    if assignment_status == AssignmentStatus.SCHEDULED.value:
        if release_date and current_time < release_date:
            raise InvalidAssignmentState(f"Assignment is scheduled and not yet open until {release_date}.")


def validate_submission_type(configured_type: str, actual_type: str) -> None:
    """BR-LMS-012: Submission type must conform to configured assignment type."""
    if configured_type != actual_type:
        raise SubmissionTypeError(
            f"Submitted type '{actual_type}' does not match required assignment type '{configured_type}'."
        )


def evaluate_submission_timeliness(due_date: datetime, submission_time: datetime) -> str:
    """BR-LMS-013: Baseline on-time check against assignment due date."""
    if submission_time > due_date:
        return SubmissionStatus.LATE.value
    return SubmissionStatus.SUBMITTED.value


def validate_submission_ownership(
    submission_student_id: int,
    requesting_user_id: int,
    requesting_role: str,
) -> None:
    """BR-LMS-014: Students may only view or touch their own submissions."""
    if requesting_role == CourseRole.STUDENT.value and submission_student_id != requesting_user_id:
        raise SubmissionOwnershipError("Students cannot access another student's submission.")


def validate_grading_authority(role: str) -> None:
    """BR-LMS-015: Only Faculty and TAs have grading authority."""
    if role not in {CourseRole.FACULTY.value, CourseRole.TA.value}:
        raise UnauthorizedGradingError(f"Role '{role}' is not authorized to grade submissions.")


def validate_grade_release_authority(role: str) -> None:
    """BR-LMS-017: Only Faculty can release grades to students."""
    if role != CourseRole.FACULTY.value:
        raise UnauthorizedGradingError(f"Role '{role}' cannot release grades; only Faculty has release authority.")


def validate_grade_visibility_for_student(grade_status: str, role: str) -> None:
    """BR-LMS-016 & BR-LMS-018: Students can only view grades once released."""
    if role == CourseRole.STUDENT.value and grade_status != GradeStatus.RELEASED.value:
        raise GradeNotReleasedError("Grade is in draft state and is not visible to students.")
