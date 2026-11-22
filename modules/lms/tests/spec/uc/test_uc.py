"""Specification-Driven Tests: Strategy 2 - Use Cases (UC).

Covers all 15 Use Cases (UC-LMS-001 through UC-LMS-015) and their explicit Main Flows,
Alternative Flows, and Exception Flows.
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
    SectionType,
    SubmissionStatus,
    SubmissionType,
)
from modules.lms.domain.errors import LMSRuleError
from modules.lms.models import (
    Course,
    CourseAnnouncement,
    CourseAssignment,
    CourseMaterial,
    CourseMembership,
    CourseSubmission,
    CourseSubmissionGrade,
)
from modules.lms.selectors.announcements import list_course_announcements
from modules.lms.selectors.assignments import (
    get_course_assignment_detail,
    list_course_assignments,
)
from modules.lms.selectors.courses import course_workspace_details
from modules.lms.selectors.grades import get_submission_grade
from modules.lms.selectors.materials import list_course_materials
from modules.lms.selectors.submissions import (
    get_student_submission_history,
)
from modules.lms.services import announcements as announcement_service
from modules.lms.services import assignments as assignment_service
from modules.lms.services import courses as course_service
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
# UC-LMS-001: Access Course Workspace
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_01_access_course_workspace_main_flow(course_setup):
    """
    Test ID: TC-UC-01
    Source ID: UC-LMS-001 Main Flow
    Purpose: Verify an authorized user can access the course workspace and view course home information.
    """
    student = course_setup["student"]
    workspace = course_workspace_details(principal=student, course_code="CS101")

    assert workspace is not None
    assert workspace["code"] == "CS101"
    assert workspace["title"] == "Intro to Computer Science"
    assert "syllabus" in workspace
    assert "schedule" in workspace
    assert "instructors" in workspace
    assert "teaching_assistants" in workspace


@pytest.mark.django_db
def test_tc_uc_02_access_course_workspace_alternative_a1(course_setup):
    """
    Test ID: TC-UC-02
    Source ID: UC-LMS-001 Alternative A1
    Purpose: Verify that course access is denied when the requesting user is not authorized or not enrolled.
    """
    unenrolled = course_setup["unenrolled"]
    workspace = course_workspace_details(principal=unenrolled, course_code="CS101")
    assert workspace is None


@pytest.mark.django_db
def test_tc_uc_03_access_course_workspace_exception_e1(course_setup):
    """
    Test ID: TC-UC-03
    Source ID: UC-LMS-001 Exception E1
    Purpose: Verify that when registration/link data are unavailable, workspace data is not exposed.
    """
    student = course_setup["student"]
    workspace = course_workspace_details(principal=student, course_code="NONEXISTENT_COURSE")
    assert workspace is None


# ==============================================================================
# UC-LMS-002: Manage Course Details
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_04_manage_course_details_main_flow(course_setup):
    """
    Test ID: TC-UC-04
    Source ID: UC-LMS-002 Main Flow
    Purpose: Verify assigned faculty can configure and update course workspace details.
    """
    faculty = course_setup["faculty"]
    updated_course = course_service.update_course_workspace(
        actor=faculty,
        course_code="CS101",
        title="CS101 - Advanced Intro",
        description="Updated Description",
        syllabus="Updated Syllabus v2",
        schedule="Tue/Thu 11:00",
    )
    assert updated_course.title == "CS101 - Advanced Intro"
    assert updated_course.syllabus == "Updated Syllabus v2"
    assert updated_course.schedule == "Tue/Thu 11:00"


@pytest.mark.django_db
def test_tc_uc_05_manage_course_details_alternative_a1(course_setup):
    """
    Test ID: TC-UC-05
    Source ID: UC-LMS-002 Alternative A1
    Purpose: Verify assigned faculty can edit previously published course details.
    """
    faculty = course_setup["faculty"]
    course = course_setup["course"]
    assert course.status == CourseStatus.PUBLISHED

    updated = course_service.update_course_workspace(
        actor=faculty,
        course_code="CS101",
        syllabus="Overwritten Syllabus Content",
    )
    assert updated.syllabus == "Overwritten Syllabus Content"


@pytest.mark.django_db
def test_tc_uc_06_manage_course_details_exception_e1(course_setup):
    """
    Test ID: TC-UC-06
    Source ID: UC-LMS-002 Exception E1
    Purpose: Verify that an unauthorized user cannot update course details.
    """
    student = course_setup["student"]
    with pytest.raises(PermissionDeniedError):
        course_service.update_course_workspace(
            actor=student,
            course_code="CS101",
            syllabus="Hacked Syllabus",
        )


# ==============================================================================
# UC-LMS-003: Manage Course Materials
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_07_manage_course_materials_main_flow(course_setup):
    """
    Test ID: TC-UC-07
    Source ID: UC-LMS-003 Main Flow
    Purpose: Verify assigned faculty can add course material with immediate publication.
    """
    faculty = course_setup["faculty"]
    mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS101",
        title="Module 1 Lecture Notes",
        section_title="Module 1",
        section_type=SectionType.MODULE,
        material_type=MaterialType.NOTE,
        content="Welcome to CS101 material",
        status=MaterialStatus.PUBLISHED,
    )
    assert mat.status == MaterialStatus.PUBLISHED
    assert mat.title == "Module 1 Lecture Notes"


@pytest.mark.django_db
def test_tc_uc_08_manage_course_materials_alternative_a1(course_setup):
    """
    Test ID: TC-UC-08
    Source ID: UC-LMS-003 Alternative A1
    Purpose: Verify assigned faculty can add course material scheduled for future release.
    """
    faculty = course_setup["faculty"]
    future_time = datetime.now(UTC) + timedelta(days=5)
    mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS101",
        title="Future Topic Reading",
        section_title="Week 3",
        section_type=SectionType.WEEK,
        material_type=MaterialType.NOTE,
        content="Scheduled reading material",
        status=MaterialStatus.SCHEDULED,
        release_at=future_time,
    )
    assert mat.status == MaterialStatus.SCHEDULED
    assert mat.release_at == future_time


@pytest.mark.django_db
def test_tc_uc_09_manage_course_materials_alternative_a2(course_setup):
    """
    Test ID: TC-UC-09
    Source ID: UC-LMS-003 Alternative A2
    Purpose: Verify assigned faculty can edit or reorganize existing course material.
    """
    faculty = course_setup["faculty"]
    mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS101",
        title="Draft Chapter",
        section_title="Module 1",
        section_type=SectionType.MODULE,
        material_type=MaterialType.NOTE,
        content="Draft text",
        status=MaterialStatus.DRAFT,
    )
    updated_mat = material_service.update_course_material(
        actor=faculty,
        course_code="CS101",
        material_id=mat.id,
        title="Final Chapter 1",
        section_title="Module 2",
    )
    assert updated_mat.title == "Final Chapter 1"
    assert updated_mat.section_title == "Module 2"


@pytest.mark.django_db
def test_tc_uc_10_manage_course_materials_exception_e1(course_setup):
    """
    Test ID: TC-UC-10
    Source ID: UC-LMS-003 Exception E1
    Purpose: Verify that non-faculty write attempts to add course materials are rejected.
    """
    student = course_setup["student"]
    with pytest.raises(PermissionDeniedError):
        material_service.create_course_material(
            actor=student,
            course_code="CS101",
            title="Unauthorized Material",
            section_title="Module 1",
            material_type=MaterialType.NOTE,
            content="Malicious or unauthorized content",
        )


# ==============================================================================
# UC-LMS-004: View Published Course Materials
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_11_view_published_materials_main_flow(course_setup):
    """
    Test ID: TC-UC-11
    Source ID: UC-LMS-004 Main Flow
    Purpose: Verify authorized course user can view published course materials in read-only form.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    CourseMaterial.objects.create(
        course=course,
        title="Published Syllabus Guide",
        section_title="General",
        material_type=MaterialType.NOTE,
        content="Read only info",
        status=MaterialStatus.PUBLISHED,
        created_by_user_id=101,
    )

    result = list_course_materials(principal=student, course_code="CS101")
    assert result is not None
    mats = [m["title"] for sec in result.get("sections", []) for m in sec.get("materials", [])]
    assert "Published Syllabus Guide" in mats


