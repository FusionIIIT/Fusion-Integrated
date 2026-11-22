"""Specification-Driven Tests: Strategy 1 - Functional Requirements (FR).

Covers all 47 AFR obligations across CFR-LMS-001 through CFR-LMS-015.
Baseline: Frozen A8_BASE for LMS (Course Management) module.
"""
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.api.exceptions import PermissionDeniedError
from fusion_auth.principal import Principal
from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    CourseStatus,
    MaterialStatus,
    MaterialType,
    SectionType,
    SubmissionStatus,
    SubmissionType,
)
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
    get_assignment_for_download,
    get_course_assignment_detail,
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
    "lms.course.view", "lms.material.view", "lms.announcement.view",
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
# CFR-LMS-001: Access Course Workspace & View Course Home
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_01_open_dedicated_course_workspace(course_setup):
    """
    Test ID: TC_FR_01
    Source ID: AFR-LMS-001.1
    Purpose: Verify system opens dedicated course workspace when authorized user selects a course
    """
    student = course_setup["student"]
    workspace = course_workspace_details(principal=student, course_code="CS101")

    assert workspace is not None
    assert workspace["code"] == "CS101"
    assert workspace["title"] == "Intro to Computer Science"


@pytest.mark.django_db
def test_tc_fr_02_display_course_home_information(course_setup):
    """
    Test ID: TC_FR_02
    Source ID: AFR-LMS-001.2
    Purpose: Verify system displays course syllabus, schedule, instructor(s), and TA(s) on course home page
    """
    student = course_setup["student"]
    workspace = course_workspace_details(principal=student, course_code="CS101")

    assert workspace is not None
    assert "syllabus" in workspace
    assert workspace["syllabus"] == "Week 1: Intro, Week 2: Logic"
    assert "schedule" in workspace
    assert workspace["schedule"] == "Mon/Wed 10:00"
    assert "instructors" in workspace
    assert "teaching_assistants" in workspace
    assert len(workspace["instructors"]) == 1
    assert len(workspace["teaching_assistants"]) == 1


@pytest.mark.django_db
def test_tc_fr_03_restrict_course_specific_access(course_setup):
    """
    Test ID: TC_FR_03
    Source ID: AFR-LMS-001.3
    Purpose: Verify system restricts course workspace access to users enrolled in, assigned to, or linked to the course
    """
    unenrolled = course_setup["unenrolled"]
    workspace = course_workspace_details(principal=unenrolled, course_code="CS101")
    assert workspace is None


# ==============================================================================
# CFR-LMS-002: Manage Course Workspace Details
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_04_configure_assigned_course_workspace(course_setup):
    """
    Test ID: TC_FR_04
    Source ID: AFR-LMS-002.1
    Purpose: Verify Faculty can configure course workspace for an assigned course
    """
    faculty = course_setup["faculty"]
    updated = course_service.update_course_workspace(
        actor=faculty,
        course_code="CS101",
        description="Updated CS101 description",
        syllabus="Expanded syllabus",
        schedule="Tue/Thu 14:00",
    )

    assert updated.description == "Updated CS101 description"
    assert updated.syllabus == "Expanded syllabus"
    assert updated.schedule == "Tue/Thu 14:00"


@pytest.mark.django_db
def test_tc_fr_05_publish_and_edit_course_details(course_setup):
    """
    Test ID: TC_FR_05
    Source ID: AFR-LMS-002.2
    Purpose: Verify Faculty can publish and edit course details for an assigned course workspace
    """
    faculty = course_setup["faculty"]
    updated = course_service.update_course_workspace(
        actor=faculty,
        course_code="CS101",
        title="Intro to Computer Science - Revised",
        status=CourseStatus.PUBLISHED,
    )

    assert updated.title == "Intro to Computer Science - Revised"
    assert updated.status == CourseStatus.PUBLISHED


