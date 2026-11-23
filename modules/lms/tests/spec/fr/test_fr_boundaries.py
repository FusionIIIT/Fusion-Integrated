"""Specification tests for LMS TA and Observer boundary functional requirements.

Covers:
- TC-FR-039 / AFR-LMS-014.1: TA views course content (CFR-LMS-014)
- TC-FR-040 / AFR-LMS-014.2: TA views submissions (CFR-LMS-014)
- TC-FR-041 / AFR-LMS-014.3: TA cannot author assignments (CFR-LMS-014)
- TC-FR-042 / AFR-LMS-014.4: TA cannot author materials (CFR-LMS-014)
- TC-FR-043 / AFR-LMS-014.5: TA cannot modify course structure (CFR-LMS-014)
- TC-FR-044 / AFR-LMS-015.1: Observer reads permitted course content (CFR-LMS-015)
- TC-FR-045 / AFR-LMS-015.2: Observer cannot view submissions (CFR-LMS-015)
- TC-FR-046 / AFR-LMS-015.3: Observer cannot view grades/student-specific data (CFR-LMS-015)
- TC-FR-047 / AFR-LMS-015.4: Observer has no write access (CFR-LMS-015)
"""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms import selectors
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
from modules.lms.registry import _OBSERVER, _TA

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


def _setup_boundary_world(course_id: int = 101):
    now = timezone.now()
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"C{course_id}",
        title="Distributed Systems",
        syllabus="Consensus, Replication, Fault Tolerance",
        schedule_info="MWF 14:00-15:30",
    )
    # Instructor
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=2001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=3001,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_grade=True,
    )
    # Student
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # Observer
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=4001,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )

    mat = CourseMaterial.objects.create(
        course_id=course_id,
        title="Raft Paper",
        material_type=MaterialType.LINK,
        external_url="https://raft.github.io/raft.pdf",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=2001,
    )

    ann = CourseAnnouncement.objects.create(
        course_id=course_id,
        title="Welcome to Distributed Systems",
        content="First lecture slides are posted.",
        author_id=2001,
        author_role=CourseRole.INSTRUCTOR,
    )

    asg = Assignment.objects.create(
        course_id=course_id,
        title="Lab 1: MapReduce",
        instructions="Implement worker and coordinator.",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=2001,
    )

    sub = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=1001,
        submission_type=SubmissionType.TEXT,
        content_text="MapReduce coordinator implementation.",
    )

    grade = SubmissionGrade.objects.create(
        submission=sub,
        points_awarded=Decimal("92.00"),
        feedback_text="Good concurrency handling.",
        status=GradeStatus.PUBLISHED,
        graded_by=3001,
        published_by=2001,
        published_at=now,
    )

    return {
        "workspace": ws,
        "material": mat,
        "announcement": ann,
        "assignment": asg,
        "submission": sub,
        "grade": grade,
    }


def test_tc_fr_039_ta_views_course_content(stub_iam):
    """Test ID: TC-FR-039.

    Source ID: AFR-LMS-014.1: TA views course content (CFR-LMS-014)
    Purpose: Verify that an assigned TA can view course details, published materials,
    and announcements.
    """
    world = _setup_boundary_world(101)
    client = _make_client(
        stub_iam, user_id=3001, perms=_TA, kind="student", role="teaching_assistant"
    )

    # 1. Course details
    resp_ws = client.get("/api/v1/lms/courses/101/")
    assert resp_ws.status_code == 200
    assert resp_ws.json()["course_code"] == "C101"

    # 2. Published materials
    resp_mat = client.get("/api/v1/lms/materials/?course_id=101")
    assert resp_mat.status_code == 200
    assert any(m["id"] == world["material"].id for m in resp_mat.json())

    # 3. Announcements
    resp_ann = client.get("/api/v1/lms/announcements/?course_id=101")
    assert resp_ann.status_code == 200
    assert any(a["id"] == world["announcement"].id for a in resp_ann.json())