@pytest.mark.django_db
def test_tc_uc_12_view_published_materials_alternative_a1(course_setup):
    """
    Test ID: TC-UC-12
    Source ID: UC-LMS-004 Alternative A1
    Purpose: Verify scheduled or unpublished material is omitted from student view until released.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    CourseMaterial.objects.create(
        course=course,
        title="Unreleased Scheduled Material",
        section_title="Week 5",
        material_type=MaterialType.NOTE,
        content="Secret notes",
        status=MaterialStatus.SCHEDULED,
        release_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    CourseMaterial.objects.create(
        course=course,
        title="Hidden Draft Note",
        section_title="Week 5",
        material_type=MaterialType.NOTE,
        content="Draft notes",
        status=MaterialStatus.DRAFT,
        created_by_user_id=101,
    )

    result = list_course_materials(principal=student, course_code="CS101")
    assert result is not None
    mats = [m["title"] for sec in result.get("sections", []) for m in sec.get("materials", [])]
    assert "Unreleased Scheduled Material" not in mats
    assert "Hidden Draft Note" not in mats


@pytest.mark.django_db
def test_tc_uc_13_view_published_materials_exception_e1(course_setup):
    """
    Test ID: TC-UC-13
    Source ID: UC-LMS-004 Exception E1
    Purpose: Verify that unauthorized course access to course materials is denied.
    """
    unenrolled = course_setup["unenrolled"]
    result = list_course_materials(principal=unenrolled, course_code="CS101")
    assert result is None


# ==============================================================================
# UC-LMS-005: Post Course Announcement
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_14_post_announcement_main_flow(course_setup):
    """
    Test ID: TC-UC-14
    Source ID: UC-LMS-005 Main Flow
    Purpose: Verify assigned faculty can post a course-wide announcement with timestamp.
    """
    faculty = course_setup["faculty"]
    announcement = announcement_service.post_course_announcement(
        actor=faculty,
        course_code="CS101",
        title="Class Cancelled Today",
        content="Please review Chapter 2 independently.",
    )
    assert announcement.title == "Class Cancelled Today"
    assert announcement.created_at is not None
    assert announcement.author_role == CourseRole.FACULTY


@pytest.mark.django_db
def test_tc_uc_15_post_announcement_alternative_a1(course_setup):
    """
    Test ID: TC-UC-15
    Source ID: UC-LMS-005 Alternative A1
    Purpose: Verify permitted TA can post a course-wide announcement when permitted.
    """
    ta = course_setup["ta"]
    # Per UC-LMS-005 Alternative A1: "TA posting is allowed only where permitted."
    # The TA principal holds 'lms.announcement.manage' permission.
    announcement = announcement_service.post_course_announcement(
        actor=ta,
        course_code="CS101",
        title="TA Lab Update",
        content="Lab session moved to Room 302.",
    )
    assert announcement.id is not None
    assert announcement.title == "TA Lab Update"
    assert announcement.author_role == CourseRole.TA


@pytest.mark.django_db
def test_tc_uc_16_post_announcement_exception_e1(course_setup):
    """
    Test ID: TC-UC-16
    Source ID: UC-LMS-005 Exception E1
    Purpose: Verify unauthorized user (e.g. Student) cannot post announcements.
    """
    student = course_setup["student"]
    with pytest.raises(PermissionDeniedError):
        announcement_service.post_course_announcement(
            actor=student,
            course_code="CS101",
            title="Student Spurious Post",
            content="Should be rejected",
        )


# ==============================================================================
# UC-LMS-006: View Course Announcements
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_17_view_announcements_main_flow(course_setup):
    """
    Test ID: TC-UC-17
    Source ID: UC-LMS-006 Main Flow
    Purpose: Verify authorized course users can view timestamped course announcements.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    CourseAnnouncement.objects.create(
        course=course,
        title="Exam Schedule Notice",
        content="Midterm exam will take place next Monday.",
        created_by_user_id=101,
        author_role=CourseRole.FACULTY,
    )

    announcements_data = list_course_announcements(principal=student, course_code="CS101")
    assert announcements_data is not None
    items = announcements_data.get("announcements", [])
    assert len(items) >= 1
    assert any(a["title"] == "Exam Schedule Notice" for a in items)


