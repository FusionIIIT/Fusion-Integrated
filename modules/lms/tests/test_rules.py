"""Unit tests for pure-Python LMS business rules (BR-LMS-001 through BR-LMS-019)."""
from datetime import datetime, timedelta
from decimal import Decimal
import pytest

from modules.lms.domain.entities import CourseRole, GradeStatus, MaterialStatus, SubmissionStatus
from modules.lms.domain.errors import (
    CourseAccessDenied,
    GradeNotReleasedError,
    InvalidAssignmentState,
    ObserverAccessViolation,
    SubmissionOwnershipError,
    SubmissionTypeError,
    TAAuthoringRestriction,
    UnauthorizedGradingError,
)
from modules.lms.domain.rules import (
    evaluate_submission_timeliness,
    validate_assignment_configuration,
    validate_course_access,
    validate_grade_release_authority,
    validate_grade_visibility_for_student,
    validate_grading_authority,
    validate_material_visibility,
    validate_observer_restriction,
    validate_submission_eligibility,
    validate_submission_ownership,
    validate_submission_type,
    validate_ta_permission,
)


def test_course_access_allowed_for_enrolled_user():
    """BR-LMS-001 & BR-LMS-002: Enrolled user access passes."""
    validate_course_access(is_member=True, user_id=101, course_code="CS3010")


def test_course_access_denied_for_non_member():
    """BR-LMS-001: Access denied for non-enrolled user."""
    with pytest.raises(CourseAccessDenied):
        validate_course_access(is_member=False, user_id=999, course_code="CS3010")


def test_observer_cannot_access_student_submissions_or_grades():
    """BR-LMS-003: Observers cannot view student submissions or grade."""
    with pytest.raises(ObserverAccessViolation):
        validate_observer_restriction("observer", "view_submission")
    with pytest.raises(ObserverAccessViolation):
        validate_observer_restriction("observer", "grade")
    with pytest.raises(ObserverAccessViolation):
        validate_observer_restriction("observer", "submit")


def test_observer_allowed_read_only_course_details():
    """BR-LMS-003: Observer can view course materials and announcements."""
    validate_observer_restriction("observer", "view_materials")
    validate_observer_restriction("observer", "view_announcements")


def test_ta_cannot_create_or_delete_assignments():
    """BR-LMS-004: TA authoring restriction."""
    with pytest.raises(TAAuthoringRestriction):
        validate_ta_permission("create_assignment")
    with pytest.raises(TAAuthoringRestriction):
        validate_ta_permission("delete_assignment")
    with pytest.raises(TAAuthoringRestriction):
        validate_ta_permission("create_material")


def test_ta_announcement_permission():
    """BR-LMS-004: TA announcement posting requires explicit grant."""
    with pytest.raises(TAAuthoringRestriction):
        validate_ta_permission("post_announcement", can_post_announcements=False)
    # Permitted TA passes
    validate_ta_permission("post_announcement", can_post_announcements=True)


def test_material_visibility():
    """BR-LMS-005 & BR-LMS-006: Non-faculty can only view published materials."""
    assert validate_material_visibility("draft", CourseRole.FACULTY.value) is True
    assert validate_material_visibility("draft", CourseRole.STUDENT.value) is False
    assert validate_material_visibility("published", CourseRole.STUDENT.value) is True
    assert validate_material_visibility("published", CourseRole.OBSERVER.value) is True


def test_assignment_configuration_validation():
    """BR-LMS-009: Assignment required fields."""
    now = datetime(2026, 11, 15, 23, 59)
    # Valid passes
    validate_assignment_configuration("Midsem Lab", Decimal("100.00"), "file", now)

    # Empty title raises
    with pytest.raises(InvalidAssignmentState):
        validate_assignment_configuration("", Decimal("100.00"), "file", now)

    # Non-positive points raises
    with pytest.raises(InvalidAssignmentState):
        validate_assignment_configuration("Lab 1", Decimal("0.00"), "file", now)

    # Invalid submission type raises
    with pytest.raises(InvalidAssignmentState):
        validate_assignment_configuration("Lab 1", Decimal("50.00"), "video", now)


def test_submission_eligibility():
    """BR-LMS-010 & BR-LMS-011: Cannot submit to draft or unreleased assignment."""
    now = datetime(2026, 11, 10, 10, 0)
    future = datetime(2026, 11, 12, 10, 0)

    # Draft raises
    with pytest.raises(InvalidAssignmentState):
        validate_submission_eligibility("draft", now)

    # Scheduled in future raises
    with pytest.raises(InvalidAssignmentState):
        validate_submission_eligibility("scheduled", now, release_date=future)

    # Available passes
    validate_submission_eligibility("available", now)


def test_submission_type_conformity():
    """BR-LMS-012: Actual submission type must match assignment configured type."""
    validate_submission_type("file", "file")
    with pytest.raises(SubmissionTypeError):
        validate_submission_type("file", "text")


def test_submission_timeliness_evaluation():
    """BR-LMS-013: Timeliness check against due date."""
    due = datetime(2026, 11, 10, 23, 59)
    on_time = datetime(2026, 11, 10, 20, 0)
    late = datetime(2026, 11, 11, 0, 1)

    assert evaluate_submission_timeliness(due, on_time) == SubmissionStatus.SUBMITTED.value
    assert evaluate_submission_timeliness(due, late) == SubmissionStatus.LATE.value


def test_submission_ownership_privacy():
    """BR-LMS-014: Students cannot view other students' submissions."""
    # Student accessing own submission passes
    validate_submission_ownership(101, 101, CourseRole.STUDENT.value)

    # Student accessing another student raises
    with pytest.raises(SubmissionOwnershipError):
        validate_submission_ownership(101, 102, CourseRole.STUDENT.value)

    # Faculty can access any student submission
    validate_submission_ownership(101, 200, CourseRole.FACULTY.value)


def test_grading_authority():
    """BR-LMS-015: Faculty and TAs can grade; Students cannot."""
    validate_grading_authority(CourseRole.FACULTY.value)
    validate_grading_authority(CourseRole.TA.value)
    with pytest.raises(UnauthorizedGradingError):
        validate_grading_authority(CourseRole.STUDENT.value)


def test_grade_release_authority():
    """BR-LMS-017: Only Faculty can release grades; TAs cannot."""
    validate_grade_release_authority(CourseRole.FACULTY.value)
    with pytest.raises(UnauthorizedGradingError):
        validate_grade_release_authority(CourseRole.TA.value)


def test_grade_visibility_for_student():
    """BR-LMS-016 & BR-LMS-018: Students cannot see draft grades; only released."""
    # Draft grade raises
    with pytest.raises(GradeNotReleasedError):
        validate_grade_visibility_for_student(GradeStatus.DRAFT.value, CourseRole.STUDENT.value)

    # Released grade passes
    validate_grade_visibility_for_student(GradeStatus.RELEASED.value, CourseRole.STUDENT.value)