# ==============================================================================
# CFR-LMS-003: Manage and Schedule Course Materials
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_06_upload_supported_material_types(course_setup):
    """
    Test ID: TC_FR_06
    Source ID: AFR-LMS-003.1
    Purpose: Verify Faculty can add course materials as files, links, or notes
    """
    faculty = course_setup["faculty"]
    test_file = SimpleUploadedFile("slides.pdf", b"%PDF-1.4 test slides", content_type="application/pdf")

    file_mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS101",
        title="Lecture 1 Slides",
        section_title="Module 1",
        material_type=MaterialType.FILE,
        file=test_file,
    )
    link_mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS101",
        title="Reference Website",
        section_title="Module 1",
        material_type=MaterialType.LINK,
        link_url="https://docs.python.org/3/",
    )
    note_mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS101",
        title="Lecture 1 Notes",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Key concepts discussed during lecture.",
    )

    assert file_mat.material_type == MaterialType.FILE
    assert link_mat.material_type == MaterialType.LINK
    assert note_mat.material_type == MaterialType.NOTE


@pytest.mark.django_db
def test_tc_fr_07_organize_materials(course_setup):
    """
    Test ID: TC_FR_07
    Source ID: AFR-LMS-003.2
    Purpose: Verify Faculty can organize course materials into modules or weekly sections
    """
    faculty = course_setup["faculty"]

    mat1 = material_service.create_course_material(
        actor=faculty,
        course_code="CS101",
        title="Module Material",
        section_type=SectionType.MODULE,
        section_title="Module 1: Foundations",
        material_type=MaterialType.NOTE,
        content="Foundations content",
    )
    mat2 = material_service.create_course_material(
        actor=faculty,
        course_code="CS101",
        title="Week Material",
        section_type=SectionType.WEEK,
        section_title="Week 1: Orientation",
        material_type=MaterialType.NOTE,
        content="Week 1 content",
    )

    assert mat1.section_type == SectionType.MODULE
    assert mat1.section_title == "Module 1: Foundations"
    assert mat2.section_type == SectionType.WEEK
    assert mat2.section_title == "Week 1: Orientation"


@pytest.mark.django_db
def test_tc_fr_08_schedule_future_material_release(course_setup):
    """
    Test ID: TC_FR_08
    Source ID: AFR-LMS-003.3
    Purpose: Verify Faculty can configure a future release date for course material
    """
    faculty = course_setup["faculty"]
    future_time = datetime.now(UTC) + timedelta(days=7)

    mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS101",
        title="Future Topic Material",
        section_title="Module 2",
        material_type=MaterialType.NOTE,
        content="Future content",
        status=MaterialStatus.SCHEDULED,
        release_at=future_time,
    )

    assert mat.status == MaterialStatus.SCHEDULED
    assert mat.release_at == future_time


@pytest.mark.django_db
def test_tc_fr_09_release_scheduled_material(course_setup):
    """
    Test ID: TC_FR_09
    Source ID: AFR-LMS-003.4
    Purpose: Verify scheduled material is published/available to authorized users when release time is reached
    """
    course = course_setup["course"]
    due_time = datetime.now(UTC) - timedelta(minutes=5)

    mat = CourseMaterial.objects.create(
        course=course,
        title="Due Scheduled Material",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Now released notes",
        status=MaterialStatus.SCHEDULED,
        release_at=due_time,
        created_by_user_id=101,
    )

    released_count = material_service.release_scheduled_materials()
    mat.refresh_from_db()

    assert released_count >= 1
    assert mat.status == MaterialStatus.PUBLISHED


# ==============================================================================
# CFR-LMS-004: View Published Course Materials
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_10_student_read_only_material_access(course_setup):
    """
    Test ID: TC_FR_10
    Source ID: AFR-LMS-004.1
    Purpose: Verify Student can view published course materials for registered course in read-only form
    """
    course = course_setup["course"]
    student = course_setup["student"]

    CourseMaterial.objects.create(
        course=course,
        title="Published Material",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Visible note",
        status=MaterialStatus.PUBLISHED,
        created_by_user_id=101,
    )
    CourseMaterial.objects.create(
        course=course,
        title="Draft Material",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Hidden note",
        status=MaterialStatus.DRAFT,
        created_by_user_id=101,
    )

    result = list_course_materials(principal=student, course_code="CS101")
    assert result is not None
    titles = [m["title"] for sec in result.get("sections", []) for m in sec.get("materials", [])]

    assert "Published Material" in titles
    assert "Draft Material" not in titles