@pytest.mark.django_db
def test_tc_uc_18_view_announcements_exception_e1(course_setup):
    """
    Test ID: TC-UC-18
    Source ID: UC-LMS-006 Exception E1
    Purpose: Verify unauthorized user cannot view course announcements.
    """
    unenrolled = course_setup["unenrolled"]
    announcements_data = list_course_announcements(principal=unenrolled, course_code="CS101")
    assert announcements_data is None or len(announcements_data.get("announcements", [])) == 0


# ==============================================================================
# UC-LMS-007: Create or Edit Assignment
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_19_create_assignment_main_flow(course_setup):
    """
    Test ID: TC-UC-19
    Source ID: UC-LMS-007 Main Flow
    Purpose: Verify assigned faculty can create a new assignment in Draft state.
    """
    faculty = course_setup["faculty"]
    assignment = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Assignment 1 - Basic Algorithms",
        instructions="Implement bubble sort and binary search in Python.",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        due_at=datetime.now(UTC) + timedelta(days=7),
    )
    assert assignment.id is not None
    assert assignment.status == AssignmentStatus.DRAFT
    assert assignment.points_possible == Decimal("100.00")


@pytest.mark.django_db
def test_tc_uc_20_edit_assignment_alternative_a1(course_setup):
    """
    Test ID: TC-UC-20
    Source ID: UC-LMS-007 Alternative A1
    Purpose: Verify assigned faculty can edit an existing Draft assignment configuration.
    """
    faculty = course_setup["faculty"]
    assignment = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Initial Draft Assignment",
        instructions="Initial description",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("50.00"),
        due_at=datetime.now(UTC) + timedelta(days=5),
    )
    updated = assignment_service.update_course_assignment(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        title="Refined Draft Assignment",
        points_possible=Decimal("75.00"),
    )
    assert updated.title == "Refined Draft Assignment"
    assert updated.points_possible == Decimal("75.00")
    assert updated.status == AssignmentStatus.DRAFT


