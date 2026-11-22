"""UC Strategy Executable Test Suite (Use Case flows: Main, Alternative, Exception).

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
    LmsDomainError,
    SubmissionOwnershipError,
    SubmissionTypeError,
    TAAuthoringRestriction,
    UnauthorizedGradingError,
)
from modules.lms.models import (
    Assignment,
    CourseAnnouncement,
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
        course_code="CS201",
        title="Data Structures",
        syllabus="Trees and Graphs",
        schedule="Tue/Thu 11:30 AM",
        instructor_user_id=9002,
        is_active=True,
    )
    CourseMembership.objects.create(course=ws, user_id=9002, role=CourseRole.FACULTY.value)
    CourseMembership.objects.create(course=ws, user_id=2002, role=CourseRole.STUDENT.value)
    CourseMembership.objects.create(
        course=ws, user_id=3002, role=CourseRole.TA.value, can_post_announcements=True
    )
    CourseMembership.objects.create(course=ws, user_id=4002, role=CourseRole.OBSERVER.value)
    return ws


def test_uc_test_001_access_course_workspace_main_flow(course):
    """UC-TEST-001 | UC-LMS-001 Main Flow | Enrolled user opens course workspace and views course home details."""
    ws = selectors.get_course_workspace(course.id, 2002)
    assert ws.title == "Data Structures"
    assert ws.syllabus == "Trees and Graphs"


def test_uc_test_002_access_course_workspace_exception_e1(course):
    """UC-TEST-002 | UC-LMS-001 Exception E1 | Unenrolled user attempts to access course workspace."""
    with pytest.raises(CourseAccessDenied):
        selectors.get_course_workspace(course.id, 9999)


def test_uc_test_003_manage_course_details_main_flow(course):
    """UC-TEST-003 | UC-LMS-002 Main Flow | Assigned Faculty updates syllabus and schedule."""
    course.syllabus = "Advanced Graphs & Hash Tables"
    course.save()
    ws = selectors.get_course_workspace(course.id, 9002)
    assert ws.syllabus == "Advanced Graphs & Hash Tables"


def test_uc_test_004_manage_course_details_exception_e1(stub_iam, course):
    """UC-TEST-004 | UC-LMS-002 Exception E1 | Unauthorized role attempts to edit course workspace details."""
    c = _client(stub_iam, permissions=("lms.view",), uid=2002)
    res = c.put(f"/api/v1/lms/courses/{course.id}/", {"syllabus": "Illegal change"})
    assert res.status_code in (403, 405)


def test_uc_test_005_manage_materials_main_flow(course):
    """UC-TEST-005 | UC-LMS-003 Main Flow | Faculty uploads course material with immediate publication."""
    m = services.upload_course_material(
        course_id=course.id,
        user_id=9002,
        user_role=CourseRole.FACULTY.value,
        title="Lecture 1 Notes",
        material_type=MaterialType.NOTE.value,
        content="Welcome to CS201",
        is_scheduled=False,
    )
    assert m.status == MaterialStatus.PUBLISHED.value
    assert m.published_at is not None


def test_uc_test_006_manage_materials_alternative_a1(course):
    """UC-TEST-006 | UC-LMS-003 Alternative A1 | Faculty schedules course material with future release date."""
    rel = timezone.now() + timedelta(days=4)
    m = services.upload_course_material(
        course_id=course.id,
        user_id=9002,
        user_role=CourseRole.FACULTY.value,
        title="Midterm Review",
        material_type=MaterialType.FILE.value,
        is_scheduled=True,
        scheduled_release_at=rel,
    )
    assert m.status == MaterialStatus.SCHEDULED.value


def test_uc_test_007_manage_materials_exception_e1(course):
    """UC-TEST-007 | UC-LMS-003 Exception E1 | TA attempts to upload course material."""
    with pytest.raises(TAAuthoringRestriction):
        services.upload_course_material(
            course_id=course.id,
            user_id=3002,
            user_role=CourseRole.TA.value,
            title="TA Notes",
            material_type=MaterialType.NOTE.value,
        )


def test_uc_test_008_view_published_materials_main_flow(course):
    """UC-TEST-008 | UC-LMS-004 Main Flow | Student views published course materials."""
    CourseMaterial.objects.create(
        course=course,
        title="Pub DS Notes",
        status=MaterialStatus.PUBLISHED.value,
        uploaded_by_user_id=9002,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.STUDENT.value)
    assert any(x.title == "Pub DS Notes" for x in mats)


def test_uc_test_009_view_published_materials_alternative_a1(course):
    """UC-TEST-009 | UC-LMS-004 Alternative A1 | Observer views published course materials in read-only mode."""
    CourseMaterial.objects.create(
        course=course,
        title="Public Syllabus Guide",
        status=MaterialStatus.PUBLISHED.value,
        uploaded_by_user_id=9002,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.OBSERVER.value)
    assert any(x.title == "Public Syllabus Guide" for x in mats)


def test_uc_test_010_view_published_materials_exception_e1(course):
    """UC-TEST-010 | UC-LMS-004 Exception E1 | Student attempts to view scheduled material before release date."""
    CourseMaterial.objects.create(
        course=course,
        title="Future Secret Notes",
        status=MaterialStatus.SCHEDULED.value,
        scheduled_release_at=timezone.now() + timedelta(days=5),
        uploaded_by_user_id=9002,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.STUDENT.value)
    assert not any(x.title == "Future Secret Notes" for x in mats)


def test_uc_test_011_post_announcement_main_flow(course):
    """UC-TEST-011 | UC-LMS-005 Main Flow | Faculty posts course announcement."""
    ann = services.post_course_announcement(
        course_id=course.id,
        user_id=9002,
        user_role=CourseRole.FACULTY.value,
        title="Class Cancelled",
        content="No class this Friday",
    )
    assert ann.title == "Class Cancelled"
    assert not ann.is_ta_announcement


def test_uc_test_012_post_announcement_alternative_a1(course):
    """UC-TEST-012 | UC-LMS-005 Alternative A1 | TA with announcement permission posts announcement."""
    ann = services.post_course_announcement(
        course_id=course.id,
        user_id=3002,
        user_role=CourseRole.TA.value,
        title="Lab Session",
        content="Lab 2 starts tomorrow",
        can_post_announcements=True,
    )
    assert ann.is_ta_announcement


def test_uc_test_013_post_announcement_exception_e1(course):
    """UC-TEST-013 | UC-LMS-005 Exception E1 | TA without announcement permission attempts to post announcement."""
    with pytest.raises(TAAuthoringRestriction):
        services.post_course_announcement(
            course_id=course.id,
            user_id=3002,
            user_role=CourseRole.TA.value,
            title="Unauthorized",
            content="Test",
            can_post_announcements=False,
        )


def test_uc_test_014_view_announcements_main_flow(course):
    """UC-TEST-014 | UC-LMS-006 Main Flow | Enrolled user views course announcements."""
    CourseAnnouncement.objects.create(
        course=course, title="Welcome DS", content="Hello all", posted_by_user_id=9002
    )
    anns = selectors.get_course_announcements(course.id)
    assert any(a.title == "Welcome DS" for a in anns)


def test_uc_test_015_create_assignment_main_flow(course):
    """UC-TEST-015 | UC-LMS-007 Main Flow | Faculty creates draft assignment with valid configuration."""
    asgn = services.create_assignment(
        course_id=course.id,
        user_id=9002,
        user_role=CourseRole.FACULTY.value,
        title="Binary Trees HW",
        instructions="Implement AVL Tree",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE.value,
        due_date=timezone.now() + timedelta(days=10),
    )
    assert asgn.status == AssignmentStatus.DRAFT.value


def test_uc_test_016_edit_assignment_alternative_a1(course):
    """UC-TEST-016 | UC-LMS-007 Alternative A1 | Faculty edits existing draft assignment."""
    asgn = Assignment.objects.create(
        course=course,
        title="Old Title",
        points_possible=Decimal("50.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.DRAFT.value,
        created_by_user_id=9002,
    )
    asgn.title = "New Updated Title"
    asgn.save()
    assert Assignment.objects.get(id=asgn.id).title == "New Updated Title"


def test_uc_test_017_create_assignment_exception_e1(course):
    """UC-TEST-017 | UC-LMS-007 Exception E1 | Faculty creates assignment with invalid points (points <= 0)."""
    with pytest.raises(InvalidAssignmentState):
        services.create_assignment(
            course_id=course.id,
            user_id=9002,
            user_role=CourseRole.FACULTY.value,
            title="Zero Point HW",
            instructions="none",
            points_possible=Decimal("0.00"),
            submission_type=SubmissionType.TEXT.value,
            due_date=timezone.now() + timedelta(days=5),
        )


def test_uc_test_018_create_assignment_exception_e2(course):
    """UC-TEST-018 | UC-LMS-007 Exception E2 | TA attempts to create assignment."""
    with pytest.raises(TAAuthoringRestriction):
        services.create_assignment(
            course_id=course.id,
            user_id=3002,
            user_role=CourseRole.TA.value,
            title="TA Assignment",
            instructions="none",
            points_possible=Decimal("50.00"),
            submission_type=SubmissionType.TEXT.value,
            due_date=timezone.now() + timedelta(days=5),
        )


def test_uc_test_019_publish_assignment_main_flow(course):
    """UC-TEST-019 | UC-LMS-008 Main Flow | Faculty publishes draft assignment immediately."""
    asgn = Assignment.objects.create(
        course=course,
        title="Graph HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.DRAFT.value,
        created_by_user_id=9002,
    )
    pub = services.publish_assignment(
        assignment_id=asgn.id, user_role=CourseRole.FACULTY.value, is_scheduled=False
    )
    assert pub.status == AssignmentStatus.AVAILABLE.value


def test_uc_test_020_publish_assignment_alternative_a1(course):
    """UC-TEST-020 | UC-LMS-008 Alternative A1 | Faculty schedules assignment for future release."""
    asgn = Assignment.objects.create(
        course=course,
        title="Future Graph HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=12),
        status=AssignmentStatus.DRAFT.value,
        created_by_user_id=9002,
    )
    rel = timezone.now() + timedelta(days=2)
    pub = services.publish_assignment(
        assignment_id=asgn.id,
        user_role=CourseRole.FACULTY.value,
        is_scheduled=True,
        release_date=rel,
    )
    assert pub.status == AssignmentStatus.SCHEDULED.value


def test_uc_test_021_publish_assignment_exception_e1(stub_iam, course):
    """UC-TEST-021 | UC-LMS-008 Exception E1 | Unenrolled / non-faculty user attempts to publish assignment via API."""
    asgn = Assignment.objects.create(
        course=course,
        title="Sec Draft",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.DRAFT.value,
        created_by_user_id=9002,
    )
    # User 7777 is not enrolled in course
    c = _client(stub_iam, permissions=("lms.view", "lms.assignment.create"), uid=7777)
    res = c.post(
        f"/api/v1/lms/assignments/{asgn.id}/publish/", {"is_scheduled": False}, format="json"
    )
    # Expected by UC-LMS-008: HTTP 403 Forbidden
    # Candidate Defect: API defaults membership.role to 'faculty' when membership is None!
    assert res.status_code == 403, (
        f"Candidate Defect: Unenrolled user published assignment! Got {res.status_code}"
    )


def test_uc_test_022_view_published_assignment_main_flow(course):
    """UC-TEST-022 | UC-LMS-009 Main Flow | Student views published assignment details."""
    Assignment.objects.create(
        course=course,
        title="Active HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    asgns = selectors.get_course_assignments(course.id, CourseRole.STUDENT.value)
    assert any(a.title == "Active HW" for a in asgns)


def test_uc_test_023_view_draft_assignment_exception_e1(course):
    """UC-TEST-023 | UC-LMS-009 Exception E1 | Student attempts to access draft assignment before publication."""
    Assignment.objects.create(
        course=course,
        title="Hidden Draft HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.DRAFT.value,
        created_by_user_id=9002,
    )
    asgns = selectors.get_course_assignments(course.id, CourseRole.STUDENT.value)
    assert not any(a.title == "Hidden Draft HW" for a in asgns)


def test_uc_test_024_submit_assignment_main_flow(course):
    """UC-TEST-024 | UC-LMS-010 Main Flow | Student submits valid work before deadline."""
    asgn = Assignment.objects.create(
        course=course,
        title="Submit HW",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    sub = services.submit_assignment(
        assignment_id=asgn.id,
        student_user_id=2002,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="Valid solution",
    )
    assert sub.status == SubmissionStatus.SUBMITTED.value


def test_uc_test_025_submit_assignment_alternative_a1(course):
    """UC-TEST-025 | UC-LMS-010 Alternative A1 | Student submits work after deadline."""
    asgn = Assignment.objects.create(
        course=course,
        title="Late HW",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=timezone.now() - timedelta(hours=2),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    sub = services.submit_assignment(
        assignment_id=asgn.id,
        student_user_id=2002,
        student_role=CourseRole.STUDENT.value,
        submission_type=SubmissionType.TEXT.value,
        submission_content="Late solution",
    )
    assert sub.status == SubmissionStatus.LATE.value


def test_uc_test_026_submit_assignment_exception_e1(stub_iam, course):
    """UC-TEST-026 | UC-LMS-010 Exception E1 | Unenrolled student attempts to submit assignment via API."""
    asgn = Assignment.objects.create(
        course=course,
        title="API Asgn",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT.value,
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    c = _client(stub_iam, permissions=("lms.view", "lms.assignment.view"), uid=8888)
    res = c.post(
        f"/api/v1/lms/assignments/{asgn.id}/submissions/",
        {"submission_type": "text", "submission_content": "Unenrolled work"},
        format="json",
    )
    # Expected by UC-LMS-010: HTTP 403 Forbidden
    # Candidate Defect: API defaults membership.role to 'student' when membership is None!
    assert res.status_code == 403, (
        f"Candidate Defect: Unenrolled user submitted work! Got {res.status_code}"
    )


def test_uc_test_027_submit_assignment_exception_e2(course):
    """UC-TEST-027 | UC-LMS-010 Exception E2 | Student submits work with mismatched submission type."""
    asgn = Assignment.objects.create(
        course=course,
        title="File Only HW",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE.value,
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    with pytest.raises(SubmissionTypeError):
        services.submit_assignment(
            assignment_id=asgn.id,
            student_user_id=2002,
            student_role=CourseRole.STUDENT.value,
            submission_type=SubmissionType.TEXT.value,
            submission_content="Text when file required",
        )


def test_uc_test_028_view_submission_main_flow(course):
    """UC-TEST-028 | UC-LMS-011 Main Flow | Student views own submission history and status."""
    asgn = Assignment.objects.create(
        course=course,
        title="Hist HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2002,
        submission_type="text",
        submission_content="My DS code",
        status=SubmissionStatus.SUBMITTED.value,
    )
    det = selectors.get_submission_detail(sub.id, 2002, CourseRole.STUDENT.value)
    assert det.submission_content == "My DS code"


def test_uc_test_029_view_submission_exception_e1(course):
    """UC-TEST-029 | UC-LMS-011 Exception E1 | Student attempts to view another student submission detail."""
    asgn = Assignment.objects.create(
        course=course,
        title="Peer HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2002,
        submission_type="text",
        submission_content="Peer work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    with pytest.raises(SubmissionOwnershipError):
        selectors.get_submission_detail(sub.id, 9999, CourseRole.STUDENT.value)


def test_uc_test_030_grade_submission_main_flow(course):
    """UC-TEST-030 | UC-LMS-012 Main Flow | Faculty evaluates submission and saves draft grade."""
    asgn = Assignment.objects.create(
        course=course,
        title="Grading HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2002,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    g = services.grade_submission(
        submission_id=sub.id,
        grader_user_id=9002,
        grader_role=CourseRole.FACULTY.value,
        points=Decimal("89.00"),
        feedback="Good trees",
    )
    assert g.points == Decimal("89.00")
    assert g.status == GradeStatus.DRAFT.value


def test_uc_test_031_grade_submission_alternative_a1(course):
    """UC-TEST-031 | UC-LMS-012 Alternative A1 | TA evaluates submission and saves draft grade with attribution."""
    asgn = Assignment.objects.create(
        course=course,
        title="TA Grading HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2002,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    g = services.grade_submission(
        submission_id=sub.id,
        grader_user_id=3002,
        grader_role=CourseRole.TA.value,
        points=Decimal("82.00"),
        feedback="Checked by TA",
    )
    assert g.graded_by_user_id == 3002


def test_uc_test_032_grade_submission_exception_e1(course):
    """UC-TEST-032 | UC-LMS-012 Exception E1 | Score exceeding points_possible rejected."""
    asgn = Assignment.objects.create(
        course=course,
        title="Bound HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2002,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    with pytest.raises(LmsDomainError):
        services.grade_submission(
            submission_id=sub.id,
            grader_user_id=9002,
            grader_role=CourseRole.FACULTY.value,
            points=Decimal("105.00"),
        )


def test_uc_test_033_release_grades_main_flow(course):
    """UC-TEST-033 | UC-LMS-013 Main Flow | Faculty releases all draft grades for assignment."""
    asgn = Assignment.objects.create(
        course=course,
        title="Rel HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2002,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    Grade.objects.create(
        submission=sub,
        points=Decimal("90.00"),
        status=GradeStatus.DRAFT.value,
        graded_by_user_id=9002,
    )
    count = services.release_assignment_grades(
        assignment_id=asgn.id, releaser_user_id=9002, releaser_role=CourseRole.FACULTY.value
    )
    assert count == 1


def test_uc_test_034_release_grades_exception_e1(course):
    """UC-TEST-034 | UC-LMS-013 Exception E1 | TA attempts to release grades."""
    asgn = Assignment.objects.create(
        course=course,
        title="TA Rel HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    with pytest.raises(UnauthorizedGradingError):
        services.release_assignment_grades(
            assignment_id=asgn.id, releaser_user_id=3002, releaser_role=CourseRole.TA.value
        )


def test_uc_test_035_view_released_grade_main_flow(course):
    """UC-TEST-035 | UC-LMS-014 Main Flow | Student views own released grade and feedback."""
    asgn = Assignment.objects.create(
        course=course,
        title="View Rel HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2002,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    Grade.objects.create(
        submission=sub,
        points=Decimal("94.00"),
        feedback="Well done",
        status=GradeStatus.RELEASED.value,
        graded_by_user_id=9002,
        released_by_user_id=9002,
    )
    grades = selectors.get_student_course_grades(course.id, 2002)
    assert len(grades) == 1
    assert grades[0].points == Decimal("94.00")


def test_uc_test_036_view_unreleased_grade_exception_e1(course):
    """UC-TEST-036 | UC-LMS-014 Exception E1 | Student attempts to view draft/unreleased grade."""
    asgn = Assignment.objects.create(
        course=course,
        title="Hold Rel HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9002,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2002,
        submission_type="text",
        submission_content="Student work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    Grade.objects.create(
        submission=sub,
        points=Decimal("90.00"),
        status=GradeStatus.DRAFT.value,
        graded_by_user_id=9002,
    )
    grades = selectors.get_student_course_grades(course.id, 2002)
    assert len(grades) == 0


def test_uc_test_037_scheduled_release_main_flow(course):
    """UC-TEST-037 | UC-LMS-015 Main Flow | Scheduled release when release date <= now."""
    m = CourseMaterial.objects.create(
        course=course,
        title="Release Now Notes",
        status=MaterialStatus.SCHEDULED.value,
        scheduled_release_at=timezone.now() - timedelta(minutes=5),
        uploaded_by_user_id=9002,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.STUDENT.value)
    assert any(x.id == m.id for x in mats)


def test_uc_test_038_scheduled_release_alternative_a1(course):
    """UC-TEST-038 | UC-LMS-015 Alternative A1 | Scheduled content remains hidden when release date > now."""
    m = CourseMaterial.objects.create(
        course=course,
        title="Pending Secret Notes",
        status=MaterialStatus.SCHEDULED.value,
        scheduled_release_at=timezone.now() + timedelta(days=3),
        uploaded_by_user_id=9002,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.STUDENT.value)
    assert not any(x.id == m.id for x in mats)