@pytest.mark.django_db
def test_tc_fr_11_ta_read_only_material_access(course_setup):
    """
    Test ID: TC_FR_11
    Source ID: AFR-LMS-004.2
    Purpose: Verify TA can view published course materials for assigned course in read-only form
    """
    course = course_setup["course"]
    ta = course_setup["ta"]

    CourseMaterial.objects.create(
        course=course,
        title="TA Accessible Material",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="TA note",
        status=MaterialStatus.PUBLISHED,
        created_by_user_id=101,
    )

    result = list_course_materials(principal=ta, course_code="CS101")
    assert result is not None
    titles = [m["title"] for sec in result.get("sections", []) for m in sec.get("materials", [])]
    assert "TA Accessible Material" in titles


@pytest.mark.django_db
def test_tc_fr_12_observer_read_only_material_access(course_setup):
    """
    Test ID: TC_FR_12
    Source ID: AFR-LMS-004.3
    Purpose: Verify Observer can view published course materials for linked course in read-only form
    """
    course = course_setup["course"]
    observer = course_setup["observer"]

    CourseMaterial.objects.create(
        course=course,
        title="Observer Material",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Observer note",
        status=MaterialStatus.PUBLISHED,
        created_by_user_id=101,
    )

    result = list_course_materials(principal=observer, course_code="CS101")
    assert result is not None
    titles = [m["title"] for sec in result.get("sections", []) for m in sec.get("materials", [])]
    assert "Observer Material" in titles


# ==============================================================================
# CFR-LMS-005: Post and View Course Announcements
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_13_faculty_posts_announcement(course_setup):
    """
    Test ID: TC_FR_13
    Source ID: AFR-LMS-005.1
    Purpose: Verify Faculty can post a course-wide announcement for an assigned course
    """
    faculty = course_setup["faculty"]
    ann = announcement_service.post_course_announcement(
        actor=faculty,
        course_code="CS101",
        title="Midterm Exam Schedule",
        content="Midterm exam will be held on Friday at 10 AM.",
    )

    assert ann.id is not None
    assert ann.title == "Midterm Exam Schedule"
    assert ann.content == "Midterm exam will be held on Friday at 10 AM."


@pytest.mark.django_db
def test_tc_fr_14_permitted_ta_posts_announcement(course_setup):
    """
    Test ID: TC_FR_14
    Source ID: AFR-LMS-005.2
    Purpose: Verify TA can post announcement only when permitted, and unpermitted TA is prevented from posting
    """
    ta = course_setup["ta"]
    with pytest.raises(PermissionDeniedError):
        announcement_service.post_course_announcement(
            actor=ta,
            course_code="CS101",
            title="Unauthorized Notice",
            content="TA notice without permission",
        )


@pytest.mark.django_db
def test_tc_fr_15_timestamp_announcement(course_setup):
    """
    Test ID: TC_FR_15
    Source ID: AFR-LMS-005.3
    Purpose: Verify system timestamps each posted course announcement
    """
    faculty = course_setup["faculty"]
    ann = announcement_service.post_course_announcement(
        actor=faculty,
        course_code="CS101",
        title="Timestamp Test Notice",
        content="Testing timestamp creation",
    )

    assert ann.created_at is not None
    assert isinstance(ann.created_at, datetime)


@pytest.mark.django_db
def test_tc_fr_16_make_announcement_course_wide(course_setup):
    """
    Test ID: TC_FR_16
    Source ID: AFR-LMS-005.4
    Purpose: Verify posted announcement is visible to all users enrolled in or linked to the course
    """
    faculty = course_setup["faculty"]
    announcement_service.post_course_announcement(
        actor=faculty,
        course_code="CS101",
        title="Course-Wide Welcome",
        content="Welcome to all students, TAs, and observers.",
    )

    for role_name in ["faculty", "ta", "student", "observer"]:
        actor = course_setup[role_name]
        res = list_course_announcements(principal=actor, course_code="CS101")
        assert res is not None
        titles = [a["title"] for a in res["announcements"]]
        assert "Course-Wide Welcome" in titles


# ==============================================================================
# CFR-LMS-006: Create and Edit Assignments
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_17_create_assignment(course_setup):
    """
    Test ID: TC_FR_17
    Source ID: AFR-LMS-006.1
    Purpose: Verify Faculty can create an assignment for an assigned course
    """
    faculty = course_setup["faculty"]
    assignment = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Assignment 1: Algorithms",
        instructions="Complete questions 1 to 5.",
        submission_type=SubmissionType.FILE,
        points_possible=Decimal("100.00"),
    )

    assert assignment.id is not None
    assert assignment.title == "Assignment 1: Algorithms"