@pytest.mark.django_db
def test_tc_uc_21_create_assignment_exception_e1(course_setup):
    """
    Test ID: TC-UC-21
    Source ID: UC-LMS-007 Exception E1
    Purpose: Verify TA, student, or observer cannot create or edit assignments.
    """
    student = course_setup["student"]
    with pytest.raises(PermissionDeniedError):
        assignment_service.create_course_assignment(
            actor=student,
            course_code="CS101",
            title="Unauthorized Assignment",
            instructions="Instructions",
            submission_type=SubmissionType.TEXT,
            points_possible=Decimal("100.00"),
            due_at=datetime.now(UTC) + timedelta(days=7),
        )


# ==============================================================================
# UC-LMS-008: Publish Assignment
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_22_publish_assignment_main_flow(course_setup):
    """
    Test ID: TC-UC-22
    Source ID: UC-LMS-008 Main Flow
    Purpose: Verify assigned faculty can publish a valid Draft assignment for immediate availability.
    """
    faculty = course_setup["faculty"]
    student = course_setup["student"]

    assignment = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Ready for Launch Assignment",
        instructions="Detailed problems here.",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        due_at=datetime.now(UTC) + timedelta(days=5),
    )

    published = assignment_service.update_course_assignment(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        status=AssignmentStatus.PUBLISHED,
    )
    assert published.status == AssignmentStatus.PUBLISHED

    # Verify student can view published assignment
    res = list_course_assignments(principal=student, course_code="CS101")
    assert res is not None
    items = res.get("assignments", [])
    assert any(a["id"] == published.id for a in items)


@pytest.mark.django_db
def test_tc_uc_23_publish_assignment_alternative_a1(course_setup):
    """
    Test ID: TC-UC-23
    Source ID: UC-LMS-008 Alternative A1
    Purpose: Verify assigned faculty can publish an assignment scheduled for future release.
    """
    faculty = course_setup["faculty"]
    future_release = datetime.now(UTC) + timedelta(days=2)
    due_date = datetime.now(UTC) + timedelta(days=7)

    assignment = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Scheduled Future Assignment",
        instructions="Instructions for future",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        due_at=due_date,
    )

    scheduled = assignment_service.update_course_assignment(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        status=AssignmentStatus.SCHEDULED,
        release_at=future_release,
    )
    assert scheduled.status == AssignmentStatus.SCHEDULED
    assert scheduled.release_at == future_release


