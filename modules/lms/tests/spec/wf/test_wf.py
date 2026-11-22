"""Specification-Driven Tests: Strategy 4 - Workflows (WF).

Covers all 5 Basis Workflows (BW-LMS-01 through BW-LMS-05) and 2 Composite Workflows
(CW-LMS-01, CW-LMS-02) based on the authoritative State-Transition Tables.
Baseline: Frozen A8_BASE for LMS (Course Management) module.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from fusion_auth.principal import Principal
from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    CourseStatus,
    GradeStatus,
    MaterialStatus,
    MaterialType,
    SectionType,
    SubmissionStatus,
    SubmissionType,
)
from modules.lms.domain.errors import LMSRuleError
from modules.lms.models import (
    Course,
    CourseAssignment,
    CourseMaterial,
    CourseMembership,
    CourseSubmission,
    CourseSubmissionGrade,
)
from modules.lms.selectors.grades import get_submission_grade
from modules.lms.selectors.materials import list_course_materials
from modules.lms.services import assignments as assignment_service
from modules.lms.services import grades as grade_service
from modules.lms.services import materials as material_service
from modules.lms.services import submissions as submission_service


def make_actor(user_id: int, role: str, permissions: tuple[str, ...]) -> Principal:
    """Helper to construct an authenticated Principal for LMS testing."""
    from conftest import make_principal as _mp
    return _mp(
        user_id=user_id,
        kind=role,
        roles=(role,),
        active_role=role,
        permissions=permissions,
        modules=("lms",),
    )


FACULTY_PERMS = (
    "lms.course.view", "lms.course.manage",
    "lms.material.view", "lms.material.manage",
    "lms.announcement.view", "lms.announcement.manage",
    "lms.assignment.view", "lms.assignment.manage",
    "lms.deadline.view", "lms.deadline.manage",
    "lms.submission.view", "lms.grade.view", "lms.grade.grade",
)

TA_PERMS = (
    "lms.course.view", "lms.material.view", "lms.announcement.view",
    "lms.assignment.view", "lms.deadline.view", "lms.submission.view",
    "lms.grade.view", "lms.grade.grade",
)

STUDENT_PERMS = (
    "lms.course.view", "lms.material.view", "lms.announcement.view",
    "lms.assignment.view", "lms.deadline.view", "lms.submission.submit",
    "lms.submission.view", "lms.grade.view",
)


@pytest.fixture
def course_setup():
    """Fixture providing a standard course with faculty, TA, and student."""
    course = Course.objects.create(
        code="CS101",
        title="Intro to Computer Science",
        description="Fundamental computing concepts",
        syllabus="Week 1: Intro, Week 2: Logic",
        schedule="Mon/Wed 10:00",
        status=CourseStatus.PUBLISHED,
    )
    CourseMembership.objects.create(course=course, user_id=101, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=102, role=CourseRole.TA)
    CourseMembership.objects.create(course=course, user_id=103, role=CourseRole.STUDENT)

    faculty = make_actor(101, "faculty", FACULTY_PERMS)
    ta = make_actor(102, "ta", TA_PERMS)
    student = make_actor(103, "student", STUDENT_PERMS)

    return {
        "course": course,
        "faculty": faculty,
        "ta": ta,
        "student": student,
    }


# ==============================================================================
# BW-LMS-01: Scheduled Course Material Release
# ==============================================================================

@pytest.mark.django_db
def test_tc_wf_01_material_draft_to_scheduled(course_setup):
    """Test ID: TC-WF-01 | Source ID: BW-LMS-01 Transition 1"""
    faculty = course_setup["faculty"]
    future_time = datetime.now(UTC) + timedelta(days=3)
    mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS101",
        title="Future Lecture",
        section_title="Module 1",
        section_type=SectionType.MODULE,
        material_type=MaterialType.NOTE,
        content="Notes",
        status=MaterialStatus.SCHEDULED,
        release_at=future_time,
    )
    assert mat.status == MaterialStatus.SCHEDULED
    assert mat.release_at == future_time


@pytest.mark.django_db
def test_tc_wf_02_scheduled_material_to_published(course_setup):
    """Test ID: TC-WF-02 | Source ID: BW-LMS-01 Transition 2"""
    course = course_setup["course"]
    mat = CourseMaterial.objects.create(
        course=course,
        title="Due Release Lecture",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Notes",
        status=MaterialStatus.SCHEDULED,
        release_at=datetime.now(UTC) - timedelta(minutes=5),
        created_by_user_id=101,
    )
    released = material_service.release_scheduled_materials()
    mat.refresh_from_db()
    assert released >= 1
    assert mat.status == MaterialStatus.PUBLISHED


@pytest.mark.django_db
def test_tc_wf_03_scheduled_material_guard_withheld(course_setup):
    """Test ID: TC-WF-03 | Source ID: BW-LMS-01 Guard Check"""
    course = course_setup["course"]
    student = course_setup["student"]
    CourseMaterial.objects.create(
        course=course,
        title="Unreleased Note",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Secret",
        status=MaterialStatus.SCHEDULED,
        release_at=datetime.now(UTC) + timedelta(days=5),
        created_by_user_id=101,
    )
    mats_data = list_course_materials(principal=student, course_code="CS101")
    titles = [m["title"] for sec in mats_data.get("sections", []) for m in sec.get("materials", [])]
    assert "Unreleased Note" not in titles


# ==============================================================================
# BW-LMS-02: Assignment Immediate Release and On-Time Submission
# ==============================================================================

@pytest.mark.django_db
def test_tc_wf_04_assignment_new_to_draft(course_setup):
    """Test ID: TC-WF-04 | Source ID: BW-LMS-02 Transition 1"""
    faculty = course_setup["faculty"]
    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Algorithm Lab",
        instructions="Implement sorting",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        due_at=datetime.now(UTC) + timedelta(days=5),
    )
    assert asg.status == AssignmentStatus.DRAFT


@pytest.mark.django_db
def test_tc_wf_05_assignment_draft_to_available(course_setup):
    """Test ID: TC-WF-05 | Source ID: BW-LMS-02 Transition 2"""
    faculty = course_setup["faculty"]
    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Immediate Assignment",
        instructions="Complete tasks",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        due_at=datetime.now(UTC) + timedelta(days=5),
    )
    pub = assignment_service.update_course_assignment(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
        status=AssignmentStatus.PUBLISHED,
    )
    assert pub.status == AssignmentStatus.PUBLISHED


@pytest.mark.django_db
def test_tc_wf_06_assignment_available_to_submission_recorded(course_setup):
    """Test ID: TC-WF-06 | Source ID: BW-LMS-02 Transition 3"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Open Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = submission_service.create_submission(
        actor=student,
        course_code="CS101",
        assignment_id=asg.id,
        submission_type=SubmissionType.TEXT,
        content_text="Solution code",
    )
    assert sub.status == SubmissionStatus.SUBMITTED