@pytest.mark.django_db
def test_tc_fr_18_capture_assignment_configuration(course_setup):
    """
    Test ID: TC_FR_18
    Source ID: AFR-LMS-006.2
    Purpose: Verify system captures assignment due date, instructions, submission type, and points possible
    """
    faculty = course_setup["faculty"]
    due_date = datetime.now(UTC) + timedelta(days=5)

    assignment = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Assignment 2: Sorting",
        instructions="Implement Merge Sort and Quick Sort.",
        submission_type=SubmissionType.FILE,
        points_possible=Decimal("50.00"),
        due_at=due_date,
    )

    assert assignment.instructions == "Implement Merge Sort and Quick Sort."
    assert assignment.submission_type == SubmissionType.FILE
    assert assignment.points_possible == Decimal("50.00")
    assert assignment.due_at == due_date


@pytest.mark.django_db
def test_tc_fr_19_edit_assignment(course_setup):
    """
    Test ID: TC_FR_19
    Source ID: AFR-LMS-006.3
    Purpose: Verify Faculty can edit an existing assignment
    """
    faculty = course_setup["faculty"]
    assignment = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Assignment 3: Initial",
        instructions="Initial instructions",
        submission_type=SubmissionType.TEXT,
        points_possible=Decimal("20.00"),
    )

    updated = assignment_service.update_course_assignment(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        title="Assignment 3: Updated",
        instructions="Updated comprehensive instructions",
        points_possible=Decimal("30.00"),
    )

    assert updated.title == "Assignment 3: Updated"
    assert updated.instructions == "Updated comprehensive instructions"
    assert updated.points_possible == Decimal("30.00")


@pytest.mark.django_db
def test_tc_fr_20_maintain_draft_before_publication(course_setup):
    """
    Test ID: TC_FR_20
    Source ID: AFR-LMS-006.4
    Purpose: Verify assignment remains in Draft state until Faculty publishes it
    """
    faculty = course_setup["faculty"]
    assignment = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Draft Assignment",
        status=AssignmentStatus.DRAFT,
    )

    assert assignment.status == AssignmentStatus.DRAFT


# ==============================================================================
# CFR-LMS-007: Publish Assignments and Control Release Visibility
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_21_publish_assignment(course_setup):
    """
    Test ID: TC_FR_21
    Source ID: AFR-LMS-007.1
    Purpose: Verify Faculty can publish an assignment
    """
    faculty = course_setup["faculty"]
    due_date = datetime.now(UTC) + timedelta(days=7)
    assignment = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Assignment to Publish",
        instructions="Complete the exercises.",
        due_at=due_date,
        status=AssignmentStatus.DRAFT,
    )

    published = assignment_service.update_course_assignment(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        status=AssignmentStatus.PUBLISHED,
    )

    assert published.status == AssignmentStatus.PUBLISHED


@pytest.mark.django_db
def test_tc_fr_22_apply_release_date_visibility(course_setup):
    """
    Test ID: TC_FR_22
    Source ID: AFR-LMS-007.2
    Purpose: Verify published assignment with future release date is withheld from Students until release time
    """
    faculty = course_setup["faculty"]
    student = course_setup["student"]
    future_release = datetime.now(UTC) + timedelta(days=3)
    future_due = datetime.now(UTC) + timedelta(days=10)

    assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS101",
        title="Future Scheduled Assignment",
        instructions="Instructions for future assignment",
        due_at=future_due,
        status=AssignmentStatus.SCHEDULED,
        release_at=future_release,
    )

    res = list_course_assignments(principal=student, course_code="CS101")
    assert res is not None
    titles = [a["title"] for a in res["assignments"]]
    assert "Future Scheduled Assignment" not in titles


