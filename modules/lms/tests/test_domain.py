"""Domain layer unit tests: pure Python, zero database dependencies."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from modules.lms.domain import calculations, rules, validators
from modules.lms.domain import state_machine as sm
from modules.lms.domain.constants import (
    AssignmentStatus,
    GradeStatus,
    MaterialStatus,
    MaterialType,
    SubmissionType,
)

# ==============================================================================
# State Machines
# ==============================================================================


def test_material_fsm_immediate_and_scheduled():
    now = datetime.now(UTC)
    future = now + timedelta(days=2)

    # Immediate publication
    assert sm.MaterialFSM.publish(None, now) == MaterialStatus.PUBLISHED
    # Future publication -> SCHEDULED
    assert sm.MaterialFSM.publish(future, now) == MaterialStatus.SCHEDULED


def test_material_fsm_auto_release():
    now = datetime.now(UTC)
    past = now - timedelta(hours=1)
    future = now + timedelta(hours=1)

    # Due for release -> PUBLISHED
    assert (
        sm.MaterialFSM.auto_release(MaterialStatus.SCHEDULED, past, now) == MaterialStatus.PUBLISHED
    )

    # Not yet due -> raises IllegalTransitionError
    with pytest.raises(sm.IllegalTransitionError, match="not yet arrived"):
        sm.MaterialFSM.auto_release(MaterialStatus.SCHEDULED, future, now)

    # Wrong status -> raises IllegalTransitionError
    with pytest.raises(sm.IllegalTransitionError, match="Cannot auto-release"):
        sm.MaterialFSM.auto_release(MaterialStatus.DRAFT, past, now)


def test_assignment_fsm_publish():
    now = datetime.now(UTC)
    future = now + timedelta(days=1)

    # Immediate
    assert sm.AssignmentFSM.publish(AssignmentStatus.DRAFT, None, now) == AssignmentStatus.PUBLISHED
    # Scheduled
    assert (
        sm.AssignmentFSM.publish(AssignmentStatus.DRAFT, future, now) == AssignmentStatus.SCHEDULED
    )

    # Not draft
    with pytest.raises(sm.IllegalTransitionError, match="Only DRAFT"):
        sm.AssignmentFSM.publish(AssignmentStatus.PUBLISHED, None, now)


def test_assignment_fsm_auto_release_and_close():
    now = datetime.now(UTC)
    past = now - timedelta(hours=1)
    future = now + timedelta(hours=1)

    assert (
        sm.AssignmentFSM.auto_release(AssignmentStatus.SCHEDULED, past, now)
        == AssignmentStatus.PUBLISHED
    )

    with pytest.raises(sm.IllegalTransitionError, match="not yet arrived"):
        sm.AssignmentFSM.auto_release(AssignmentStatus.SCHEDULED, future, now)

    with pytest.raises(sm.IllegalTransitionError, match="Only SCHEDULED"):
        sm.AssignmentFSM.auto_release(AssignmentStatus.DRAFT, past, now)

    assert sm.AssignmentFSM.close(AssignmentStatus.PUBLISHED) == AssignmentStatus.CLOSED
    with pytest.raises(sm.IllegalTransitionError, match="Cannot close"):
        sm.AssignmentFSM.close(AssignmentStatus.DRAFT)


def test_grade_fsm_publish():
    assert sm.GradeFSM.publish(GradeStatus.DRAFT) == GradeStatus.PUBLISHED

    with pytest.raises(sm.IllegalTransitionError, match="Only DRAFT"):
        sm.GradeFSM.publish(GradeStatus.PUBLISHED)


# ==============================================================================
# Rules
# ==============================================================================


def test_rules_is_content_released():
    now = datetime.now(UTC)
    past = now - timedelta(hours=1)
    future = now + timedelta(hours=1)

    assert rules.is_content_released(None, current_time=now) is True
    assert rules.is_content_released(past, current_time=now) is True
    assert rules.is_content_released(future, current_time=now) is False


def test_rules_is_submission_ontime():
    now = datetime.now(UTC)
    due = now + timedelta(days=1)
    past_due = now - timedelta(days=1)

    assert rules.is_submission_ontime(submitted_at=now, due_date=due) is True
    assert rules.is_submission_ontime(submitted_at=now, due_date=past_due) is False


# ==============================================================================
# Calculations
# ==============================================================================


def test_calculations_compute_submission_status():
    now = datetime.now(UTC)
    due = now + timedelta(hours=2)
    past_due = now - timedelta(hours=2)

    assert (
        calculations.compute_submission_status(has_submitted=True, due_date=due, now=now)
        == "SUBMITTED"
    )
    assert (
        calculations.compute_submission_status(has_submitted=False, due_date=due, now=now)
        == "PENDING"
    )
    assert (
        calculations.compute_submission_status(has_submitted=False, due_date=past_due, now=now)
        == "MISSING"
    )


# ==============================================================================
# Validators
# ==============================================================================


def test_validate_material_payload():
    # File valid & invalid
    validators.validate_material_payload(
        material_type=MaterialType.FILE,
        content_text=None,
        external_url=None,
        has_file=True,
    )
    with pytest.raises(validators.DomainValidationError, match="file attachment"):
        validators.validate_material_payload(
            material_type=MaterialType.FILE,
            content_text=None,
            external_url=None,
            has_file=False,
        )

    # Link valid & invalid
    validators.validate_material_payload(
        material_type=MaterialType.LINK,
        content_text=None,
        external_url="https://example.com/lecture",
        has_file=False,
    )
    with pytest.raises(validators.DomainValidationError, match="external_url"):
        validators.validate_material_payload(
            material_type=MaterialType.LINK,
            content_text=None,
            external_url="",
            has_file=False,
        )

    # Note valid & invalid
    validators.validate_material_payload(
        material_type=MaterialType.NOTE,
        content_text="Week 1 review notes",
        external_url=None,
        has_file=False,
    )
    with pytest.raises(validators.DomainValidationError, match="content_text"):
        validators.validate_material_payload(
            material_type=MaterialType.NOTE,
            content_text="  ",
            external_url=None,
            has_file=False,
        )

    # Unknown type
    with pytest.raises(validators.DomainValidationError, match="Invalid material type"):
        validators.validate_material_payload(
            material_type="VIDEO",
            content_text=None,
            external_url=None,
            has_file=False,
        )


def test_validate_assignment_config():
    now = datetime.now(UTC)
    due = now + timedelta(days=7)
    release = now + timedelta(days=1)

    # Valid
    validators.validate_assignment_config(
        title="Assignment 1",
        instructions="Complete questions 1 to 5",
        points_possible=100.0,
        submission_type=SubmissionType.FILE,
        due_date=due,
        release_date=release,
    )

    # Empty title
    with pytest.raises(validators.DomainValidationError, match="title cannot be empty"):
        validators.validate_assignment_config(
            title="",
            instructions="Complete questions",
            points_possible=100,
            submission_type=SubmissionType.FILE,
            due_date=due,
            release_date=release,
        )

    # Non-positive points
    with pytest.raises(validators.DomainValidationError, match="greater than zero"):
        validators.validate_assignment_config(
            title="Assignment 1",
            instructions="Complete questions",
            points_possible=0,
            submission_type=SubmissionType.FILE,
            due_date=due,
            release_date=release,
        )

    # Due date before release date
    with pytest.raises(validators.DomainValidationError, match="after release date"):
        validators.validate_assignment_config(
            title="Assignment 1",
            instructions="Complete questions",
            points_possible=50,
            submission_type=SubmissionType.FILE,
            due_date=release - timedelta(days=1),
            release_date=release,
        )


def test_validate_submission_payload():
    # Valid file
    validators.validate_submission_payload(
        submission_type=SubmissionType.FILE,
        content_text=None,
        content_link=None,
        has_file=True,
    )
    with pytest.raises(validators.DomainValidationError, match="file attachment"):
        validators.validate_submission_payload(
            submission_type=SubmissionType.FILE,
            content_text=None,
            content_link=None,
            has_file=False,
        )

    # Valid link
    validators.validate_submission_payload(
        submission_type=SubmissionType.LINK,
        content_text=None,
        content_link="https://github.com/student/lab",
        has_file=False,
    )
    with pytest.raises(validators.DomainValidationError, match="content_link"):
        validators.validate_submission_payload(
            submission_type=SubmissionType.LINK,
            content_text=None,
            content_link="   ",
            has_file=False,
        )

    # Valid text
    validators.validate_submission_payload(
        submission_type=SubmissionType.TEXT,
        content_text="Solution essay",
        content_link=None,
        has_file=False,
    )
    with pytest.raises(validators.DomainValidationError, match="content_text"):
        validators.validate_submission_payload(
            submission_type=SubmissionType.TEXT,
            content_text="",
            content_link=None,
            has_file=False,
        )


def test_validate_grade_points():
    validators.validate_grade_points(points_awarded=85.5, points_possible=Decimal("100.00"))
    validators.validate_grade_points(points_awarded=0, points_possible=100)

    # Negative points
    with pytest.raises(validators.DomainValidationError, match="cannot be negative"):
        validators.validate_grade_points(points_awarded=-1, points_possible=100)

    # Points exceeding maximum
    with pytest.raises(validators.DomainValidationError, match="cannot exceed points possible"):
        validators.validate_grade_points(points_awarded=105, points_possible=100)


def test_rules_role_authorities_and_release_date():
    from modules.lms.domain.constants import CourseRole

    now = datetime.now(UTC)
    future = now + timedelta(days=2)
    past = now - timedelta(days=2)

    # validate_release_date
    assert rules.validate_release_date(None, now) is True
    assert rules.validate_release_date(future, now) is True
    assert rules.validate_release_date(past, now) is False

    # can_update_course_details
    assert rules.can_update_course_details(CourseRole.INSTRUCTOR) is True
    assert rules.can_update_course_details(CourseRole.TA) is False
    assert rules.can_update_course_details(CourseRole.STUDENT) is False

    # can_post_announcement
    assert rules.can_post_announcement(CourseRole.INSTRUCTOR) is True
    assert rules.can_post_announcement(CourseRole.TA, can_post_flag=True) is True
    assert rules.can_post_announcement(CourseRole.TA, can_post_flag=False) is False
    assert rules.can_post_announcement(CourseRole.STUDENT) is False

    # can_author_assignment
    assert rules.can_author_assignment(CourseRole.INSTRUCTOR) is True
    assert rules.can_author_assignment(CourseRole.TA) is False
    assert rules.can_author_assignment(CourseRole.STUDENT) is False

    # can_author_material
    assert rules.can_author_material(CourseRole.INSTRUCTOR) is True
    assert rules.can_author_material(CourseRole.TA) is False
    assert rules.can_author_material(CourseRole.STUDENT) is False

    # can_manage_workspace
    assert rules.can_manage_workspace(CourseRole.INSTRUCTOR) is True
    assert rules.can_manage_workspace(CourseRole.TA) is False
    assert rules.can_manage_workspace(CourseRole.STUDENT) is False

    # can_grade_submission
    assert rules.can_grade_submission(CourseRole.INSTRUCTOR) is True
    assert rules.can_grade_submission(CourseRole.TA, can_grade_flag=True) is True
    assert rules.can_grade_submission(CourseRole.TA, can_grade_flag=False) is False
    assert rules.can_grade_submission(CourseRole.STUDENT) is False

    # can_release_grades
    assert rules.can_release_grades(CourseRole.INSTRUCTOR) is True
    assert rules.can_release_grades(CourseRole.TA) is False
    assert rules.can_release_grades(CourseRole.STUDENT) is False


def test_state_machine_transition_resolvers():
    # Valid transitions
    t_mat = sm.resolve_material_transition(MaterialStatus.DRAFT, MaterialStatus.PUBLISHED, "INSTRUCTOR")
    assert t_mat.frm == MaterialStatus.DRAFT

    t_asg = sm.resolve_assignment_transition(AssignmentStatus.DRAFT, AssignmentStatus.PUBLISHED, "INSTRUCTOR")
    assert t_asg.frm == AssignmentStatus.DRAFT

    t_grd = sm.resolve_grade_transition(GradeStatus.DRAFT, GradeStatus.PUBLISHED, "INSTRUCTOR")
    assert t_grd.frm == GradeStatus.DRAFT

    # Invalid state transition
    with pytest.raises(sm.IllegalTransitionError):
        sm.resolve_material_transition(MaterialStatus.ARCHIVED, MaterialStatus.DRAFT)

    with pytest.raises(sm.IllegalTransitionError):
        sm.resolve_assignment_transition(AssignmentStatus.ARCHIVED, AssignmentStatus.DRAFT)

    with pytest.raises(sm.IllegalTransitionError):
        sm.resolve_grade_transition(GradeStatus.PUBLISHED, GradeStatus.DRAFT)

    # Actor not allowed
    with pytest.raises(sm.ActorNotAllowedError):
        sm.resolve_material_transition(MaterialStatus.DRAFT, MaterialStatus.PUBLISHED, "STUDENT")

    with pytest.raises(sm.ActorNotAllowedError):
        sm.resolve_assignment_transition(AssignmentStatus.DRAFT, AssignmentStatus.PUBLISHED, "TA")

    with pytest.raises(sm.ActorNotAllowedError):
        sm.resolve_grade_transition(GradeStatus.DRAFT, GradeStatus.PUBLISHED, "TA")


def test_validator_instructions_and_type_failures():
    now = datetime.now(UTC)
    with pytest.raises(validators.DomainValidationError, match="instructions cannot be empty"):
        validators.validate_assignment_config(
            title="Valid Title",
            instructions="",
            points_possible=100,
            submission_type=SubmissionType.FILE,
            due_date=now + timedelta(days=5),
            release_date=None,
        )

    with pytest.raises(validators.DomainValidationError, match="Invalid submission type"):
        validators.validate_assignment_config(
            title="Valid Title",
            instructions="Valid instructions",
            points_possible=100,
            submission_type="UNKNOWN_TYPE",
            due_date=now + timedelta(days=5),
            release_date=None,
        )