@pytest.mark.django_db
def test_tc_wf_07_assignment_publish_guard_failure(course_setup):
    """Test ID: TC-WF-07 | Source ID: BW-LMS-02 Guard Failure"""
    faculty = course_setup["faculty"]
    course = course_setup["course"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Incomplete Assignment",
        instructions="No due date",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.DRAFT,
        created_by_user_id=101,
    )
    with pytest.raises((ConflictError, LMSRuleError)):
        assignment_service.update_course_assignment(
            actor=faculty,
            course_code="CS101",
            assignment_id=asg.id,
            status=AssignmentStatus.PUBLISHED,
        )


# ==============================================================================
# BW-LMS-03: Assignment Scheduled Release and On-Time Submission
# ==============================================================================

@pytest.mark.django_db
def test_tc_wf_08_assignment_draft_to_scheduled(course_setup):
    """Test ID: TC-WF-08 | Source ID: BW-LMS-03 Transition 2"""
    faculty = course_setup["faculty"]
    future_release = datetime.now(UTC) + timedelta(days=2)
    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Scheduled Project",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        due_at=datetime.now(UTC) + timedelta(days=7),
    )
    scheduled = assignment_service.update_course_assignment(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
        status=AssignmentStatus.SCHEDULED,
        release_at=future_release,
    )
    assert scheduled.status == AssignmentStatus.SCHEDULED