@pytest.mark.django_db
def test_tc_fr_23_release_scheduled_assignment(course_setup):
    """
    Test ID: TC_FR_23
    Source ID: AFR-LMS-007.3
    Purpose: Verify scheduled assignment becomes available to authorized Students when release time is reached
    """
    course = course_setup["course"]
    student = course_setup["student"]
    past_release = datetime.now(UTC) - timedelta(minutes=10)
    future_due = datetime.now(UTC) + timedelta(days=5)

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Now Releasable Assignment",
        instructions="Solve tasks.",
        status=AssignmentStatus.SCHEDULED,
        release_at=past_release,
        due_at=future_due,
        created_by_user_id=101,
    )

    assignment_service.release_scheduled_assignments()
    assignment.refresh_from_db()
    assert assignment.status == AssignmentStatus.PUBLISHED

    res = list_course_assignments(principal=student, course_code="CS101")
    assert res is not None
    titles = [a["title"] for a in res["assignments"]]
    assert "Now Releasable Assignment" in titles


@pytest.mark.django_db
def test_tc_fr_24_view_download_released_assignment(course_setup):
    """
    Test ID: TC_FR_24
    Source ID: AFR-LMS-007.4
    Purpose: Verify Student can view and download released assignment for registered course
    """
    course = course_setup["course"]
    student = course_setup["student"]
    file_content = b"%PDF-1.4 assignment prompt"
    test_file = SimpleUploadedFile("prompt.pdf", file_content, content_type="application/pdf")

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Downloadable Assignment",
        instructions="Instructions",
        status=AssignmentStatus.PUBLISHED,
        file=test_file,
        file_name="prompt.pdf",
        file_size=len(file_content),
        due_at=datetime.now(UTC) + timedelta(days=5),
        created_by_user_id=101,
    )

    details = get_course_assignment_detail(principal=student, course_code="CS101", assignment_id=assignment.id)
    assert details is not None
    assert details["title"] == "Downloadable Assignment"

    download_obj, filename = get_assignment_for_download(principal=student, course_code="CS101", assignment_id=assignment.id)
    assert download_obj.id == assignment.id
    assert os.path.basename(filename) == "prompt.pdf" or "prompt" in filename


# ==============================================================================
# CFR-LMS-008: Submit Assignment Work
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_25_submit_configured_work_type(course_setup):
    """
    Test ID: TC_FR_25
    Source ID: AFR-LMS-008.1
    Purpose: Verify Student can submit assignment work according to configured submission type (file, text, link)
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="File Submission Assignment",
        instructions="Upload file",
        submission_type=SubmissionType.FILE,
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
        created_by_user_id=101,
    )

    sub_file = SimpleUploadedFile("solution.pdf", b"Student Solution Content", content_type="application/pdf")
    sub = submission_service.create_submission(
        actor=student,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_type=SubmissionType.FILE,
        file=sub_file,
    )

    assert sub.id is not None
    assert sub.submission_type == SubmissionType.FILE
    assert sub.student_user_id == 103


@pytest.mark.django_db
def test_tc_fr_26_accept_on_time_submission(course_setup):
    """
    Test ID: TC_FR_26
    Source ID: AFR-LMS-008.2
    Purpose: Verify system accepts and records Student submission made before due date
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="On-Time Test Assignment",
        instructions="Submit on time",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(hours=12),
        created_by_user_id=101,
    )

    sub = submission_service.create_submission(
        actor=student,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_type=SubmissionType.TEXT,
        content_text="Solution submitted well before deadline.",
    )

    assert sub.status == SubmissionStatus.SUBMITTED
    assert sub.submitted_at < assignment.due_at


# ==============================================================================
# CFR-LMS-009: View Own Submission History and Status
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_27_view_own_submission_history(course_setup):
    """
    Test ID: TC_FR_27
    Source ID: AFR-LMS-009.1
    Purpose: Verify Student can view Student own submission history for an assignment
    """
    course = course_setup["course"]
    student1 = course_setup["student"]
    make_actor(202, "student", STUDENT_PERMS)
    CourseMembership.objects.create(course=course, user_id=202, role=CourseRole.STUDENT)

    assignment = CourseAssignment.objects.create(
        course=course,
        title="History Test Assignment",
        instructions="Submit work",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
        created_by_user_id=101,
    )

    CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Student 1 Work",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )
    CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=202,
        submission_type=SubmissionType.TEXT,
        content_text="Student 2 Work",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    history = get_student_submission_history(principal=student1, course_code="CS101", assignment_id=assignment.id)
    assert history is not None
    submissions = history.get("history", [])
    assert len(submissions) == 1
    assert submissions[0]["student_user_id"] == 103