def test_tc_fr_040_ta_views_submissions(stub_iam):
    """Test ID: TC-FR-040.

    Source ID: AFR-LMS-014.2: TA views submissions (CFR-LMS-014)
    Purpose: Verify that an assigned TA can view Student submissions for their
    assigned course.
    """
    world = _setup_boundary_world(101)
    client = _make_client(
        stub_iam, user_id=3001, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client.get(f"/api/v1/lms/assignments/{world['assignment'].id}/submissions/")
    assert resp.status_code == 200
    submissions = resp.json()
    assert len(submissions) >= 1
    assert any(s["id"] == world["submission"].id for s in submissions)


def test_tc_fr_041_ta_cannot_author_assignments(stub_iam):
    """Test ID: TC-FR-041.

    Source ID: AFR-LMS-014.3: TA cannot author assignments (CFR-LMS-014)
    Purpose: Verify that the system prevents a TA from creating or editing assignments.
    """
    world = _setup_boundary_world(101)
    client = _make_client(
        stub_iam, user_id=3001, perms=_TA, kind="student", role="teaching_assistant"
    )

    # Attempt to create assignment
    resp_create = client.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "TA Created Assignment",
            "instructions": "Attempt by TA",
            "points_possible": "100.00",
            "submission_type": SubmissionType.TEXT,
            "due_date": (timezone.now() + timedelta(days=5)).isoformat(),
        },
        format="json",
    )
    assert resp_create.status_code == 403

    # Attempt to edit assignment
    resp_edit = client.patch(
        f"/api/v1/lms/assignments/{world['assignment'].id}/",
        data={"title": "TA Edited Title"},
        format="json",
    )
    assert resp_edit.status_code == 403

    # Domain rule check
    assert rules.can_author_assignment(CourseRole.TA) is False


def test_tc_fr_042_ta_cannot_author_materials(stub_iam):
    """Test ID: TC-FR-042.

    Source ID: AFR-LMS-014.4: TA cannot author materials (CFR-LMS-014)
    Purpose: Verify that the system prevents a TA from creating or editing course materials.
    """
    world = _setup_boundary_world(101)
    client = _make_client(
        stub_iam, user_id=3001, perms=_TA, kind="student", role="teaching_assistant"
    )

    # Attempt to create material
    resp_create = client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": 101,
            "title": "TA Material Upload Attempt",
            "material_type": MaterialType.NOTE,
            "content_text": "Forbidden",
        },
        format="json",
    )
    assert resp_create.status_code == 403

    # Attempt to edit material
    resp_edit = client.patch(
        f"/api/v1/lms/materials/{world['material'].id}/",
        data={"title": "TA Altered Material"},
        format="json",
    )
    assert resp_edit.status_code == 403

    # Domain rule check
    assert rules.can_author_material(CourseRole.TA) is False


def test_tc_fr_043_ta_cannot_modify_course_structure(stub_iam):
    """Test ID: TC-FR-043.

    Source ID: AFR-LMS-014.5: TA cannot modify course structure (CFR-LMS-014)
    Purpose: Verify that the system prevents a TA from modifying course structure.
    """
    _setup_boundary_world(101)
    client = _make_client(
        stub_iam, user_id=3001, perms=_TA, kind="student", role="teaching_assistant"
    )

    resp = client.patch(
        "/api/v1/lms/courses/101/",
        data={"syllabus": "TA Modified Syllabus"},
        format="json",
    )
    assert resp.status_code == 403

    # Domain rule check
    assert rules.can_manage_workspace(CourseRole.TA) is False


def test_tc_fr_044_observer_reads_permitted_course_content(stub_iam):
    """Test ID: TC-FR-044.

    Source ID: AFR-LMS-015.1: Observer reads permitted course content (CFR-LMS-015)
    Purpose: Verify that an Observer can view course details, published materials,
    and announcements for the linked course in read-only form.
    """
    world = _setup_boundary_world(101)
    client = _make_client(
        stub_iam, user_id=4001, perms=_OBSERVER, kind="student", role="course_observer"
    )

    # 1. Course details
    resp_ws = client.get("/api/v1/lms/courses/101/")
    assert resp_ws.status_code == 200
    assert resp_ws.json()["course_code"] == "C101"

    # 2. Published materials
    resp_mat = client.get("/api/v1/lms/materials/?course_id=101")
    assert resp_mat.status_code == 200
    assert any(m["id"] == world["material"].id for m in resp_mat.json())

    # 3. Announcements
    resp_ann = client.get("/api/v1/lms/announcements/?course_id=101")
    assert resp_ann.status_code == 200
    assert any(a["id"] == world["announcement"].id for a in resp_ann.json())