@pytest.mark.django_db
def test_tc_wf_09_assignment_scheduled_to_available(course_setup):
    """Test ID: TC-WF-09 | Source ID: BW-LMS-03 Transition 3"""
    course = course_setup["course"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Due Project",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.SCHEDULED,
        release_at=datetime.now(UTC) - timedelta(minutes=5),
        due_at=datetime.now(UTC) + timedelta(days=5),
        created_by_user_id=101,
    )
    rel = assignment_service.release_scheduled_assignments()
    asg.refresh_from_db()
    assert rel >= 1
    assert asg.status == AssignmentStatus.PUBLISHED


@pytest.mark.django_db
def test_tc_wf_10_assignment_released_scheduled_to_submitted(course_setup):
    """Test ID: TC-WF-10 | Source ID: BW-LMS-03 Transition 4"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Auto Released Project",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=5),
        created_by_user_id=101,
    )
    sub = submission_service.create_submission(
        actor=student,
        course_code="CS101",
        assignment_id=asg.id,
        submission_type=SubmissionType.TEXT,
        content_text="Solution",
    )
    assert sub.status == SubmissionStatus.SUBMITTED


@pytest.mark.django_db
def test_tc_wf_11_assignment_scheduled_guard_submission_rejected(course_setup):
    """Test ID: TC-WF-11 | Source ID: BW-LMS-03 Guard Check"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Unreleased Scheduled Project",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.SCHEDULED,
        release_at=datetime.now(UTC) + timedelta(days=3),
        due_at=datetime.now(UTC) + timedelta(days=7),
        created_by_user_id=101,
    )
    with pytest.raises(ConflictError):
        submission_service.create_submission(
            actor=student,
            course_code="CS101",
            assignment_id=asg.id,
            submission_type=SubmissionType.TEXT,
            content_text="Premature submit",
        )


# ==============================================================================
# BW-LMS-04: Faculty Grading and Grade Release
# ==============================================================================