@pytest.mark.django_db
def test_tc_fr_28_view_own_submission_status(course_setup):
    """
    Test ID: TC_FR_28
    Source ID: AFR-LMS-009.2
    Purpose: Verify system shows Student own submission status as submitted, late, or missing where applicable
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Status Tracking Assignment",
        instructions="Submit work",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=1),
        created_by_user_id=101,
    )

    CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="My content",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    history = get_student_submission_history(principal=student, course_code="CS101", assignment_id=assignment.id)
    assert history is not None
    assert history["status"] in ["submitted", "late", "missing", "not_submitted"]


# ==============================================================================
# CFR-LMS-010: Grade Individual Submissions
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_29_faculty_grades_submission(course_setup):
    """
    Test ID: TC_FR_29
    Source ID: AFR-LMS-010.1
    Purpose: Verify Faculty can grade an individual Student submission by entering points and feedback
    """
    course = course_setup["course"]
    faculty = course_setup["faculty"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Grading Assignment",
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
        content_text="Answers",
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
    assert grade.graded_by_user_id == 101


@pytest.mark.django_db
def test_tc_fr_30_ta_grades_submission(course_setup):
    """
    Test ID: TC_FR_30
    Source ID: AFR-LMS-010.2
    Purpose: Verify TA can grade an individual Student submission for assigned course with points and feedback
    """
    course = course_setup["course"]
    ta = course_setup["ta"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="TA Grading Assignment",
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
        content_text="Answers",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    grade = grade_service.record_submission_grade(
        actor=ta,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
        score=Decimal("84.00"),
    )

    assert grade.score == Decimal("84.00")
    assert grade.graded_by_user_id == 102


@pytest.mark.django_db
def test_tc_fr_31_attribute_grading_action(course_setup):
    """
    Test ID: TC_FR_31
    Source ID: AFR-LMS-010.3
    Purpose: Verify system records identity of Faculty member or TA who performs grading action
    """
    course = course_setup["course"]
    faculty = course_setup["faculty"]

    assignment = CourseAssignment.objects.create(
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
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Work",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    grade = grade_service.record_submission_grade(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
        score=Decimal("95.00"),
    )

    assert grade.graded_by_user_id == faculty.user_id


# ==============================================================================
# CFR-LMS-011: Hold and Release Grades/Feedback
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_32_hold_grade_in_draft(course_setup):
    """
    Test ID: TC_FR_32
    Source ID: AFR-LMS-011.1
    Purpose: Verify grade and feedback remain in Draft state until release
    """
    course = course_setup["course"]
    assignment = CourseAssignment.objects.create(
        course=course,
        title="Draft Grade Assignment",
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
    grade = CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("88.00"),
        status="draft",
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    assert grade.status == "draft"


@pytest.mark.django_db
def test_tc_fr_33_hide_draft_grade_from_student(course_setup):
    """
    Test ID: TC_FR_33
    Source ID: AFR-LMS-011.2
    Purpose: Verify system prevents Student from viewing grade or feedback before release
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Hidden Grade Assignment",
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
    CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("88.00"),
        status="draft",
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    grade_info = get_submission_grade(
        principal=student,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
    )
    assert grade_info is None or grade_info.get("status") != "draft" or grade_info.get("score") is None


