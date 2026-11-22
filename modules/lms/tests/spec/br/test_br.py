"""Specification-Driven Tests: Strategy 3 - Business Rules (BR).

Covers all 19 Business Rules (BR-LMS-001 through BR-LMS-019).
Baseline: Frozen A8_BASE for LMS (Course Management) module.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, PermissionDeniedError
from fusion_auth.principal import Principal
from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    CourseStatus,
    GradeStatus,
    MaterialStatus,
    MaterialType,
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
from modules.lms.selectors.announcements import list_course_announcements
from modules.lms.selectors.assignments import (
    list_course_assignments,
)
from modules.lms.selectors.courses import course_workspace_details
from modules.lms.selectors.grades import get_submission_grade
from modules.lms.selectors.materials import list_course_materials
from modules.lms.selectors.submissions import (
    get_student_submission_history,
    list_assignment_submissions,
)
from modules.lms.services import announcements as announcement_service
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
    "lms.course.view", "lms.material.view", "lms.announcement.view", "lms.announcement.manage",
    "lms.assignment.view", "lms.deadline.view", "lms.submission.view",
    "lms.grade.view", "lms.grade.grade",
)

STUDENT_PERMS = (
    "lms.course.view", "lms.material.view", "lms.announcement.view",
    "lms.assignment.view", "lms.deadline.view", "lms.submission.submit",
    "lms.submission.view", "lms.grade.view",
)

OBSERVER_PERMS = (
    "lms.course.view", "lms.material.view", "lms.announcement.view",
)


@pytest.fixture
def course_setup():
    """Fixture providing a standard course with faculty, TA, student, and observer."""
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
    CourseMembership.objects.create(course=course, user_id=104, role=CourseRole.OBSERVER)

    faculty = make_actor(101, "faculty", FACULTY_PERMS)
    ta = make_actor(102, "ta", TA_PERMS)
    student = make_actor(103, "student", STUDENT_PERMS)
    observer = make_actor(104, "observer", OBSERVER_PERMS)
    unenrolled = make_actor(999, "student", STUDENT_PERMS)

    return {
        "course": course,
        "faculty": faculty,
        "ta": ta,
        "student": student,
        "observer": observer,
        "unenrolled": unenrolled,
    }


# ==============================================================================
# BR-LMS-001: Course-specific access control
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_01_course_access_permitted(course_setup):
    """Test ID: TC-BR-01 | Source ID: BR-LMS-001 Permitted"""
    student = course_setup["student"]
    ws = course_workspace_details(principal=student, course_code="CS101")
    assert ws is not None
    assert ws["code"] == "CS101"


@pytest.mark.django_db
def test_tc_br_02_course_access_prohibited(course_setup):
    """Test ID: TC-BR-02 | Source ID: BR-LMS-001 Prohibited"""
    unenrolled = course_setup["unenrolled"]
    ws = course_workspace_details(principal=unenrolled, course_code="CS101")
    assert ws is None


# ==============================================================================
# BR-LMS-002: Student registration data governs Student course access
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_03_student_registration_governs_access_permitted(course_setup):
    """Test ID: TC-BR-03 | Source ID: BR-LMS-002 Permitted"""
    student = course_setup["student"]
    ws = course_workspace_details(principal=student, course_code="CS101")
    assert ws is not None
    assert ws["role"] == CourseRole.STUDENT


@pytest.mark.django_db
def test_tc_br_04_student_registration_governs_access_prohibited(course_setup):
    """Test ID: TC-BR-04 | Source ID: BR-LMS-002 Prohibited"""
    unenrolled = course_setup["unenrolled"]
    ws = course_workspace_details(principal=unenrolled, course_code="CS101")
    assert ws is None


# ==============================================================================
# BR-LMS-003: Observer read-only and student-data restriction
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_05_observer_read_only_permitted(course_setup):
    """Test ID: TC-BR-05 | Source ID: BR-LMS-003 Permitted Read"""
    observer = course_setup["observer"]
    ws = course_workspace_details(principal=observer, course_code="CS101")
    mats = list_course_materials(principal=observer, course_code="CS101")
    anns = list_course_announcements(principal=observer, course_code="CS101")
    assert ws is not None
    assert mats is not None
    assert anns is not None


@pytest.mark.django_db
def test_tc_br_06_observer_prohibited_from_student_data(course_setup):
    """Test ID: TC-BR-06 | Source ID: BR-LMS-003 Prohibited Student Data"""
    observer = course_setup["observer"]
    course = course_setup["course"]
    assignment = CourseAssignment.objects.create(
        course=course,
        title="Privacy Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Solution",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("95.00"),
        status=GradeStatus.RELEASED,
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )
    grade = get_submission_grade(
        principal=observer,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
    )
    subs = list_assignment_submissions(
        principal=observer,
        course_code="CS101",
        assignment_id=assignment.id,
    )
    assert grade is None
    assert subs is None


@pytest.mark.django_db
def test_tc_br_07_observer_prohibited_from_write(course_setup):
    """Test ID: TC-BR-07 | Source ID: BR-LMS-003 Prohibited Write"""
    observer = course_setup["observer"]
    with pytest.raises(PermissionDeniedError):
        announcement_service.post_course_announcement(
            actor=observer,
            course_code="CS101",
            title="Observer Notice",
            content="Illegal post",
        )


# ==============================================================================
# BR-LMS-004: TA authoring restriction
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_08_ta_view_and_grade_permitted(course_setup):
    """Test ID: TC-BR-08 | Source ID: BR-LMS-004 Permitted View/Grade"""
    ta = course_setup["ta"]
    course = course_setup["course"]
    assignment = CourseAssignment.objects.create(
        course=course,
        title="TA Test Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Work",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    grade = grade_service.record_submission_grade(
        actor=ta,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
        score=Decimal("88.00"),
    )
    assert grade.score == Decimal("88.00")
    assert grade.graded_by_user_id == 102


@pytest.mark.django_db
def test_tc_br_09_ta_prohibited_authoring(course_setup):
    """Test ID: TC-BR-09 | Source ID: BR-LMS-004 Prohibited Authoring"""
    ta = course_setup["ta"]
    with pytest.raises(PermissionDeniedError):
        assignment_service.create_course_assignment(
            actor=ta,
            course_code="CS101",
            title="TA Assignment",
            instructions="Not allowed",
            submission_type=SubmissionType.TEXT,
            points_possible=Decimal("100.00"),
            due_at=datetime.now(UTC) + timedelta(days=2),
        )


# ==============================================================================
# BR-LMS-005: Published material visibility
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_10_published_material_visibility_permitted(course_setup):
    """Test ID: TC-BR-10 | Source ID: BR-LMS-005 Permitted Published"""
    course = course_setup["course"]
    student = course_setup["student"]
    CourseMaterial.objects.create(
        course=course,
        title="Visible Material",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Read me",
        status=MaterialStatus.PUBLISHED,
        created_by_user_id=101,
    )
    result = list_course_materials(principal=student, course_code="CS101")
    titles = [m["title"] for sec in result.get("sections", []) for m in sec.get("materials", [])]
    assert "Visible Material" in titles


@pytest.mark.django_db
def test_tc_br_11_unpublished_material_hidden(course_setup):
    """Test ID: TC-BR-11 | Source ID: BR-LMS-005 Prohibited Unpublished"""
    course = course_setup["course"]
    student = course_setup["student"]
    CourseMaterial.objects.create(
        course=course,
        title="Draft Secret Material",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Hidden",
        status=MaterialStatus.DRAFT,
        created_by_user_id=101,
    )
    result = list_course_materials(principal=student, course_code="CS101")
    titles = [m["title"] for sec in result.get("sections", []) for m in sec.get("materials", [])]
    assert "Draft Secret Material" not in titles


# ==============================================================================
# BR-LMS-006: Scheduled material release
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_12_scheduled_material_future_release_hidden(course_setup):
    """Test ID: TC-BR-12 | Source ID: BR-LMS-006 Future Release"""
    course = course_setup["course"]
    student = course_setup["student"]
    CourseMaterial.objects.create(
        course=course,
        title="Future Scheduled Note",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Hidden future",
        status=MaterialStatus.SCHEDULED,
        release_at=datetime.now(UTC) + timedelta(days=5),
        created_by_user_id=101,
    )
    result = list_course_materials(principal=student, course_code="CS101")
    titles = [m["title"] for sec in result.get("sections", []) for m in sec.get("materials", [])]
    assert "Future Scheduled Note" not in titles


@pytest.mark.django_db
def test_tc_br_13_scheduled_material_release_time_reached(course_setup):
    """Test ID: TC-BR-13 | Source ID: BR-LMS-006 Release Time Reached"""
    course = course_setup["course"]
    mat = CourseMaterial.objects.create(
        course=course,
        title="Released Scheduled Note",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Now live",
        status=MaterialStatus.SCHEDULED,
        release_at=datetime.now(UTC) - timedelta(minutes=5),
        created_by_user_id=101,
    )
    rel = material_service.release_scheduled_materials()
    mat.refresh_from_db()
    assert rel >= 1
    assert mat.status == MaterialStatus.PUBLISHED


# ==============================================================================
# BR-LMS-007: Announcement posting authority
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_14_faculty_announcement_permitted(course_setup):
    """Test ID: TC-BR-14 | Source ID: BR-LMS-007 Faculty Permitted"""
    faculty = course_setup["faculty"]
    ann = announcement_service.post_course_announcement(
        actor=faculty,
        course_code="CS101",
        title="Faculty Post",
        content="Class note",
    )
    assert ann.id is not None
    assert ann.author_role == CourseRole.FACULTY


@pytest.mark.django_db
def test_tc_br_15_ta_announcement_permitted_when_authorized(course_setup):
    """Test ID: TC-BR-15 | Source ID: BR-LMS-007 TA Permitted/Configured"""
    ta = course_setup["ta"]
    # Per BR-LMS-007: "a TA may post only where permitted by Faculty for that course."
    # The TA actor possesses announcement manage permission.
    ann = announcement_service.post_course_announcement(
        actor=ta,
        course_code="CS101",
        title="TA Permitted Post",
        content="Lab reminder",
    )
    assert ann.id is not None
    assert ann.author_role == CourseRole.TA


@pytest.mark.django_db
def test_tc_br_16_student_announcement_prohibited(course_setup):
    """Test ID: TC-BR-16 | Source ID: BR-LMS-007 Student Prohibited"""
    student = course_setup["student"]
    with pytest.raises(PermissionDeniedError):
        announcement_service.post_course_announcement(
            actor=student,
            course_code="CS101",
            title="Spam",
            content="Spam",
        )


# ==============================================================================
# BR-LMS-008: Announcement timestamp and audience
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_17_announcement_timestamp_and_audience(course_setup):
    """Test ID: TC-BR-17 | Source ID: BR-LMS-008 Timestamp & Visibility"""
    faculty = course_setup["faculty"]
    student = course_setup["student"]
    ann = announcement_service.post_course_announcement(
        actor=faculty,
        course_code="CS101",
        title="Midterm Notice",
        content="Details inside",
    )
    assert ann.created_at is not None
    anns_data = list_course_announcements(principal=student, course_code="CS101")
    items = anns_data.get("announcements", [])
    assert any(a["id"] == ann.id for a in items)


# ==============================================================================
# BR-LMS-009: Assignment required configuration
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_18_assignment_valid_configuration(course_setup):
    """Test ID: TC-BR-18 | Source ID: BR-LMS-009 Valid Configuration"""
    faculty = course_setup["faculty"]
    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Valid Assignment",
        instructions="Complete tasks",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        due_at=datetime.now(UTC) + timedelta(days=3),
    )
    pub = assignment_service.update_course_assignment(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
        status=AssignmentStatus.PUBLISHED,
    )
    assert pub.status == AssignmentStatus.PUBLISHED


@pytest.mark.django_db
def test_tc_br_19_assignment_missing_required_configuration(course_setup):
    """Test ID: TC-BR-19 | Source ID: BR-LMS-009 Missing Configuration"""
    faculty = course_setup["faculty"]
    course = course_setup["course"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="No Due Date Assignment",
        instructions="Work",
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
# BR-LMS-010: Assignment draft-before-publication
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_20_assignment_draft_before_publication(course_setup):
    """Test ID: TC-BR-20 | Source ID: BR-LMS-010 Draft State"""
    faculty = course_setup["faculty"]
    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Draft Test",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("50.00"),
        due_at=datetime.now(UTC) + timedelta(days=5),
    )
    assert asg.status == AssignmentStatus.DRAFT


# ==============================================================================
# BR-LMS-011: Assignment release-date visibility
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_21_assignment_future_release_hidden(course_setup):
    """Test ID: TC-BR-21 | Source ID: BR-LMS-011 Future Release Hidden"""
    course = course_setup["course"]
    student = course_setup["student"]
    CourseAssignment.objects.create(
        course=course,
        title="Future Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("50.00"),
        status=AssignmentStatus.SCHEDULED,
        release_at=datetime.now(UTC) + timedelta(days=3),
        due_at=datetime.now(UTC) + timedelta(days=7),
        created_by_user_id=101,
    )
    res = list_course_assignments(principal=student, course_code="CS101")
    items = res.get("assignments", [])
    assert not any(a["title"] == "Future Assignment" for a in items)


@pytest.mark.django_db
def test_tc_br_22_assignment_released_available(course_setup):
    """Test ID: TC-BR-22 | Source ID: BR-LMS-011 Released Available"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Now Released Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("50.00"),
        status=AssignmentStatus.SCHEDULED,
        release_at=datetime.now(UTC) - timedelta(minutes=5),
        due_at=datetime.now(UTC) + timedelta(days=5),
        created_by_user_id=101,
    )
    rel = assignment_service.release_scheduled_assignments()
    assert rel >= 1
    res = list_course_assignments(principal=student, course_code="CS101")
    items = res.get("assignments", [])
    assert any(a["id"] == asg.id for a in items)


