"""BR Strategy Executable Test Suite (Business Rules: Permitted, Prohibited, Thresholds).

Every test contains its test_id and source_id.
Target: modules.lms
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain import rules
from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    GradeStatus,
    MaterialStatus,
    SubmissionStatus,
)
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
        course_code="CS301",
        title="Operating Systems",
        syllabus="Processes and Concurrency",
        schedule="Mon/Wed/Fri 9:00 AM",
        instructor_user_id=9003,
        is_active=True,
    )
    CourseMembership.objects.create(course=ws, user_id=9003, role=CourseRole.FACULTY.value)
    CourseMembership.objects.create(course=ws, user_id=2003, role=CourseRole.STUDENT.value)
    CourseMembership.objects.create(
        course=ws, user_id=3003, role=CourseRole.TA.value, can_post_announcements=True
    )
    CourseMembership.objects.create(course=ws, user_id=4003, role=CourseRole.OBSERVER.value)
    return ws


def test_br_test_001_course_access_permitted(course):
    """BR-TEST-001 | BR-LMS-001 permitted | Enrolled member can access course workspace."""
    ws = selectors.get_course_workspace(course.id, 2003)
    assert ws.course_code == "CS301"


def test_br_test_002_course_access_prohibited(course):
    """BR-TEST-002 | BR-LMS-001 prohibited | Unenrolled user is prohibited from course workspace."""
    with pytest.raises(CourseAccessDenied):
        selectors.get_course_workspace(course.id, 8888)


def test_br_test_003_student_registration_governs_access(course):
    """BR-TEST-003 | BR-LMS-002 permitted | Active student registration grants course access."""
    membership = selectors.get_membership(course.id, 2003)
    assert membership is not None
    assert membership.role == CourseRole.STUDENT.value


def test_br_test_004_observer_read_only_permitted(course):
    """BR-TEST-004 | BR-LMS-003 permitted | Observer can view syllabus and published course materials."""
    CourseMaterial.objects.create(
        course=course,
        title="OS Overview",
        status=MaterialStatus.PUBLISHED.value,
        uploaded_by_user_id=9003,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.OBSERVER.value)
    assert any(m.title == "OS Overview" for m in mats)


def test_br_test_005_observer_student_data_prohibited(course):
    """BR-TEST-005 | BR-LMS-003 prohibited | Observer is prohibited from viewing submissions or grading."""
    asgn = Assignment.objects.create(
        course=course,
        title="Kernel HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9003,
    )
    with pytest.raises(ObserverAccessViolation):
        selectors.get_assignment_submissions(asgn.id, 4003, CourseRole.OBSERVER.value)


def test_br_test_006_ta_grading_permitted(course):
    """BR-TEST-006 | BR-LMS-004 permitted | TA can view course content and student submissions for grading."""
    asgn = Assignment.objects.create(
        course=course,
        title="Sync HW",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9003,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2003,
        submission_type="text",
        submission_content="Mutex implementation",
        status=SubmissionStatus.SUBMITTED.value,
    )
    subs = selectors.get_assignment_submissions(asgn.id, 3003, CourseRole.TA.value)
    assert any(s.id == sub.id for s in subs)


def test_br_test_007_ta_authoring_prohibited(course):
    """BR-TEST-007 | BR-LMS-004 prohibited | TA is prohibited from authoring assignments or materials."""
    with pytest.raises(TAAuthoringRestriction):
        services.upload_course_material(
            course_id=course.id,
            user_id=3003,
            user_role=CourseRole.TA.value,
            title="TA Notes",
            material_type="file",
        )


def test_br_test_008_published_material_visibility_permitted(course):
    """BR-TEST-008 | BR-LMS-005 permitted | Published materials are visible to students."""
    visible = rules.validate_material_visibility(
        MaterialStatus.PUBLISHED.value, CourseRole.STUDENT.value
    )
    assert visible is True


def test_br_test_009_draft_material_visibility_prohibited(course):
    """BR-TEST-009 | BR-LMS-005 prohibited | Draft materials are prohibited from student view."""
    visible = rules.validate_material_visibility(
        MaterialStatus.DRAFT.value, CourseRole.STUDENT.value
    )
    assert visible is False


def test_br_test_010_scheduled_material_threshold_past(course):
    """BR-TEST-010 | BR-LMS-006 threshold-le | Material scheduled_release_at <= now is published/visible."""
    past_date = timezone.now() - timedelta(hours=1)
    m = CourseMaterial.objects.create(
        course=course,
        title="Released Lecture",
        status=MaterialStatus.SCHEDULED.value,
        scheduled_release_at=past_date,
        uploaded_by_user_id=9003,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.STUDENT.value)
    assert any(x.id == m.id for x in mats)


def test_br_test_011_scheduled_material_threshold_future(course):
    """BR-TEST-011 | BR-LMS-006 threshold-gt | Material scheduled_release_at > now remains hidden from students."""
    future_date = timezone.now() + timedelta(days=2)
    m = CourseMaterial.objects.create(
        course=course,
        title="Future Lecture",
        status=MaterialStatus.SCHEDULED.value,
        scheduled_release_at=future_date,
        uploaded_by_user_id=9003,
    )
    mats = selectors.get_course_materials(course.id, CourseRole.STUDENT.value)
    assert not any(x.id == m.id for x in mats)


def test_br_test_012_announcement_faculty_permitted(course):
    """BR-TEST-012 | BR-LMS-007 permitted-faculty | Faculty is authorized to post course announcements."""
    ann = services.post_course_announcement(
        course_id=course.id,
        user_id=9003,
        user_role=CourseRole.FACULTY.value,
        title="Notice 1",
        content="Text",
    )
    assert ann.id is not None
    assert not ann.is_ta_announcement


def test_br_test_013_announcement_ta_permitted(course):
    """BR-TEST-013 | BR-LMS-007 permitted-ta | TA with can_post_announcements=True is authorized to post."""
    ann = services.post_course_announcement(
        course_id=course.id,
        user_id=3003,
        user_role=CourseRole.TA.value,
        title="TA Notice",
        content="Text",
        can_post_announcements=True,
    )
    assert ann.is_ta_announcement is True


def test_br_test_014_announcement_ta_prohibited(course):
    """BR-TEST-014 | BR-LMS-007 prohibited-ta | TA without permission is prohibited from posting announcements."""
    with pytest.raises(TAAuthoringRestriction):
        services.post_course_announcement(
            course_id=course.id,
            user_id=3003,
            user_role=CourseRole.TA.value,
            title="Unauthorized Notice",
            content="Text",
            can_post_announcements=False,
        )


def test_br_test_015_announcement_timestamp_coursewide(course):
    """BR-TEST-015 | BR-LMS-008 course-wide | Announcements have automatic timestamp and course-wide visibility."""
    ann = CourseAnnouncement.objects.create(
        course=course, title="Broad Notice", content="Notice for all", posted_by_user_id=9003
    )
    assert ann.posted_at is not None
    anns = selectors.get_course_announcements(course.id)
    assert any(a.title == "Broad Notice" for a in anns)


def test_br_test_016_assignment_config_permitted(course):
    """BR-TEST-016 | BR-LMS-009 permitted | Assignment config with positive points and valid due date passes."""
    due = timezone.now() + timedelta(days=5)
    rules.validate_assignment_configuration("Valid HW", Decimal("100.00"), "file", due)


def test_br_test_017_assignment_config_prohibited(course):
    """BR-TEST-017 | BR-LMS-009 prohibited | Assignment with non-positive points is rejected."""
    due = timezone.now() + timedelta(days=5)
    with pytest.raises(InvalidAssignmentState):
        rules.validate_assignment_configuration("Bad HW", Decimal("0.00"), "file", due)


def test_br_test_018_assignment_draft_holding(course):
    """BR-TEST-018 | BR-LMS-010 draft-holding | Assignment in draft state is omitted from student view."""
    Assignment.objects.create(
        course=course,
        title="Draft Only",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.DRAFT.value,
        created_by_user_id=9003,
    )
    asgns = selectors.get_course_assignments(course.id, CourseRole.STUDENT.value)
    assert not any(a.title == "Draft Only" for a in asgns)


def test_br_test_019_assignment_scheduled_threshold_le(course):
    """BR-TEST-019 | BR-LMS-011 threshold-le | Assignment scheduled_release_at <= now becomes eligible."""
    past = timezone.now() - timedelta(minutes=1)
    rules.validate_submission_eligibility(AssignmentStatus.SCHEDULED.value, timezone.now(), past)


def test_br_test_020_assignment_scheduled_threshold_gt(course):
    """BR-TEST-020 | BR-LMS-011 threshold-gt | Assignment scheduled_release_at > now remains unavailable."""
    future = timezone.now() + timedelta(days=2)
    with pytest.raises(InvalidAssignmentState):
        rules.validate_submission_eligibility(
            AssignmentStatus.SCHEDULED.value, timezone.now(), future
        )


def test_br_test_021_submission_type_permitted(course):
    """BR-TEST-021 | BR-LMS-012 permitted | Submission conforming to assignment submission_type passes."""
    rules.validate_submission_type("text", "text")


def test_br_test_022_submission_type_prohibited(course):
    """BR-TEST-022 | BR-LMS-012 prohibited | Submission violating submission_type is rejected."""
    with pytest.raises(SubmissionTypeError):
        rules.validate_submission_type("file", "text")


def test_br_test_023_submission_timeliness_on_time(course):
    """BR-TEST-023 | BR-LMS-013 threshold-on-time | Submission at or before due date evaluated as submitted."""
    due = timezone.now() + timedelta(hours=2)
    sub_time = timezone.now()
    res = rules.evaluate_submission_timeliness(due, sub_time)
    assert res == SubmissionStatus.SUBMITTED.value


def test_br_test_024_submission_timeliness_late(course):
    """BR-TEST-024 | BR-LMS-013 threshold-late | Submission after due date evaluated as late."""
    due = timezone.now() - timedelta(hours=2)
    sub_time = timezone.now()
    res = rules.evaluate_submission_timeliness(due, sub_time)
    assert res == SubmissionStatus.LATE.value


def test_br_test_025_submission_ownership_permitted(course):
    """BR-TEST-025 | BR-LMS-014 permitted | Student is permitted to view their own submission record."""
    rules.validate_submission_ownership(2003, 2003, CourseRole.STUDENT.value)


def test_br_test_026_submission_ownership_prohibited(course):
    """BR-TEST-026 | BR-LMS-014 prohibited | Student is prohibited from accessing another student submission."""
    with pytest.raises(SubmissionOwnershipError):
        rules.validate_submission_ownership(2003, 9999, CourseRole.STUDENT.value)


def test_br_test_027_grading_authority_faculty(course):
    """BR-TEST-027 | BR-LMS-015 permitted-faculty | Faculty has grading authority."""
    rules.validate_grading_authority(CourseRole.FACULTY.value)


def test_br_test_028_grading_authority_ta(course):
    """BR-TEST-028 | BR-LMS-015 permitted-ta | TA has grading authority."""
    rules.validate_grading_authority(CourseRole.TA.value)


def test_br_test_029_draft_grade_hidden_from_student(course):
    """BR-TEST-029 | BR-LMS-016 draft-hidden | Draft grades are strictly hidden from students."""
    with pytest.raises(GradeNotReleasedError):
        rules.validate_grade_visibility_for_student(
            GradeStatus.DRAFT.value, CourseRole.STUDENT.value
        )


def test_br_test_030_grade_release_authority_faculty(course):
    """BR-TEST-030 | BR-LMS-017 permitted-faculty | Faculty has grade release authority."""
    rules.validate_grade_release_authority(CourseRole.FACULTY.value)


def test_br_test_031_grade_release_authority_ta_prohibited(course):
    """BR-TEST-031 | BR-LMS-017 prohibited-ta | TA is prohibited from releasing grades."""
    with pytest.raises(UnauthorizedGradingError):
        rules.validate_grade_release_authority(CourseRole.TA.value)


def test_br_test_032_released_grade_visible_to_student(course):
    """BR-TEST-032 | BR-LMS-018 released-visible | Released grades and feedback are readable by student."""
    rules.validate_grade_visibility_for_student(
        GradeStatus.RELEASED.value, CourseRole.STUDENT.value
    )


def test_br_test_033_grade_change_audit_log(course):
    """BR-TEST-033 | BR-LMS-019 audit-logged | Modification of released grade generates immutable GradeChangeLog."""
    asgn = Assignment.objects.create(
        course=course,
        title="Kernel Test",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.AVAILABLE.value,
        created_by_user_id=9003,
    )
    sub = StudentSubmission.objects.create(
        assignment=asgn,
        student_user_id=2003,
        submission_type="text",
        submission_content="Work",
        status=SubmissionStatus.SUBMITTED.value,
    )
    g = Grade.objects.create(
        submission=sub,
        points=Decimal("75.00"),
        status=GradeStatus.RELEASED.value,
        graded_by_user_id=9003,
        released_by_user_id=9003,
    )
    services.modify_released_grade(
        grade_id=g.id,
        modifier_user_id=9003,
        modifier_role=CourseRole.FACULTY.value,
        new_points=Decimal("85.00"),
        reason="Rechecked Question 4",
    )
    logs = selectors.get_grade_change_logs(g.id)
    assert len(logs) == 1
    assert logs[0].old_points == Decimal("75.00")
    assert logs[0].new_points == Decimal("85.00")
    assert logs[0].reason == "Rechecked Question 4"


def test_br_test_034_unenrolled_user_publish_defect(stub_iam, course):
    """BR-TEST-034 | BR-LMS-001 prohibited-api-defect | Unenrolled user publish defect in AssignmentPublishView."""
    asgn = Assignment.objects.create(
        course=course,
        title="OS Draft Assignment",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=5),
        status=AssignmentStatus.DRAFT.value,
        created_by_user_id=9003,
    )
    c = _client(stub_iam, permissions=("lms.view", "lms.assignment.create"), uid=8888)
    res = c.post(
        f"/api/v1/lms/assignments/{asgn.id}/publish/", {"is_scheduled": False}, format="json"
    )
    # Expected by BR-LMS-001: HTTP 403 Forbidden
    # Candidate Defect: API defaults membership.role to 'faculty' when membership is None and publishes assignment!
    assert res.status_code == 403, (
        f"Candidate Defect: Unenrolled user published assignment! Got {res.status_code}"
    )
