"""FR Strategy Executable Test Suite (AFR and CFR obligations).

Every test contains its test_id and source_id.
Target: modules.lms
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    GradeStatus,
    MaterialStatus,
    MaterialType,
    SubmissionStatus,
    SubmissionType,
)
from modules.lms.domain.errors import (
    CourseAccessDenied,
    InvalidAssignmentState,
    ObserverAccessViolation,
    SubmissionTypeError,
    TAAuthoringRestriction,
)
from modules.lms.models import (
    Assignment,
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
    Grade,
    StudentSubmission,
)
from modules.lms.selectors import courses as selectors
from modules.lms.services import courses as services

pytestmark = pytest.mark.django_db


def _client(stub_iam, permissions=(), kind="student", uid=1001, roles=("student",)):
    stub_iam(
        make_session(user_id=uid, kind=kind, permissions=permissions, roles=roles, modules=("lms",))
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.fixture
def course():
    ws = CourseWorkspace.objects.create(
        course_code="CS101",
        title="Intro to CS",
        syllabus="Basic Python and Algorithms",
        schedule="Mon/Wed 10:00 AM",
        instructor_user_id=9001,
        is_active=True,
    )
    CourseMembership.objects.create(course=ws, user_id=9001, role=CourseRole.FACULTY.value)
    CourseMembership.objects.create(course=ws, user_id=2001, role=CourseRole.STUDENT.value)
    CourseMembership.objects.create(
        course=ws, user_id=3001, role=CourseRole.TA.value, can_post_announcements=True
    )
    CourseMembership.objects.create(course=ws, user_id=4001, role=CourseRole.OBSERVER.value)
    return ws


def test_fr_test_001_open_course_workspace(course):
    """FR-TEST-001 | AFR-LMS-001.1 | Verify authorized user can open dedicated course workspace."""
    ws = selectors.get_course_workspace(course.id, 2001)
    assert ws.course_code == "CS101"
    assert ws.title == "Intro to CS"


def test_fr_test_002_display_course_home_info(course):
    """FR-TEST-002 | AFR-LMS-001.2 | Verify course home displays syllabus, schedule, instructors, and TAs."""
    ws = selectors.get_course_workspace(course.id, 2001)
    memberships = selectors.get_user_memberships(2001)
    assert ws.syllabus == "Basic Python and Algorithms"
    assert ws.schedule == "Mon/Wed 10:00 AM"
    assert len(memberships) >= 1


def test_fr_test_003_restrict_unenrolled_access(course):
    """FR-TEST-003 | AFR-LMS-001.3 | Verify unenrolled user access restriction to course workspace."""
    with pytest.raises(CourseAccessDenied):
        selectors.get_course_workspace(course.id, 9999)


def test_fr_test_004_faculty_configures_workspace(course):
    """FR-TEST-004 | AFR-LMS-002.1 | Verify Faculty can configure and update course details."""
    course.syllabus = "Updated Syllabus 2026"
    course.schedule = "Tue/Thu 2:00 PM"
    course.save()
    ws = selectors.get_course_workspace(course.id, 9001)
    assert ws.syllabus == "Updated Syllabus 2026"


def test_fr_test_005_student_cannot_edit_course(stub_iam, course):
    """FR-TEST-005 | AFR-LMS-002.2 | Verify Student cannot modify course workspace details."""
    c = _client(stub_iam, permissions=("lms.view",), uid=2001)
    res = c.put(f"/api/v1/lms/courses/{course.id}/", {"syllabus": "Hacked"})
    assert res.status_code in (403, 405)


def test_fr_test_006_faculty_uploads_supported_material_types(course):
    """FR-TEST-006 | AFR-LMS-003.1 | Verify Faculty can upload supported material types (file, link, note)."""
    m_file = services.upload_course_material(
        course_id=course.id,
        user_id=9001,
        user_role=CourseRole.FACULTY.value,
        title="Slides 1",
        material_type=MaterialType.FILE.value,
        file_url="https://files.com/s1.pdf",
    )
    m_link = services.upload_course_material(
        course_id=course.id,
        user_id=9001,
        user_role=CourseRole.FACULTY.value,
        title="Link 1",
        material_type=MaterialType.LINK.value,
        file_url="https://docs.com",
    )
    m_note = services.upload_course_material(
        course_id=course.id,
        user_id=9001,
        user_role=CourseRole.FACULTY.value,
        title="Note 1",
        material_type=MaterialType.NOTE.value,
        content="Read Chapter 1",
    )
    assert m_file.material_type == "file"
    assert m_link.material_type == "link"
    assert m_note.material_type == "note"


def test_fr_test_007_organize_materials_into_sections(course):
    """FR-TEST-007 | AFR-LMS-003.2 | Verify Faculty can organize materials into sections."""
    m = services.upload_course_material(
        course_id=course.id,
        user_id=9001,
        user_role=CourseRole.FACULTY.value,
        title="Lab Guide",
        section_or_week="Week 3",
        material_type="file",
    )
    assert m.section_or_week == "Week 3"


def test_fr_test_008_schedule_future_material_release(course):
    """FR-TEST-008 | AFR-LMS-003.3 | Verify Faculty can schedule future material release."""
    rel_date = timezone.now() + timedelta(days=3)
    m = services.upload_course_material(
        course_id=course.id,
        user_id=9001,
        user_role=CourseRole.FACULTY.value,
        title="Exam Prep",
        is_scheduled=True,
        scheduled_release_at=rel_date,
    )
    assert m.status == MaterialStatus.SCHEDULED.value
    assert m.scheduled_release_at == rel_date


def test_fr_test_009_scheduled_material_release_time_reached(course):
    """FR-TEST-009 | AFR-LMS-003.4 | Verify scheduled material release when release time reached."""
    m = CourseMaterial.objects.create(
        course=course,
        title="Released Item",
        status=MaterialStatus.SCHEDULED.value,
        scheduled_release_at=timezone.now() - timedelta(minutes=10),
        uploaded_by_user_id=9001,
    )
    materials = selectors.get_course_materials(course.id, CourseRole.STUDENT.value)
    assert any(mat.id == m.id for mat in materials)


def test_fr_test_010_student_read_only_published_materials(course):
    """FR-TEST-010 | AFR-LMS-004.1 | Verify Student read-only material access."""
    CourseMaterial.objects.create(
        course=course,
        title="Pub Notes",
        status=MaterialStatus.PUBLISHED.value,
        uploaded_by_user_id=9001,
    )
    CourseMaterial.objects.create(
        course=course,
        title="Draft Notes",
        status=MaterialStatus.DRAFT.value,
        uploaded_by_user_id=9001,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.STUDENT.value)
    titles = [x.title for x in mats]
    assert "Pub Notes" in titles
    assert "Draft Notes" not in titles


def test_fr_test_011_ta_read_only_material_access(course):
    """FR-TEST-011 | AFR-LMS-004.2 | Verify TA read-only material access."""
    CourseMaterial.objects.create(
        course=course,
        title="Lecture 1",
        status=MaterialStatus.PUBLISHED.value,
        uploaded_by_user_id=9001,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.TA.value)
    assert any(x.title == "Lecture 1" for x in mats)


def test_fr_test_012_observer_read_only_material_access(course):
    """FR-TEST-012 | AFR-LMS-004.3 | Verify Observer read-only material access."""
    CourseMaterial.objects.create(
        course=course,
        title="Public Guide",
        status=MaterialStatus.PUBLISHED.value,
        uploaded_by_user_id=9001,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.OBSERVER.value)
    assert any(x.title == "Public Guide" for x in mats)


def test_fr_test_013_faculty_posts_announcement(course):
    """FR-TEST-013 | AFR-LMS-005.1 | Verify Faculty can post course announcement."""
    ann = services.post_course_announcement(
        course_id=course.id,
        user_id=9001,
        user_role=CourseRole.FACULTY.value,
        title="Welcome",
        content="Welcome to the class!",
    )
    assert ann.title == "Welcome"
    assert not ann.is_ta_announcement


def test_fr_test_014_permitted_ta_posts_announcement(course):
    """FR-TEST-014 | AFR-LMS-005.2 | Verify permitted TA can post announcement."""
    ann = services.post_course_announcement(
        course_id=course.id,
        user_id=3001,
        user_role=CourseRole.TA.value,
        title="Office Hours",
        content="TA Office hours today at 4 PM",
        can_post_announcements=True,
    )
    assert ann.is_ta_announcement


def test_fr_test_015_announcement_timestamp_and_coursewide_access(course):
    """FR-TEST-015 | AFR-LMS-005.3 | Verify announcement timestamping and course-wide visibility."""
    ann = services.post_course_announcement(
        course_id=course.id,
        user_id=9001,
        user_role=CourseRole.FACULTY.value,
        title="Exam Notice",
        content="Finals next week",
    )
    announcements = selectors.get_course_announcements(course.id)
    assert ann.posted_at is not None
    assert any(a.title == "Exam Notice" for a in announcements)


def test_fr_test_016_faculty_creates_draft_assignment(course):
    """FR-TEST-016 | AFR-LMS-006.1 | Verify Faculty can create assignment in draft state."""
    due = timezone.now() + timedelta(days=7)
    asgn = services.create_assignment(
        course_id=course.id,
        user_id=9001,
        user_role=CourseRole.FACULTY.value,
        title="HW1",
        instructions="Complete ex 1-5",
        points_possible=Decimal("50.00"),
        submission_type=SubmissionType.FILE.value,
        due_date=due,
    )
    assert asgn.status == AssignmentStatus.DRAFT.value
    assert asgn.points_possible == Decimal("50.00")


def test_fr_test_017_assignment_configuration_validation(course):
    """FR-TEST-017 | AFR-LMS-006.2 | Verify assignment configuration validation (negative points rejected)."""
    due = timezone.now() + timedelta(days=7)
    with pytest.raises(InvalidAssignmentState):
        services.create_assignment(
            course_id=course.id,
            user_id=9001,
            user_role=CourseRole.FACULTY.value,
            title="HW Invalid",
            instructions="test",
            points_possible=Decimal("-10.00"),
            submission_type=SubmissionType.FILE.value,
            due_date=due,
        )


def test_fr_test_018_draft_assignment_hidden_from_students(course):
    """FR-TEST-018 | AFR-LMS-006.4 | Verify draft assignment remains hidden from students."""
    Assignment.objects.create(
        course=course,
        title="Secret Draft",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=7),
        status=AssignmentStatus.DRAFT.value,
        created_by_user_id=9001,
    )
    asgns = selectors.get_course_assignments(course.id, CourseRole.STUDENT.value)
    assert not any(a.title == "Secret Draft" for a in asgns)


def test_fr_test_019_faculty_publishes_assignment_immediately(course):
    """FR-TEST-019 | AFR-LMS-007.1 | Verify Faculty can publish assignment immediately."""
    asgn = Assignment.objects.create(
        course=course,
        title="HW2",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=7),
        status=AssignmentStatus.DRAFT.value,
        created_by_user_id=9001,
    )
    pub = services.publish_assignment(
        assignment_id=asgn.id, user_role=CourseRole.FACULTY.value, is_scheduled=False
    )
    assert pub.status == AssignmentStatus.AVAILABLE.value
    assert pub.published_at is not None


def test_fr_test_020_scheduled_assignment_hidden_before_release(course):
    """FR-TEST-020 | AFR-LMS-007.2 | Verify scheduled assignment hidden from students before release date."""
    Assignment.objects.create(
        course=course,
        title="Future HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=14),
        status=AssignmentStatus.SCHEDULED.value,
        scheduled_release_at=timezone.now() + timedelta(days=2),
        created_by_user_id=9001,
    )
    asgns = selectors.get_course_assignments(course.id, CourseRole.STUDENT.value)
    assert not any(a.title == "Future HW" for a in asgns)


def test_fr_test_021_student_views_available_assignment(course):
    """FR-TEST-021 | AFR-LMS-007.4 | Verify Student can view available assignment."""
    Assignment.objects.create(
        course=course,
        title="Open HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    asgns = selectors.get_course_assignments(course.id, CourseRole.STUDENT.value)
    assert any(a.title == "Open HW" for a in asgns)


def test_fr_test_022_student_submits_matching_type(course):
    """FR-TEST-022 | AFR-LMS-008.1 | Verify Student can submit assignment with matching submission type."""
    asgn = Assignment.objects.create(
        course=course,
        title="Text HW",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    sub = services.submit_assignment(
        assignment_id=asgn.id,
        student_user_id=2001,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="My essay content",
    )
    assert sub.status == SubmissionStatus.SUBMITTED.value
    assert sub.submission_content == "My essay content"


def test_fr_test_023_submission_type_mismatch_rejected(course):
    """FR-TEST-023 | AFR-LMS-008.2 | Verify submission type mismatch is rejected."""
    asgn = Assignment.objects.create(
        course=course,
        title="File HW",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE.value,
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    with pytest.raises(SubmissionTypeError):
        services.submit_assignment(
            assignment_id=asgn.id,
            student_user_id=2001,
            student_role=CourseRole.STUDENT.value,
            submission_type=SubmissionType.TEXT.value,
            submission_content="Text where file expected",
        )


def test_fr_test_024_student_views_own_submission(course):
    """FR-TEST-024 | AFR-LMS-009.1 | Verify Student can view own submission history and status."""
    asgn = Assignment.objects.create(
        course=course,
        title="HW View",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2001,
        submission_type="text",
        submission_content="Student 2001 work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    detail = selectors.get_submission_detail(sub.id, 2001, CourseRole.STUDENT.value)
    assert detail.submission_content == "Student 2001 work"


def test_fr_test_025_faculty_grades_submission(course):
    """FR-TEST-025 | AFR-LMS-010.1 | Verify Faculty can grade student submission with score and feedback."""
    asgn = Assignment.objects.create(
        course=course,
        title="HW Grade",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2001,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    grade = services.grade_submission(
        submission_id=sub.id,
        grader_user_id=9001,
        grader_role=CourseRole.FACULTY.value,
        points=Decimal("92.50"),
        feedback="Great work!",
    )
    assert grade.points == Decimal("92.50")
    assert grade.graded_by_user_id == 9001
    assert grade.status == GradeStatus.DRAFT.value


def test_fr_test_026_ta_grades_submission(course):
    """FR-TEST-026 | AFR-LMS-010.2 | Verify TA can grade student submission with score and feedback."""
    asgn = Assignment.objects.create(
        course=course,
        title="HW TA Grade",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2001,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    grade = services.grade_submission(
        submission_id=sub.id,
        grader_user_id=3001,
        grader_role=CourseRole.TA.value,
        points=Decimal("85.00"),
        feedback="Good job",
    )
    assert grade.graded_by_user_id == 3001
    assert grade.status == GradeStatus.DRAFT.value


def test_fr_test_027_draft_grade_hidden_from_student(course):
    """FR-TEST-027 | AFR-LMS-011.1 | Verify draft grade remains hidden from student until release."""
    asgn = Assignment.objects.create(
        course=course,
        title="HW Draft Grade",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2001,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    Grade.objects.create(
        submission=sub,
        points=Decimal("90.00"),
        status=GradeStatus.DRAFT.value,
        graded_by_user_id=9001,
    )
    student_grades = selectors.get_student_course_grades(course.id, 2001)
    assert len(student_grades) == 0


def test_fr_test_028_faculty_releases_draft_grades(course):
    """FR-TEST-028 | AFR-LMS-011.3 | Verify Faculty can release draft grades to students."""
    asgn = Assignment.objects.create(
        course=course,
        title="HW Release",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2001,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    Grade.objects.create(
        submission=sub,
        points=Decimal("95.00"),
        status=GradeStatus.DRAFT.value,
        graded_by_user_id=9001,
    )
    count = services.release_assignment_grades(
        assignment_id=asgn.id, releaser_user_id=9001, releaser_role=CourseRole.FACULTY.value
    )
    assert count == 1
    grade = Grade.objects.get(submission=sub)
    assert grade.status == GradeStatus.RELEASED.value
    assert grade.released_at is not None


def test_fr_test_029_student_views_released_grade(course):
    """FR-TEST-029 | AFR-LMS-012.1 | Verify Student can view released grade and feedback."""
    asgn = Assignment.objects.create(
        course=course,
        title="HW View Grade",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2001,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    Grade.objects.create(
        submission=sub,
        points=Decimal("98.00"),
        feedback="Excellent!",
        status=GradeStatus.RELEASED.value,
        graded_by_user_id=9001,
        released_by_user_id=9001,
    )
    grades = selectors.get_student_course_grades(course.id, 2001)
    assert len(grades) == 1
    assert grades[0].points == Decimal("98.00")


def test_fr_test_030_post_release_grade_modification_audit(course):
    """FR-TEST-030 | AFR-LMS-013.1 | Verify post-release grade modification creates audit log."""
    asgn = Assignment.objects.create(
        course=course,
        title="HW Audit",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2001,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    g = Grade.objects.create(
        submission=sub,
        points=Decimal("80.00"),
        status=GradeStatus.RELEASED.value,
        graded_by_user_id=9001,
        released_by_user_id=9001,
    )
    services.modify_released_grade(
        grade_id=g.id,
        modifier_user_id=9001,
        modifier_role=CourseRole.FACULTY.value,
        new_points=Decimal("88.00"),
        reason="Recheck question 2",
    )
    logs = selectors.get_grade_change_logs(g.id)
    assert len(logs) == 1
    assert logs[0].old_points == Decimal("80.00")
    assert logs[0].new_points == Decimal("88.00")
    assert logs[0].reason == "Recheck question 2"


def test_fr_test_031_ta_cannot_create_assignment(course):
    """FR-TEST-031 | AFR-LMS-014.3 | Verify TA authoring restriction on assignments."""
    due = timezone.now() + timedelta(days=7)
    with pytest.raises(TAAuthoringRestriction):
        services.create_assignment(
            course_id=course.id,
            user_id=3001,
            user_role=CourseRole.TA.value,
            title="TA HW",
            instructions="none",
            points_possible=Decimal("50.00"),
            submission_type="file",
            due_date=due,
        )


def test_fr_test_032_ta_cannot_upload_material(course):
    """FR-TEST-032 | AFR-LMS-014.4 | Verify TA authoring restriction on course materials."""
    with pytest.raises(TAAuthoringRestriction):
        services.upload_course_material(
            course_id=course.id,
            user_id=3001,
            user_role=CourseRole.TA.value,
            title="TA Slides",
            material_type="file",
        )


def test_fr_test_033_observer_cannot_view_submissions(course):
    """FR-TEST-033 | AFR-LMS-015.2 | Verify Observer restriction from viewing student submissions."""
    asgn = Assignment.objects.create(
        course=course,
        title="Obs HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    with pytest.raises(ObserverAccessViolation):
        selectors.get_assignment_submissions(asgn.id, 4001, CourseRole.OBSERVER.value)


def test_fr_test_034_observer_cannot_grade(course):
    """FR-TEST-034 | AFR-LMS-015.4 | Verify Observer write restriction on grade evaluation."""
    asgn = Assignment.objects.create(
        course=course,
        title="Obs Grade HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2001,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    with pytest.raises(ObserverAccessViolation):
        services.grade_submission(
            submission_id=sub.id,
            grader_user_id=4001,
            grader_role=CourseRole.OBSERVER.value,
            points=Decimal("50.00"),
        )


def test_fr_test_035_unenrolled_user_submission_rejection_defect(stub_iam, course):
    """FR-TEST-035 | AFR-LMS-001.3-DEFECT | Verify unenrolled user cannot submit assignment via API."""
    asgn = Assignment.objects.create(
        course=course,
        title="API Submission",
        instructions="Submit",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9001,
    )
    c = _client(stub_iam, permissions=("lms.view", "lms.assignment.view"), uid=8888)
    res = c.post(
        f"/api/v1/lms/assignments/{asgn.id}/submissions/",
        {"submission_type": "text", "submission_content": "Unenrolled work"},
        format="json",
    )
    # Expected by AFR-LMS-001.3: HTTP 403 Forbidden
    # Candidate Defect: API defaults membership.role to 'student' when membership is None and creates submission!
    assert res.status_code == 403, (
        f"Candidate Defect: Unenrolled user was permitted to submit work! Got {res.status_code}"
    )