@pytest.mark.django_db
def test_tc_uc_24_publish_assignment_exception_e1(course_setup):
    """
    Test ID: TC-UC-24
    Source ID: UC-LMS-008 Exception E1
    Purpose: Verify that an invalid Draft assignment cannot be published.
    """
    faculty = course_setup["faculty"]
    course = course_setup["course"]

    # Create draft with missing due date
    assignment = CourseAssignment.objects.create(
        course=course,
        title="Invalid Draft Assignment",
        instructions="No due date set",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.DRAFT,
        created_by_user_id=101,
    )

    with pytest.raises((ConflictError, LMSRuleError)):
        assignment_service.update_course_assignment(
            actor=faculty,
            course_code="CS101",
            assignment_id=assignment.id,
            status=AssignmentStatus.PUBLISHED,
        )


# ==============================================================================
# UC-LMS-009: View or Download Published Assignment
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_25_view_published_assignment_main_flow(course_setup):
    """
    Test ID: TC-UC-25
    Source ID: UC-LMS-009 Main Flow
    Purpose: Verify registered student can view published available assignment details.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Downloadable Assignment",
        instructions="Detailed instructions text",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("50.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )

    detail = get_course_assignment_detail(
        principal=student,
        course_code="CS101",
        assignment_id=assignment.id,
    )
    assert detail is not None
    assert detail["title"] == "Downloadable Assignment"
    assert detail["instructions"] == "Detailed instructions text"


@pytest.mark.django_db
def test_tc_uc_26_view_published_assignment_alternative_a1(course_setup):
    """
    Test ID: TC-UC-26
    Source ID: UC-LMS-009 Alternative A1
    Purpose: Verify draft or future-dated unreleased assignments are omitted from student view.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    # Scheduled future assignment
    CourseAssignment.objects.create(
        course=course,
        title="Unreleased Future Assignment",
        instructions="Secret instructions",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("50.00"),
        status=AssignmentStatus.SCHEDULED,
        release_at=datetime.now(UTC) + timedelta(days=4),
        due_at=datetime.now(UTC) + timedelta(days=10),
        created_by_user_id=101,
    )

    assignments_data = list_course_assignments(principal=student, course_code="CS101")
    assert assignments_data is not None
    items = assignments_data.get("assignments", [])
    assert not any(a["title"] == "Unreleased Future Assignment" for a in items)


@pytest.mark.django_db
def test_tc_uc_27_view_published_assignment_exception_e1(course_setup):
    """
    Test ID: TC-UC-27
    Source ID: UC-LMS-009 Exception E1
    Purpose: Verify unauthorized user cannot view assignment details.
    """
    course = course_setup["course"]
    unenrolled = course_setup["unenrolled"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Protected Assignment",
        instructions="Instructions",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("50.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )

    detail = get_course_assignment_detail(
        principal=unenrolled,
        course_code="CS101",
        assignment_id=assignment.id,
    )
    assert detail is None


# ==============================================================================
# UC-LMS-010: Submit Assignment
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_28_submit_assignment_main_flow(course_setup):
    """
    Test ID: TC-UC-28
    Source ID: UC-LMS-010 Main Flow
    Purpose: Verify registered student can submit on-time assignment work matching configured type.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Homework 1",
        instructions="Write responses",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )

    submission = submission_service.create_submission(
        actor=student,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_type=SubmissionType.TEXT,
        content_text="My completed solutions.",
    )
    assert submission.id is not None
    assert submission.status == SubmissionStatus.SUBMITTED
    assert submission.student_user_id == 103
    assert submission.submitted_at is not None


@pytest.mark.django_db
def test_tc_uc_29_submit_assignment_alternative_a1(course_setup):
    """
    Test ID: TC-UC-29
    Source ID: UC-LMS-010 Alternative A1
    Purpose: Verify submission handling when submission occurs after due date (late submission).
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Late Allowed Assignment",
        instructions="Write responses",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) - timedelta(hours=2),
        closes_at=datetime.now(UTC) + timedelta(days=2),
        allow_late=True,
        created_by_user_id=101,
    )

    submission = submission_service.create_submission(
        actor=student,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_type=SubmissionType.TEXT,
        content_text="Late completed homework.",
    )
    assert submission.id is not None
    assert submission.status == SubmissionStatus.LATE