def test_tc_fr_045_observer_cannot_view_submissions(stub_iam):
    """Test ID: TC-FR-045.

    Source ID: AFR-LMS-015.2: Observer cannot view submissions (CFR-LMS-015)
    Purpose: Verify that the system prevents an Observer from viewing individual
    Student submissions.
    """
    world = _setup_boundary_world(101)
    client = _make_client(
        stub_iam, user_id=4001, perms=_OBSERVER, kind="student", role="course_observer"
    )

    # List submissions -> 403 Forbidden (observer lacks lms.submission.view)
    resp_list = client.get(f"/api/v1/lms/assignments/{world['assignment'].id}/submissions/")
    assert resp_list.status_code == 403

    # Get submission detail -> 403 Forbidden
    resp_detail = client.get(f"/api/v1/lms/submissions/{world['submission'].id}/")
    assert resp_detail.status_code == 403

    # Verify at selector layer
    obs_principal = SimpleNamespace(
        user_id=4001,
        erp_user_id=4001,
        roles=["course_observer"],
        permissions=_OBSERVER,
    )
    assert (
        selectors.submissions.list_course_submissions(
            world["assignment"].id, obs_principal
        )
        == []
    )
    assert (
        selectors.submissions.get_student_submission(
            world["assignment"].id, obs_principal
        )
        is None
    )


def test_tc_fr_046_observer_cannot_view_grades_or_student_data(stub_iam):
    """Test ID: TC-FR-046.

    Source ID: AFR-LMS-015.3: Observer cannot view grades/student-specific data (CFR-LMS-015)
    Purpose: Verify that the system prevents an Observer from viewing student grades
    or any other Student-specific data.
    """
    world = _setup_boundary_world(101)
    client = _make_client(
        stub_iam, user_id=4001, perms=_OBSERVER, kind="student", role="course_observer"
    )

    # Grades list -> 403 Forbidden (observer lacks lms.grade.view)
    resp_grades = client.get(f"/api/v1/lms/assignments/{world['assignment'].id}/grades/")
    assert resp_grades.status_code == 403

    # Grade detail -> 403 Forbidden
    resp_grade_detail = client.get(
        f"/api/v1/lms/submissions/{world['submission'].id}/grade-detail/"
    )
    assert resp_grade_detail.status_code == 403

    # Verify at selector layer
    obs_principal = SimpleNamespace(
        user_id=4001,
        erp_user_id=4001,
        roles=["course_observer"],
        permissions=_OBSERVER,
    )
    assert (
        selectors.grading.list_course_grades(world["assignment"].id, obs_principal)
        == []
    )
    assert (
        selectors.grading.get_submission_grade(world["submission"].id, obs_principal)
        is None
    )


def test_tc_fr_047_observer_has_no_write_access(stub_iam):
    """Test ID: TC-FR-047.

    Source ID: AFR-LMS-015.4: Observer has no write access (CFR-LMS-015)
    Purpose: Verify that the system prevents an Observer from performing write
    actions anywhere in the LMS Course Management module.
    """
    world = _setup_boundary_world(101)
    client = _make_client(
        stub_iam, user_id=4001, perms=_OBSERVER, kind="student", role="course_observer"
    )

    # 1. Post announcement
    assert (
        client.post(
            "/api/v1/lms/announcements/",
            data={"course_id": 101, "title": "Obs", "content": "Obs"},
            format="json",
        ).status_code
        == 403
    )

    # 2. Upload material
    assert (
        client.post(
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

    # 3. Create assignment
    assert (
        client.post(
            "/api/v1/lms/assignments/",
            data={
                "course_id": 101,
                "title": "Obs Asg",
                "instructions": "None",
                "points_possible": 100,
                "submission_type": SubmissionType.TEXT,
                "due_date": timezone.now().isoformat(),
            },
            format="json",
        ).status_code
        == 403
    )

    # 4. Submit assignment
    assert (
        client.post(
            f"/api/v1/lms/assignments/{world['assignment'].id}/submissions/",
            data={"submission_type": SubmissionType.TEXT, "content_text": "Obs Work"},
            format="json",
        ).status_code
        == 403
    )

    # 5. Grade submission
    assert (
        client.post(
            f"/api/v1/lms/submissions/{world['submission'].id}/grade/",
            data={"points_awarded": 100},
            format="json",
        ).status_code
        == 403
    )

    # 6. Configure course workspace
    assert (
        client.patch(
            "/api/v1/lms/courses/101/",
            data={"syllabus": "Obs Syllabus"},
            format="json",
        ).status_code
        == 403
    )
