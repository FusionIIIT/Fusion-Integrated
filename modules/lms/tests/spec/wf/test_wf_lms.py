"""WF Strategy Executable Test Suite (Workflows: Basis & Composite Workflows).

Every test contains its test_id and source_id.
Target: modules.lms
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    GradeStatus,
    MaterialStatus,
    SubmissionStatus,
    SubmissionType,
)
from modules.lms.domain.errors import (
    InvalidAssignmentState,
    UnauthorizedGradingError,
)
from modules.lms.models import (
    Assignment,
    CourseMembership,
    CourseWorkspace,
    Grade,
    StudentSubmission,
)
from modules.lms.selectors import courses as selectors
from modules.lms.services import courses as services

pytestmark = pytest.mark.django_db


@pytest.fixture
def course():
    ws = CourseWorkspace.objects.create(
        course_code="CS401",
        title="Compilers",
        syllabus="Lexing and Parsing",
        schedule="Fri 2:00 PM",
        instructor_user_id=9004,
        is_active=True,
    )
    CourseMembership.objects.create(course=ws, user_id=9004, role=CourseRole.FACULTY.value)
    CourseMembership.objects.create(course=ws, user_id=2004, role=CourseRole.STUDENT.value)
    CourseMembership.objects.create(
        course=ws, user_id=3004, role=CourseRole.TA.value, can_post_announcements=True
    )
    CourseMembership.objects.create(course=ws, user_id=4004, role=CourseRole.OBSERVER.value)
    return ws


def test_wf_test_001_bw_lms_01_scheduled_material_released(course):
    """WF-TEST-001 | BW-LMS-01 path-released | Material Draft -> Scheduled -> Published when release date arrives."""
    m = services.upload_course_material(
        course_id=course.id,
        user_id=9004,
        user_role=CourseRole.FACULTY.value,
        title="Lexer Slides",
        is_scheduled=True,
        scheduled_release_at=timezone.now() - timedelta(minutes=5),
    )
    assert m.status == MaterialStatus.SCHEDULED.value
    mats = selectors.get_course_materials(course.id, CourseRole.STUDENT.value)
    assert any(x.id == m.id for x in mats)


def test_wf_test_002_bw_lms_01_scheduled_material_pending(course):
    """WF-TEST-002 | BW-LMS-01 path-pending | Scheduled material time not reached -> Remains Scheduled and hidden."""
    m = services.upload_course_material(
        course_id=course.id,
        user_id=9004,
        user_role=CourseRole.FACULTY.value,
        title="Parser Slides",
        is_scheduled=True,
        scheduled_release_at=timezone.now() + timedelta(days=2),
    )
    assert m.status == MaterialStatus.SCHEDULED.value
    mats = selectors.get_course_materials(course.id, CourseRole.STUDENT.value)
    assert not any(x.id == m.id for x in mats)


def test_wf_test_003_bw_lms_02_immediate_release_on_time_submission(course):
    """WF-TEST-003 | BW-LMS-02 path-immediate-on-time | Draft -> Available -> On-Time Submission -> Status Submitted."""
    asgn = services.create_assignment(
        course_id=course.id,
        user_id=9004,
        user_role=CourseRole.FACULTY.value,
        title="AST Assignment",
        instructions="Build AST",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=timezone.now() + timedelta(days=5),
    )
    assert asgn.status == AssignmentStatus.DRAFT.value
    pub = services.publish_assignment(
        assignment_id=asgn.id, user_role=CourseRole.FACULTY.value, is_scheduled=False
    )
    assert pub.status == AssignmentStatus.AVAILABLE.value

    sub = services.submit_assignment(
        assignment_id=pub.id,
        student_user_id=2004,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="AST code",
    )
    assert sub.status == SubmissionStatus.SUBMITTED.value


def test_wf_test_004_bw_lms_02_immediate_release_late_submission(course):
    """WF-TEST-004 | BW-LMS-02 path-late-submission | Draft -> Available -> Submission after due date -> Status Late."""
    asgn = Assignment.objects.create(
        course=course,
        title="Past HW",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=timezone.now() - timedelta(hours=3),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9004,
    )
    sub = services.submit_assignment(
        assignment_id=asgn.id,
        student_user_id=2004,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="Late AST code",
    )
    assert sub.status == SubmissionStatus.LATE.value


def test_wf_test_005_bw_lms_03_scheduled_release_on_time_submission(course):
    """WF-TEST-005 | BW-LMS-03 path-scheduled-on-time | Draft -> Scheduled -> Release event -> Available -> On-Time Submission."""
    asgn = services.create_assignment(
        course_id=course.id,
        user_id=9004,
        user_role=CourseRole.FACULTY.value,
        title="Typechecker HW",
        instructions="Build Typechecker",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=timezone.now() + timedelta(days=7),
    )
    rel = timezone.now() - timedelta(minutes=5)
    pub = services.publish_assignment(
        assignment_id=asgn.id,
        user_role=CourseRole.FACULTY.value,
        is_scheduled=True,
        release_date=rel,
    )
    assert pub.status == AssignmentStatus.SCHEDULED.value

    sub = services.submit_assignment(
        assignment_id=pub.id,
        student_user_id=2004,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="Typechecker code",
    )
    assert sub.status == SubmissionStatus.SUBMITTED.value


def test_wf_test_006_bw_lms_03_blocked_before_release(course):
    """WF-TEST-006 | BW-LMS-03 path-blocked-before-release | Attempt to submit to scheduled assignment before release date."""
    asgn = services.create_assignment(
        course_id=course.id,
        user_id=9004,
        user_role=CourseRole.FACULTY.value,
        title="Unreleased HW",
        instructions="Wait",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=timezone.now() + timedelta(days=10),
    )
    rel = timezone.now() + timedelta(days=2)
    pub = services.publish_assignment(
        assignment_id=asgn.id,
        user_role=CourseRole.FACULTY.value,
        is_scheduled=True,
        release_date=rel,
    )
    with pytest.raises(InvalidAssignmentState):
        services.submit_assignment(
            assignment_id=pub.id,
            student_user_id=2004,
            student_role=CourseRole.STUDENT.value,
            submission_type=SubmissionType.TEXT.value,
            submission_content="Early code",
        )


def test_wf_test_007_bw_lms_04_faculty_grading_and_release(course):
    """WF-TEST-007 | BW-LMS-04 path-faculty-grade-release | Submission -> Faculty evaluates -> Draft Grade -> Faculty releases -> Released."""
    asgn = Assignment.objects.create(
        course=course,
        title="Grading Flow HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9004,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2004,
        submission_type="text",
        submission_content="Solution",
        status=SubmissionStatus.SUBMITTED.value,
    )
    # 1. Faculty evaluates -> Draft Grade
    g = services.grade_submission(
        submission_id=sub.id,
        grader_user_id=9004,
        grader_role=CourseRole.FACULTY.value,
        points=Decimal("95.00"),
        feedback="Excellent work",
    )
    assert g.status == GradeStatus.DRAFT.value
    assert len(selectors.get_student_course_grades(course.id, 2004)) == 0

    # 2. Faculty releases grades
    count = services.release_assignment_grades(
        assignment_id=asgn.id, releaser_user_id=9004, releaser_role=CourseRole.FACULTY.value
    )
    assert count == 1
    grades = selectors.get_student_course_grades(course.id, 2004)
    assert len(grades) == 1
    assert grades[0].points == Decimal("95.00")


def test_wf_test_008_bw_lms_04_grade_hold(course):
    """WF-TEST-008 | BW-LMS-04 path-grade-hold | Draft grade held and not released -> Hidden from student."""
    asgn = Assignment.objects.create(
        course=course,
        title="Hold HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9004,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2004,
        submission_type="text",
        submission_content="Solution",
        status=SubmissionStatus.SUBMITTED.value,
    )
    services.grade_submission(
        submission_id=sub.id,
        grader_user_id=9004,
        grader_role=CourseRole.FACULTY.value,
        points=Decimal("91.00"),
        feedback="Draft comments",
    )
    assert len(selectors.get_student_course_grades(course.id, 2004)) == 0


def test_wf_test_009_bw_lms_05_ta_grading_faculty_release(course):
    """WF-TEST-009 | BW-LMS-05 path-ta-grading-faculty-release | TA grades (attributed to TA) -> Faculty releases."""
    asgn = Assignment.objects.create(
        course=course,
        title="TA Grade Flow HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9004,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2004,
        submission_type="text",
        submission_content="Solution",
        status=SubmissionStatus.SUBMITTED.value,
    )
    # TA grades
    g = services.grade_submission(
        submission_id=sub.id,
        grader_user_id=3004,
        grader_role=CourseRole.TA.value,
        points=Decimal("88.00"),
        feedback="TA review",
    )
    assert g.graded_by_user_id == 3004
    assert g.status == GradeStatus.DRAFT.value

    # Faculty releases
    count = services.release_assignment_grades(
        assignment_id=asgn.id, releaser_user_id=9004, releaser_role=CourseRole.FACULTY.value
    )
    assert count == 1
    grade = Grade.objects.get(id=g.id)
    assert grade.status == GradeStatus.RELEASED.value
    assert grade.graded_by_user_id == 3004
    assert grade.released_by_user_id == 9004


def test_wf_test_010_bw_lms_05_ta_release_rejected(course):
    """WF-TEST-010 | BW-LMS-05 path-ta-release-rejected | TA attempts release -> Rejected -> Grade remains Draft."""
    asgn = Assignment.objects.create(
        course=course,
        title="Reject Rel HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9004,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2004,
        submission_type="text",
        submission_content="Solution",
        status=SubmissionStatus.SUBMITTED.value,
    )
    g = Grade.objects.create(
        submission=sub,
        points=Decimal("85.00"),
        status=GradeStatus.DRAFT.value,
        graded_by_user_id=3004,
    )
    with pytest.raises(UnauthorizedGradingError):
        services.release_assignment_grades(
            assignment_id=asgn.id, releaser_user_id=3004, releaser_role=CourseRole.TA.value
        )
    g.refresh_from_db()
    assert g.status == GradeStatus.DRAFT.value


def test_wf_test_011_cw_lms_01_composite_publication_submission(course):
    """WF-TEST-011 | CW-LMS-01 composite-publication-submission | Create -> Schedule -> Immediate Publish -> Submit -> State validation."""
    # Step 1: Faculty creates assignment
    asgn = services.create_assignment(
        course_id=course.id,
        user_id=9004,
        user_role=CourseRole.FACULTY.value,
        title="Composite HW",
        instructions="Build full compiler",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=timezone.now() + timedelta(days=10),
    )
    assert asgn.status == AssignmentStatus.DRAFT.value

    # Step 2: Faculty publishes immediately
    pub = services.publish_assignment(
        assignment_id=asgn.id, user_role=CourseRole.FACULTY.value, is_scheduled=False
    )
    assert pub.status == AssignmentStatus.AVAILABLE.value

    # Step 3: Student fetches assignments and submits
    student_asgns = selectors.get_course_assignments(course.id, CourseRole.STUDENT.value)
    assert any(a.id == pub.id for a in student_asgns)

    sub = services.submit_assignment(
        assignment_id=pub.id,
        student_user_id=2004,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="Compiler submission",
    )
    assert sub.status == SubmissionStatus.SUBMITTED.value


def test_wf_test_012_cw_lms_02_composite_grading_release_audit(course):
    """WF-TEST-012 | CW-LMS-02 composite-grading-release-audit | Submission -> TA Grading -> Faculty Release -> Post-Release Modification -> Audit Log."""
    asgn = Assignment.objects.create(
        course=course,
        title="Full Eval HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9004,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2004,
        submission_type="text",
        submission_content="Compiler code",
        status=SubmissionStatus.SUBMITTED.value,
    )
    # 1. TA grades
    g = services.grade_submission(
        submission_id=sub.id,
        grader_user_id=3004,
        grader_role=CourseRole.TA.value,
        points=Decimal("80.00"),
        feedback="TA initial score",
    )
    assert g.status == GradeStatus.DRAFT.value

    # 2. Faculty releases
    count = services.release_assignment_grades(
        assignment_id=asgn.id, releaser_user_id=9004, releaser_role=CourseRole.FACULTY.value
    )
    assert count == 1
    g.refresh_from_db()
    assert g.status == GradeStatus.RELEASED.value

    # 3. Faculty modifies released grade with audit reason
    services.modify_released_grade(
        grade_id=g.id,
        modifier_user_id=9004,
        modifier_role=CourseRole.FACULTY.value,
        new_points=Decimal("92.00"),
        reason="Re-evaluated parsing algorithm",
    )
    g.refresh_from_db()
    assert g.points == Decimal("92.00")

    # 4. Audit log verification
    logs = selectors.get_grade_change_logs(g.id)
    assert len(logs) == 1
    assert logs[0].old_points == Decimal("80.00")
    assert logs[0].new_points == Decimal("92.00")
    assert logs[0].reason == "Re-evaluated parsing algorithm"
    assert logs[0].changed_by_user_id == 9004