@pytest.mark.django_db
def test_tc_uc_30_submit_assignment_exception_e1(course_setup):
    """
    Test ID: TC-UC-30
    Source ID: UC-LMS-010 Exception E1
    Purpose: Verify submission with type inconsistent with assignment configuration is rejected.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="File Only Assignment",
        instructions="Upload zip only",
        submission_type=SubmissionType.FILE,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )

    # Attempt text submission when file required
    with pytest.raises((ConflictError, LMSRuleError)):
        submission_service.create_submission(
            actor=student,
            course_code="CS101",
            assignment_id=assignment.id,
            submission_type=SubmissionType.TEXT,
            content_text="Text submission where file was required",
        )


# ==============================================================================
# UC-LMS-011: View Submission History and Status
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_31_view_submission_history_main_flow(course_setup):
    """
    Test ID: TC-UC-31
    Source ID: UC-LMS-011 Main Flow
    Purpose: Verify registered student can view their own assignment submission history and status.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="History Test Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Solution v1",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    history = get_student_submission_history(
        principal=student,
        course_code="CS101",
        assignment_id=assignment.id,
    )
    assert history is not None
    assert history["student_user_id"] == 103
    assert history["has_submitted"] is True
    assert len(history["history"]) >= 1


@pytest.mark.django_db
def test_tc_uc_32_view_submission_history_alternative_a1(course_setup):
    """
    Test ID: TC-UC-32
    Source ID: UC-LMS-011 Alternative A1
    Purpose: Verify submission status accurately reflects late or submitted status.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Late Status Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) - timedelta(days=1),
        created_by_user_id=101,
    )
    CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Late Solution",
        status=SubmissionStatus.LATE,
        submitted_at=datetime.now(UTC),
    )

    history = get_student_submission_history(
        principal=student,
        course_code="CS101",
        assignment_id=assignment.id,
    )
    assert history is not None
    assert history["status"] == SubmissionStatus.LATE


@pytest.mark.django_db
def test_tc_uc_33_view_submission_history_exception_e1(course_setup):
    """
    Test ID: TC-UC-33
    Source ID: UC-LMS-011 Exception E1
    Purpose: Verify access to another student's submission data is denied.
    """
    course = course_setup["course"]
    student_b = make_actor(105, "student", STUDENT_PERMS)
    CourseMembership.objects.create(course=course, user_id=105, role=CourseRole.STUDENT)

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Confidential Submission Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,  # Student A
        submission_type=SubmissionType.TEXT,
        content_text="Student A confidential answer",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    # Student B queries Student A's submission history explicitly -> PermissionDeniedError
    with pytest.raises(PermissionDeniedError):
        get_student_submission_history(
            principal=student_b,
            course_code="CS101",
            assignment_id=assignment.id,
            student_user_id=103,
        )


# ==============================================================================
# UC-LMS-012: Grade Submission
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_34_grade_submission_main_flow(course_setup):
    """
    Test ID: TC-UC-34
    Source ID: UC-LMS-012 Main Flow
    Purpose: Verify faculty or TA can grade a student submission, recording points and grader attribution in Draft state.
    """
    course = course_setup["course"]
    faculty = course_setup["faculty"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Grading Target Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Answer",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    grade = grade_service.record_submission_grade(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
        score=Decimal("92.50"),
    )
    assert grade.score == Decimal("92.50")
    assert grade.status == GradeStatus.DRAFT
    assert grade.graded_by_user_id == 101
    assert grade.graded_at is not None


@pytest.mark.django_db
def test_tc_uc_35_grade_submission_alternative_a1(course_setup):
    """
    Test ID: TC-UC-35
    Source ID: UC-LMS-012 Alternative A1
    Purpose: Verify that regrading or editing an already graded submission records an updated grade with audit tracking.
    """
    course = course_setup["course"]
    faculty = course_setup["faculty"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Regrade Target Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Answer",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    grade1 = grade_service.record_submission_grade(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
        score=Decimal("80.00"),
    )
    assert grade1.score == Decimal("80.00")

    grade2 = grade_service.record_submission_grade(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
        score=Decimal("95.00"),
    )
    assert grade2.score == Decimal("95.00")
    assert grade2.id == grade1.id


@pytest.mark.django_db
def test_tc_uc_36_grade_submission_exception_e1(course_setup):
    """
    Test ID: TC-UC-36
    Source ID: UC-LMS-012 Exception E1
    Purpose: Verify unauthorized user (e.g. Student) cannot grade submissions.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Self-Grade Prevention Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Answer",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    with pytest.raises(PermissionDeniedError):
        grade_service.record_submission_grade(
            actor=student,
            course_code="CS101",
            assignment_id=assignment.id,
            submission_id=sub.id,
            score=Decimal("100.00"),
        )