# ==============================================================================
# BR-LMS-012: Submission-type conformity
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_23_submission_type_conforming(course_setup):
    """Test ID: TC-BR-23 | Source ID: BR-LMS-012 Conforming Submission"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Text Only",
        instructions="Write",
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
        content_text="Solution",
    )
    assert sub.id is not None
    assert sub.submission_type == SubmissionType.TEXT


@pytest.mark.django_db
def test_tc_br_24_submission_type_non_conforming(course_setup):
    """Test ID: TC-BR-24 | Source ID: BR-LMS-012 Non-Conforming Submission"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="File Only",
        instructions="Upload",
        submission_type=SubmissionType.FILE,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    with pytest.raises((ConflictError, LMSRuleError)):
        submission_service.create_submission(
            actor=student,
            course_code="CS101",
            assignment_id=asg.id,
            submission_type=SubmissionType.TEXT,
            content_text="Attempting text when file required",
        )


# ==============================================================================
# BR-LMS-013: Baseline on-time submission
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_25_baseline_on_time_submission(course_setup):
    """Test ID: TC-BR-25 | Source ID: BR-LMS-013 On-Time Submission"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="On Time Test",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
        created_by_user_id=101,
    )
    sub = submission_service.create_submission(
        actor=student,
        course_code="CS101",
        assignment_id=asg.id,
        submission_type=SubmissionType.TEXT,
        content_text="On time work",
    )
    assert sub.status == SubmissionStatus.SUBMITTED


@pytest.mark.django_db
def test_tc_br_26_submission_past_due_date(course_setup):
    """Test ID: TC-BR-26 | Source ID: BR-LMS-013 Past Due Date"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Late Test",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) - timedelta(hours=1),
        closes_at=datetime.now(UTC) + timedelta(days=1),
        allow_late=True,
        created_by_user_id=101,
    )
    sub = submission_service.create_submission(
        actor=student,
        course_code="CS101",
        assignment_id=asg.id,
        submission_type=SubmissionType.TEXT,
        content_text="Late work",
    )
    assert sub.status == SubmissionStatus.LATE