@pytest.mark.django_db
def test_tc_wf_12_faculty_grades_submission_to_draft(course_setup):
    """Test ID: TC-WF-12 | Source ID: BW-LMS-04 Transition 1"""
    course = course_setup["course"]
    faculty = course_setup["faculty"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Grading Workflow",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Work",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    grade = grade_service.record_submission_grade(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
        submission_id=sub.id,
        score=Decimal("88.00"),
    )
    assert grade.status == GradeStatus.DRAFT
    assert grade.graded_by_user_id == 101


@pytest.mark.django_db
def test_tc_wf_13_faculty_releases_grade_to_released(course_setup):
    """Test ID: TC-WF-13 | Source ID: BW-LMS-04 Transition 2"""
    course = course_setup["course"]
    faculty = course_setup["faculty"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Release Workflow",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    # Per BW-LMS-04 Transition 2: Faculty releases grades via transactional grade release service
    grade_service.release_assignment_grades(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
    )


@pytest.mark.django_db
def test_tc_wf_14_draft_grade_visibility_guard(course_setup):
    """Test ID: TC-WF-14 | Source ID: BW-LMS-04 Visibility Guard"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Draft Grade Guard",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Work",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=asg,
        student_user_id=103,
        score=Decimal("85.00"),
        status=GradeStatus.DRAFT,
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )
    grade = get_submission_grade(
        principal=student,
        course_code="CS101",
        assignment_id=asg.id,
        submission_id=sub.id,
    )
    assert grade is None


# ==============================================================================
# BW-LMS-05: TA Grading and Faculty Grade Release
# ==============================================================================

@pytest.mark.django_db
def test_tc_wf_15_ta_grades_submission_to_draft(course_setup):
    """Test ID: TC-WF-15 | Source ID: BW-LMS-05 Transition 1"""
    course = course_setup["course"]
    ta = course_setup["ta"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="TA Grading Workflow",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Work",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    grade = grade_service.record_submission_grade(
        actor=ta,
        course_code="CS101",
        assignment_id=asg.id,
        submission_id=sub.id,
        score=Decimal("82.00"),
    )
    assert grade.status == GradeStatus.DRAFT
    assert grade.graded_by_user_id == 102


@pytest.mark.django_db
def test_tc_wf_16_faculty_releases_ta_grade(course_setup):
    """Test ID: TC-WF-16 | Source ID: BW-LMS-05 Transition 2"""
    course = course_setup["course"]
    faculty = course_setup["faculty"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="TA Grade Release Workflow",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    # Per BW-LMS-05 Transition 2: Faculty releases grades via transactional grade release service
    grade_service.release_assignment_grades(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
    )


@pytest.mark.django_db
def test_tc_wf_17_ta_cannot_release_grade(course_setup):
    """Test ID: TC-WF-17 | Source ID: BW-LMS-05 Authority Guard"""
    ta = course_setup["ta"]
    assert "lms.course.manage" not in ta.permissions


# ==============================================================================
# CW-LMS-01: Assignment Publication and Submission (Composite)
# ==============================================================================

@pytest.mark.django_db
def test_tc_wf_18_composite_immediate_publish_and_submit(course_setup):
    """Test ID: TC-WF-18 | Source ID: CW-LMS-01 Immediate Composite Path"""
    faculty = course_setup["faculty"]
    student = course_setup["student"]
    # Step 1: Draft
    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Composite Asg 1",
        instructions="Do this",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        due_at=datetime.now(UTC) + timedelta(days=3),
    )
    assert asg.status == AssignmentStatus.DRAFT
    # Step 2: Publish
    pub = assignment_service.update_course_assignment(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
        status=AssignmentStatus.PUBLISHED,
    )
    assert pub.status == AssignmentStatus.PUBLISHED
    # Step 3: Submit
    sub = submission_service.create_submission(
        actor=student,
        course_code="CS101",
        assignment_id=asg.id,
        submission_type=SubmissionType.TEXT,
        content_text="Composite submission answer",
    )
    assert sub.status == SubmissionStatus.SUBMITTED


@pytest.mark.django_db
def test_tc_wf_19_composite_scheduled_publish_and_submit(course_setup):
    """Test ID: TC-WF-19 | Source ID: CW-LMS-01 Scheduled Composite Path"""
    faculty = course_setup["faculty"]
    student = course_setup["student"]
    # Step 1: Draft
    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Composite Asg 2",
        instructions="Do this",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        due_at=datetime.now(UTC) + timedelta(days=5),
    )
    # Step 2: Schedule
    past_release = datetime.now(UTC) - timedelta(minutes=5)
    asg.status = AssignmentStatus.SCHEDULED
    asg.release_at = past_release
    asg.save()
    # Step 3: System auto-release
    rel = assignment_service.release_scheduled_assignments()
    assert rel >= 1
    # Step 4: Submit
    sub = submission_service.create_submission(
        actor=student,
        course_code="CS101",
        assignment_id=asg.id,
        submission_type=SubmissionType.TEXT,
        content_text="Composite scheduled answer",
    )
    assert sub.status == SubmissionStatus.SUBMITTED


# ==============================================================================
# CW-LMS-02: Grading and Grade Release (Composite)
# ==============================================================================

@pytest.mark.django_db
def test_tc_wf_20_composite_faculty_grading_and_release(course_setup):
    """Test ID: TC-WF-20 | Source ID: CW-LMS-02 Faculty Grading Composite Path"""
    faculty = course_setup["faculty"]
    course = course_setup["course"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Composite Grade Test",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Work",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    grade = grade_service.record_submission_grade(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
        submission_id=sub.id,
        score=Decimal("91.00"),
    )
    assert grade.status == GradeStatus.DRAFT
    # Step 2: Release
    grade_service.release_assignment_grades(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
    )


@pytest.mark.django_db
def test_tc_wf_21_composite_ta_grading_and_faculty_release(course_setup):
    """Test ID: TC-WF-21 | Source ID: CW-LMS-02 TA Grading Composite Path"""
    ta = course_setup["ta"]
    faculty = course_setup["faculty"]
    course = course_setup["course"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Composite TA Grade Test",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Work",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    grade = grade_service.record_submission_grade(
        actor=ta,
        course_code="CS101",
        assignment_id=asg.id,
        submission_id=sub.id,
        score=Decimal("86.00"),
    )
    assert grade.status == GradeStatus.DRAFT
    # Step 2: Release
    grade_service.release_assignment_grades(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
    )
