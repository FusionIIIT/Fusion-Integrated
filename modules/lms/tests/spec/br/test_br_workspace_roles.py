"""Specification business rule tests for Course-Specific Access and Role Boundaries.

Covers:
- TC-BR-001 / BR-LMS-001 permitted: Course-specific access control
- TC-BR-002 / BR-LMS-001 prohibited: Unauthorized user prohibited from course workspace
- TC-BR-003 / BR-LMS-002 permitted: Student access governed by active registration
- TC-BR-004 / BR-LMS-002 prohibited: Denied access when registration is inactive/dropped
- TC-BR-005 / BR-LMS-003 permitted: Observer permitted read-only access to course content
- TC-BR-006 / BR-LMS-003 prohibited (student data): Observer prohibited from student data
- TC-BR-007 / BR-LMS-003 prohibited (write actions): Observer prohibited from write actions
- TC-BR-008 / BR-LMS-004 permitted: Assigned TA permitted viewing and grading
- TC-BR-009 / BR-LMS-004 prohibited: Assigned TA prohibited from authoring & structure
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain import rules
from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    GradeStatus,
    MaterialStatus,
    MaterialType,
    MembershipStatus,
    SubmissionType,
)
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseAnnouncement,
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
    SubmissionGrade,
)
from modules.lms.registry import _OBSERVER, _STUDENT, _TA
from modules.lms.selectors.scoping import is_student_enrolled

pytestmark = pytest.mark.django_db


def _make_client(
    stub_iam,
    user_id: int,
    perms: list[str],
    kind: str = "student",
    role: str = "student",
) -> APIClient:
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            active_role=role,
            roles=(role,),
            modules=("lms",),
            permissions=perms,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token tok-{user_id}")
    return client


def _setup_course_world(course_id: int = 101):
    now = timezone.now()
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Algorithms",
        syllabus="Graph algorithms, Dynamic programming",
        schedule_info="MWF 10:00",
    )
    # Faculty
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=101,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=201,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_grade=True,
    )
    # Student S1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=301,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # Observer O1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=401,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )

    mat = CourseMaterial.objects.create(
        course_id=course_id,
        title="Lecture 1 Notes",
        material_type=MaterialType.NOTE,
        content_text="Intro to graphs",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=101,
    )

    ann = CourseAnnouncement.objects.create(
        course_id=course_id,
        title="Welcome to CS101",
        content="First lecture on Monday.",
        author_id=101,
        author_role=CourseRole.INSTRUCTOR,
    )

    asg = Assignment.objects.create(
        course_id=course_id,
        title="Problem Set 1",
        instructions="Solve graph problems",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    sub = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=301,
        submission_type=SubmissionType.TEXT,
        content_text="BFS and DFS implementation",
    )

    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("95.00"),
        feedback_text="Great work",
        status=GradeStatus.DRAFT,
        graded_by=201,
    )

    return {
        "workspace": ws,
        "material": mat,
        "announcement": ann,
        "assignment": asg,
        "submission": sub,
        "grade": grade,
    }


def test_tc_br_001_permitted_access_for_associated_user(stub_iam):
    """Test ID: TC-BR-001.

    Source ID: BR-LMS-001 permitted
    Purpose: Verify that a user enrolled in, assigned to, or linked to a course
    is permitted to access the course workspace.
    """
    _setup_course_world(101)
    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_s1.get("/api/v1/lms/courses/101/")
    assert resp.status_code == 200
    assert resp.json()["course_id"] == 101
    assert resp.json()["course_code"] == "CS101"


def test_tc_br_002_prohibited_access_without_course_association(stub_iam):
    """Test ID: TC-BR-002.

    Source ID: BR-LMS-001 prohibited
    Purpose: Verify that a user without an established course association is
    prohibited from accessing the course workspace.
    """
    _setup_course_world(101)
    # User U2 (user_id 999) has no membership in Course 101
    client_u2 = _make_client(
        stub_iam, user_id=999, perms=_STUDENT, kind="student", role="student"
    )

    resp = client_u2.get("/api/v1/lms/courses/101/")
    assert resp.status_code == 404
    error_msg = resp.json().get("error", {}).get("message", "")
    assert "not found or access denied" in error_msg.lower()


def test_tc_br_003_student_access_granted_with_active_registration(stub_iam):
    """Test ID: TC-BR-003.

    Source ID: BR-LMS-002 permitted
    Purpose: Verify that a Student is granted course access when existing
    Fusion course-registration records confirm active course enrollment.
    """
    _setup_course_world(101)
    from types import SimpleNamespace

    student_principal = SimpleNamespace(
        user_id=301, erp_user_id=301, roles=["student"], permissions=_STUDENT
    )

    # Validate registration data governs Student course access
    assert is_student_enrolled(101, student_principal) is True

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp = client_s1.get("/api/v1/lms/courses/101/")
    assert resp.status_code == 200
    assert resp.json()["course_id"] == 101


def test_tc_br_004_student_access_denied_without_active_registration(stub_iam):
    """Test ID: TC-BR-004.

    Source ID: BR-LMS-002 prohibited
    Purpose: Verify that student course access is denied when existing Fusion
    course-registration records indicate no active registration.
    """
    _setup_course_world(101)
    from types import SimpleNamespace

    # Student S2 has inactive membership in Course 101
    CourseMembership.objects.create(
        course_id=101,
        user_id=302,
        role=CourseRole.STUDENT,
        status=MembershipStatus.INACTIVE,
    )
    s2_principal = SimpleNamespace(
        user_id=302, erp_user_id=302, roles=["student"], permissions=_STUDENT
    )

    assert is_student_enrolled(101, s2_principal) is False

    client_s2 = _make_client(
        stub_iam, user_id=302, perms=_STUDENT, kind="student", role="student"
    )
    resp = client_s2.get("/api/v1/lms/courses/101/")
    assert resp.status_code == 404


def test_tc_br_005_observer_permitted_read_only_access(stub_iam):
    """Test ID: TC-BR-005.

    Source ID: BR-LMS-003 permitted
    Purpose: Verify that an Observer linked to a course is permitted read-only
    access to course details, published materials, and announcements.
    """
    world = _setup_course_world(101)
    client_obs = _make_client(
        stub_iam, user_id=401, perms=_OBSERVER, kind="student", role="course_observer"
    )

    # 1. Course details
    resp_course = client_obs.get("/api/v1/lms/courses/101/")
    assert resp_course.status_code == 200
    assert resp_course.json()["course_code"] == "CS101"

    # 2. Published materials
    resp_mat = client_obs.get("/api/v1/lms/materials/?course_id=101")
    assert resp_mat.status_code == 200
    assert any(m["id"] == world["material"].id for m in resp_mat.json())

    # 3. Announcements
    resp_ann = client_obs.get("/api/v1/lms/announcements/?course_id=101")
    assert resp_ann.status_code == 200
    assert any(a["id"] == world["announcement"].id for a in resp_ann.json())


def test_tc_br_006_observer_prohibited_from_student_data(stub_iam):
    """Test ID: TC-BR-006.

    Source ID: BR-LMS-003 prohibited (student data)
    Purpose: Verify that an Observer is prohibited from viewing individual
    student submissions, grades, or other student-specific data.
    """
    world = _setup_course_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    client_obs = _make_client(
        stub_iam, user_id=401, perms=_OBSERVER, kind="student", role="course_observer"
    )

    # Submissions list -> 403 Forbidden
    assert (
        client_obs.get(f"/api/v1/lms/assignments/{asg.id}/submissions/").status_code
        == 403
    )

    # Submission detail -> 403 Forbidden
    assert client_obs.get(f"/api/v1/lms/submissions/{sub.id}/").status_code == 403

    # Grades list -> 403 Forbidden
    assert client_obs.get(f"/api/v1/lms/assignments/{asg.id}/grades/").status_code == 403

    # Grade detail -> 403 Forbidden
    assert (
        client_obs.get(f"/api/v1/lms/submissions/{sub.id}/grade-detail/").status_code
        == 403
    )


def test_tc_br_007_observer_prohibited_from_write_actions(stub_iam):
    """Test ID: TC-BR-007.

    Source ID: BR-LMS-003 prohibited (write actions)
    Purpose: Verify that an Observer is prohibited from performing write or
    modification actions in the course workspace.
    """
    world = _setup_course_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    client_obs = _make_client(
        stub_iam, user_id=401, perms=_OBSERVER, kind="student", role="course_observer"
    )

    # 1. Upload material -> 403
    assert (
        client_obs.post(
            "/api/v1/lms/materials/",
            data={
                "course_id": 101,
                "title": "Obs",
                "material_type": MaterialType.NOTE,
                "content_text": "Obs",
            },
            format="json",
        ).status_code
        == 403
    )

    # 2. Post announcement -> 403
    assert (
        client_obs.post(
            "/api/v1/lms/announcements/",
            data={"course_id": 101, "title": "Obs", "content": "Obs"},
            format="json",
        ).status_code
        == 403
    )

    # 3. Submit course work -> 403
    assert (
        client_obs.post(
            f"/api/v1/lms/assignments/{asg.id}/submissions/",
            data={"submission_type": SubmissionType.TEXT, "content_text": "Obs"},
            format="json",
        ).status_code
        == 403
    )

    # 4. Grade submission -> 403
    assert (
        client_obs.post(
            f"/api/v1/lms/submissions/{sub.id}/grade/",
            data={"points_awarded": 100},
            format="json",
        ).status_code
        == 403
    )

    # Preserves workspace state
    assert CourseMaterial.objects.filter(course_id=101).count() == 1
    assert CourseAnnouncement.objects.filter(course_id=101).count() == 1


def test_tc_br_008_assigned_ta_permitted_viewing_and_grading(stub_iam):
    """Test ID: TC-BR-008.

    Source ID: BR-LMS-004 permitted
    Purpose: Verify that an assigned Teaching Assistant (TA) is permitted to
    view course content, view student submissions, and grade submissions.
    """
    world = _setup_course_world(101)
    asg = world["assignment"]
    sub = world["submission"]

    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )

    # 1. View course materials
    resp_mat = client_ta.get("/api/v1/lms/materials/?course_id=101")
    assert resp_mat.status_code == 200
    assert any(m["id"] == world["material"].id for m in resp_mat.json())

    # 2. View student submissions
    resp_sub = client_ta.get(f"/api/v1/lms/assignments/{asg.id}/submissions/")
    assert resp_sub.status_code == 200
    assert any(s["id"] == sub.id for s in resp_sub.json())

    # 3. Grade submission
    resp_grade = client_ta.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        data={
            "points_awarded": "88.00",
            "feedback_text": "Graded by assigned TA",
        },
        format="json",
    )
    assert resp_grade.status_code == 200
    assert Decimal(str(resp_grade.json()["points_awarded"])) == Decimal("88.00")

    sub_grade = SubmissionGrade.objects.get(submission=sub)
    assert sub_grade.points_awarded == Decimal("88.00")
    assert sub_grade.graded_by == 201


def test_tc_br_009_assigned_ta_prohibited_from_authoring_and_structure(stub_iam):
    """Test ID: TC-BR-009.

    Source ID: BR-LMS-004 prohibited
    Purpose: Verify that an assigned TA is prohibited from creating or editing
    assignments, course materials, or course structure.
    """
    _setup_course_world(101)
    now = timezone.now()

    client_ta = _make_client(
        stub_iam, user_id=201, perms=_TA, kind="student", role="teaching_assistant"
    )

    # 1. Attempt create assignment -> 403
    assert (
        client_ta.post(
            "/api/v1/lms/assignments/",
            data={
                "course_id": 101,
                "title": "TA Assignment",
                "instructions": "Instructions",
                "points_possible": "100.00",
                "submission_type": SubmissionType.TEXT,
                "due_date": (now + timedelta(days=5)).isoformat(),
            },
            format="json",
        ).status_code
        == 403
    )

    # 2. Attempt upload material -> 403
    assert (
        client_ta.post(
            "/api/v1/lms/materials/",
            data={
                "course_id": 101,
                "title": "TA Material",
                "material_type": MaterialType.NOTE,
                "content_text": "Content",
            },
            format="json",
        ).status_code
        == 403
    )

    # 3. Attempt modify course workspace structure -> 403
    assert (
        client_ta.patch(
            "/api/v1/lms/courses/101/",
            data={"syllabus": "TA Altered Syllabus"},
            format="json",
        ).status_code
        == 403
    )

    # Domain rules verification
    assert rules.can_author_assignment(CourseRole.TA) is False
    assert rules.can_author_material(CourseRole.TA) is False
    assert rules.can_manage_workspace(CourseRole.TA) is False