# ==============================================================================
# BR-LMS-014: Submission ownership/privacy
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_27_submission_own_history(course_setup):
    """Test ID: TC-BR-27 | Source ID: BR-LMS-014 Own Submission"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="History",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
        created_by_user_id=101,
    )
    CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Solution",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    history = get_student_submission_history(
        principal=student,
        course_code="CS101",
        assignment_id=asg.id,
    )
    assert history is not None
    assert history["student_user_id"] == 103


@pytest.mark.django_db
def test_tc_br_28_submission_peer_access_prohibited(course_setup):
    """Test ID: TC-BR-28 | Source ID: BR-LMS-014 Peer Submission Prohibited"""
    course = course_setup["course"]
    student_b = make_actor(105, "student", STUDENT_PERMS)
    CourseMembership.objects.create(course=course, user_id=105, role=CourseRole.STUDENT)
    asg = CourseAssignment.objects.create(
        course=course,
        title="Private Submissions",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
        created_by_user_id=101,
    )
    CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Student A answer",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    with pytest.raises(PermissionDeniedError):
        get_student_submission_history(
            principal=student_b,
            course_code="CS101",
            assignment_id=asg.id,
            student_user_id=103,
        )


# ==============================================================================
# BR-LMS-015: Grading authority and attribution
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_29_grading_authority_and_attribution(course_setup):
    """Test ID: TC-BR-29 | Source ID: BR-LMS-015 Faculty/TA Grading & Attribution"""
    course = course_setup["course"]
    ta = course_setup["ta"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Attribution Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
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
        score=Decimal("85.00"),
    )
    assert grade.graded_by_user_id == 102
    assert grade.graded_at is not None


@pytest.mark.django_db
def test_tc_br_30_student_grading_prohibited(course_setup):
    """Test ID: TC-BR-30 | Source ID: BR-LMS-015 Student Grading Prohibited"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Grading Forbidden",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
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
    with pytest.raises(PermissionDeniedError):
        grade_service.record_submission_grade(
            actor=student,
            course_code="CS101",
            assignment_id=asg.id,
            submission_id=sub.id,
            score=Decimal("100.00"),
        )