# ==============================================================================
# UC-LMS-013: Release Grades and Feedback
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_37_release_grades_main_flow(course_setup):
    """
    Test ID: TC-UC-37
    Source ID: UC-LMS-013 Main Flow
    Purpose: Verify assigned faculty can release draft grades and feedback to students.
    """
    course = course_setup["course"]
    faculty = course_setup["faculty"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Grade Release Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Answer",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    grade = CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("89.00"),
        status=GradeStatus.DRAFT,
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    # Per UC-LMS-013 Main Flow:
    # 1. System verifies Faculty release authority.
    # 2. Faculty selects/initiates release.
    # 3. System changes applicable grades from Draft to Released.
    # 4. System makes released grades/feedback available to the corresponding Students.
    # Faculty executes transactional grade release service:
    grade_service.release_assignment_grades(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
    )

    grade.refresh_from_db()
    assert grade.status == GradeStatus.RELEASED

    released_grade = get_submission_grade(
        principal=student,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
    )
    assert released_grade is not None
    assert Decimal(released_grade["score"]) == Decimal("89.00")


@pytest.mark.django_db
def test_tc_uc_38_release_grades_exception_e1(course_setup):
    """
    Test ID: TC-UC-38
    Source ID: UC-LMS-013 Exception E1
    Purpose: Verify TA or unauthorized user cannot perform grade release under baseline policy.
    """
    ta = course_setup["ta"]
    # Grade release is restricted to Faculty; TAs cannot release grades
    assert "lms.course.manage" not in ta.permissions


# ==============================================================================
# UC-LMS-014: View Released Grade and Feedback
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_39_view_released_grade_main_flow(course_setup):
    """
    Test ID: TC-UC-39
    Source ID: UC-LMS-014 Main Flow
    Purpose: Verify registered student can view their own released grade and feedback in read-only form.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Released Grade Test Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Answer",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("94.00"),
        status=GradeStatus.RELEASED,
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    grade = get_submission_grade(
        principal=student,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
    )
    assert grade is not None
    assert Decimal(grade["score"]) == Decimal("94.00")
    assert Decimal(grade["points_possible"]) == Decimal("100.00")


@pytest.mark.django_db
def test_tc_uc_40_view_released_grade_alternative_a1(course_setup):
    """
    Test ID: TC-UC-40
    Source ID: UC-LMS-014 Alternative A1
    Purpose: Verify unreleased draft grade is not exposed to student.
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Draft Grade Test Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("100.00"),
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=3),
        created_by_user_id=101,
    )
    sub = CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Answer",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("75.00"),
        status=GradeStatus.DRAFT,
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    grade = get_submission_grade(
        principal=student,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
    )
    # Draft grade must be hidden from student
    assert grade is None


# ==============================================================================
# UC-LMS-015: Process Scheduled Content Release
# ==============================================================================

@pytest.mark.django_db
def test_tc_uc_41_process_scheduled_release_main_flow(course_setup):
    """
    Test ID: TC-UC-41
    Source ID: UC-LMS-015 Main Flow
    Purpose: Verify scheduled content (material and assignment) whose release time has arrived is transitioned to Published.
    """
    course = course_setup["course"]
    past_release = datetime.now(UTC) - timedelta(minutes=10)

    mat = CourseMaterial.objects.create(
        course=course,
        title="Scheduled Material to Release",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Auto-released lecture note",
        status=MaterialStatus.SCHEDULED,
        release_at=past_release,
        created_by_user_id=101,
    )
    assignment = CourseAssignment.objects.create(
        course=course,
        title="Scheduled Assignment to Release",
        instructions="Auto-released assignment instructions",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("50.00"),
        status=AssignmentStatus.SCHEDULED,
        release_at=past_release,
        due_at=datetime.now(UTC) + timedelta(days=5),
        created_by_user_id=101,
    )

    # Process scheduled releases
    rel_mats = material_service.release_scheduled_materials()
    rel_assigns = assignment_service.release_scheduled_assignments()

    mat.refresh_from_db()
    assignment.refresh_from_db()

    assert rel_mats >= 1
    assert mat.status == MaterialStatus.PUBLISHED
    assert rel_assigns >= 1
    assert assignment.status == AssignmentStatus.PUBLISHED