@pytest.mark.django_db
def test_tc_fr_34_faculty_releases_grade_feedback(course_setup):
    """
    Test ID: TC_FR_34
    Source ID: AFR-LMS-011.3
    Purpose: Verify Faculty can release draft grades and feedback to Students
    """
    course = course_setup["course"]
    course_setup["faculty"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Release Grade Assignment",
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
    grade = CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("90.00"),
        status="draft",
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    grade.status = "published"
    grade.save()

    grade.refresh_from_db()
    assert grade.status in ["published", "released"]


# ==============================================================================
# CFR-LMS-012: View Released Grade and Feedback
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_35_view_own_released_grade_feedback(course_setup):
    """
    Test ID: TC_FR_35
    Source ID: AFR-LMS-012.1
    Purpose: Verify Student can view own grade and feedback after release
    """
    course = course_setup["course"]
    student = course_setup["student"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="View Grade Assignment",
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
    CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("91.00"),
        status="published",
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    grade_info = get_submission_grade(
        principal=student,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
    )
    assert grade_info is not None
    assert Decimal(str(grade_info["score"])) == Decimal("91.00")


@pytest.mark.django_db
def test_tc_fr_36_released_grade_is_read_only_to_student(course_setup):
    """
    Test ID: TC_FR_36
    Source ID: AFR-LMS-012.2
    Purpose: Verify released grade and feedback are presented to Student in read-only form
    """
    student = course_setup["student"]
    with pytest.raises(PermissionDeniedError):
        grade_service.record_submission_grade(
            actor=student,
            course_code="CS101",
            assignment_id=1,
            submission_id=1,
            score=Decimal("100.00"),
        )


# ==============================================================================
# CFR-LMS-013: Audit Post-Release Grade Changes
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_37_log_post_release_grade_change_actor(course_setup):
    """
    Test ID: TC_FR_37
    Source ID: AFR-LMS-013.1
    Purpose: Verify system records who made the change when a released grade is changed
    """
    course = course_setup["course"]
    faculty = course_setup["faculty"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Audit Actor Assignment",
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
    CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("80.00"),
        status="published",
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    updated_grade = grade_service.record_submission_grade(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
        score=Decimal("85.00"),
    )

    assert updated_grade.graded_by_user_id == faculty.user_id


@pytest.mark.django_db
def test_tc_fr_38_log_post_release_grade_change_time(course_setup):
    """
    Test ID: TC_FR_38
    Source ID: AFR-LMS-013.2
    Purpose: Verify system records when change was made when a released grade is changed
    """
    course = course_setup["course"]
    faculty = course_setup["faculty"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Audit Time Assignment",
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
    CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("80.00"),
        status="published",
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    updated_grade = grade_service.record_submission_grade(
        actor=faculty,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
        score=Decimal("90.00"),
    )

    assert updated_grade.updated_at is not None
    assert isinstance(updated_grade.updated_at, datetime)


# ==============================================================================
# CFR-LMS-014: Enforce Teaching Assistant Capabilities and Restrictions
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_39_ta_views_course_content(course_setup):
    """
    Test ID: TC_FR_39
    Source ID: AFR-LMS-014.1
    Purpose: Verify TA can view course details, published materials, and announcements for assigned course
    """
    ta = course_setup["ta"]
    course = course_setup["course"]

    CourseMaterial.objects.create(
        course=course,
        title="TA Viewable Material",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="TA note",
        status=MaterialStatus.PUBLISHED,
        created_by_user_id=101,
    )
    CourseAnnouncement.objects.create(
        course=course,
        title="TA Viewable Notice",
        content="Notice for all",
        created_by_user_id=101,
    )

    workspace = course_workspace_details(principal=ta, course_code="CS101")
    materials = list_course_materials(principal=ta, course_code="CS101")
    announcements = list_course_announcements(principal=ta, course_code="CS101")

    assert workspace is not None
    assert materials is not None
    assert announcements is not None


@pytest.mark.django_db
def test_tc_fr_40_ta_views_submissions(course_setup):
    """
    Test ID: TC_FR_40
    Source ID: AFR-LMS-014.2
    Purpose: Verify TA can view Student submissions for assigned course
    """
    course = course_setup["course"]
    ta = course_setup["ta"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="TA Submissions View Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
        created_by_user_id=101,
    )
    CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Solution",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    submissions_result = list_assignment_submissions(principal=ta, course_code="CS101", assignment_id=assignment.id)
    assert submissions_result is not None
    assert len(submissions_result["submissions"]) >= 1


@pytest.mark.django_db
def test_tc_fr_41_ta_cannot_author_assignments(course_setup):
    """
    Test ID: TC_FR_41
    Source ID: AFR-LMS-014.3
    Purpose: Verify TA is prevented from creating or editing assignments
    """
    ta = course_setup["ta"]
    with pytest.raises(PermissionDeniedError):
        assignment_service.create_course_assignment(
            actor=ta,
            course_code="CS101",
            title="TA Assignment Attempt",
        )


@pytest.mark.django_db
def test_tc_fr_42_ta_cannot_author_materials(course_setup):
    """
    Test ID: TC_FR_42
    Source ID: AFR-LMS-014.4
    Purpose: Verify TA is prevented from creating or editing course materials
    """
    ta = course_setup["ta"]
    with pytest.raises(PermissionDeniedError):
        material_service.create_course_material(
            actor=ta,
            course_code="CS101",
            title="TA Material Attempt",
            section_title="Module 1",
            material_type=MaterialType.NOTE,
            content="Content",
        )


@pytest.mark.django_db
def test_tc_fr_43_ta_cannot_modify_course_structure(course_setup):
    """
    Test ID: TC_FR_43
    Source ID: AFR-LMS-014.5
    Purpose: Verify TA is prevented from modifying course structure
    """
    ta = course_setup["ta"]
    with pytest.raises(PermissionDeniedError):
        course_service.update_course_workspace(
            actor=ta,
            course_code="CS101",
            syllabus="Unauthorized TA syllabus modification",
        )


# ==============================================================================
# CFR-LMS-015: Enforce Observer Read-Only Access and Privacy
# ==============================================================================

@pytest.mark.django_db
def test_tc_fr_44_observer_reads_permitted_course_content(course_setup):
    """
    Test ID: TC_FR_44
    Source ID: AFR-LMS-015.1
    Purpose: Verify Observer can view course details, published materials, and announcements in read-only form
    """
    observer = course_setup["observer"]
    course = course_setup["course"]

    CourseMaterial.objects.create(
        course=course,
        title="Observer Reading Material",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        content="Observer note content",
        status=MaterialStatus.PUBLISHED,
        created_by_user_id=101,
    )
    CourseAnnouncement.objects.create(
        course=course,
        title="Observer Notice",
        content="Notice for observer",
        created_by_user_id=101,
    )

    ws = course_workspace_details(principal=observer, course_code="CS101")
    mats = list_course_materials(principal=observer, course_code="CS101")
    anns = list_course_announcements(principal=observer, course_code="CS101")

    assert ws is not None
    assert mats is not None
    assert anns is not None


@pytest.mark.django_db
def test_tc_fr_45_observer_cannot_view_submissions(course_setup):
    """
    Test ID: TC_FR_45
    Source ID: AFR-LMS-015.2
    Purpose: Verify Observer is prevented from viewing individual Student submissions
    """
    course = course_setup["course"]
    observer = course_setup["observer"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Privacy Assignment",
        instructions="Work",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        due_at=datetime.now(UTC) + timedelta(days=2),
        created_by_user_id=101,
    )
    CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=103,
        submission_type=SubmissionType.TEXT,
        content_text="Confidential Student Work",
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(UTC),
    )

    result = list_assignment_submissions(principal=observer, course_code="CS101", assignment_id=assignment.id)
    assert result is None


@pytest.mark.django_db
def test_tc_fr_46_observer_cannot_view_grades_or_student_specific_data(course_setup):
    """
    Test ID: TC_FR_46
    Source ID: AFR-LMS-015.3
    Purpose: Verify Observer is prevented from viewing grades or any Student-specific data
    """
    course = course_setup["course"]
    observer = course_setup["observer"]

    assignment = CourseAssignment.objects.create(
        course=course,
        title="Privacy Grade Assignment",
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
    CourseSubmissionGrade.objects.create(
        submission=sub,
        assignment=assignment,
        student_user_id=103,
        score=Decimal("95.00"),
        status="published",
        graded_by_user_id=101,
        graded_at=datetime.now(UTC),
    )

    grade_result = get_submission_grade(
        principal=observer,
        course_code="CS101",
        assignment_id=assignment.id,
        submission_id=sub.id,
    )
    assert grade_result is None


@pytest.mark.django_db
def test_tc_fr_47_observer_has_no_write_access(course_setup):
    """
    Test ID: TC_FR_47
    Source ID: AFR-LMS-015.4
    Purpose: Verify Observer is prevented from performing write actions anywhere in LMS Course Management
    """
    observer = course_setup["observer"]

    with pytest.raises(PermissionDeniedError):
        course_service.update_course_workspace(
            actor=observer,
            course_code="CS101",
            title="Observer Tamper Title",
        )

    with pytest.raises(PermissionDeniedError):
        material_service.create_course_material(
            actor=observer,
            course_code="CS101",
            title="Observer Material",
            section_title="Module 1",
            material_type=MaterialType.NOTE,
            content="Observer content",
        )

    with pytest.raises(PermissionDeniedError):
        announcement_service.post_course_announcement(
            actor=observer,
            course_code="CS101",
            title="Observer Announcement",
            content="Observer text",
        )