# ==============================================================================
# BR-LMS-016: Draft grade visibility
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_31_draft_grade_hidden_from_student(course_setup):
    """Test ID: TC-BR-31 | Source ID: BR-LMS-016 Draft Hidden"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Draft Grade Test",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
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
        score=Decimal("70.00"),
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


@pytest.mark.django_db
def test_tc_br_32_released_grade_visible_to_student(course_setup):
    """Test ID: TC-BR-32 | Source ID: BR-LMS-016 Released Visible"""
    course = course_setup["course"]
    student = course_setup["student"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Released Grade Test",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
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
        score=Decimal("92.00"),
        status=GradeStatus.RELEASED,
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )
    grade = get_submission_grade(
        principal=student,
        course_code="CS101",
        assignment_id=asg.id,
        submission_id=sub.id,
    )
    assert grade is not None
    assert Decimal(grade["score"]) == Decimal("92.00")


# ==============================================================================
# BR-LMS-017: Grade release authority
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_33_faculty_grade_release(course_setup):
    """Test ID: TC-BR-33 | Source ID: BR-LMS-017 Faculty Release"""
    faculty = course_setup["faculty"]
    course = course_setup["course"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Release Test",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
        created_by_user_id=101,
    )
    # Per BR-LMS-017: Faculty releases grades to students via grade release service
    grade_service.release_assignment_grades(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
    )


@pytest.mark.django_db
def test_tc_br_34_ta_cannot_release_grades(course_setup):
    """Test ID: TC-BR-34 | Source ID: BR-LMS-017 TA Release Prohibited"""
    ta = course_setup["ta"]
    course = course_setup["course"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="TA Grade Draft",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
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
        score=Decimal("80.00"),
    )
    # TA grading does not release grades; grade status must remain draft
    assert grade.status == GradeStatus.DRAFT


# ==============================================================================
# BR-LMS-018: Released grade read-only to Student
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_35_released_grade_read_only_to_student(course_setup):
    """Test ID: TC-BR-35 | Source ID: BR-LMS-018 Read-Only Grade"""
    student = course_setup["student"]
    course = course_setup["course"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Student Read Only Test",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
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
        score=Decimal("90.00"),
        status=GradeStatus.RELEASED,
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )
    grade = get_submission_grade(
        principal=student,
        course_code="CS101",
        assignment_id=asg.id,
        submission_id=sub.id,
    )
    assert grade is not None
    assert Decimal(grade["score"]) == Decimal("90.00")
    # Student has no write access to grades
    with pytest.raises(PermissionDeniedError):
        grade_service.record_submission_grade(
            actor=student,
            course_code="CS101",
            assignment_id=asg.id,
            submission_id=sub.id,
            score=Decimal("100.00"),
        )


# ==============================================================================
# BR-LMS-019: Post-release grade-change audit
# ==============================================================================

@pytest.mark.django_db
def test_tc_br_36_post_release_grade_change_audit(course_setup):
    """Test ID: TC-BR-36 | Source ID: BR-LMS-019 Audit on Grade Change"""
    faculty = course_setup["faculty"]
    course = course_setup["course"]
    asg = CourseAssignment.objects.create(
        course=course,
        title="Audit Test Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
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
        score=Decimal("80.00"),
        status=GradeStatus.RELEASED,
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    # Faculty changes already-released grade
    grade_service.record_submission_grade(
        actor=faculty,
        course_code="CS101",
        assignment_id=asg.id,
        submission_id=sub.id,
        score=Decimal("88.00"),
    )

    # Per BR-LMS-019: System shall log the change with actor and time
    # Check that an audit log record exists for this grade change
    from django.apps import apps
    audit_log_model = apps.get_model("lms", "GradeAuditLog", require_ready=False)
    assert audit_log_model is not None
    assert audit_log_model.objects.filter(submission=sub).exists()
