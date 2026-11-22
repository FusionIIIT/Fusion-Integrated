"""Tests for Course Grades, Evaluation, Feedback, Grade Release, and Audit (UC-LMS-012, UC-LMS-013, UC-LMS-014, BR-LMS-015, BR-LMS-016, BR-LMS-017, BR-LMS-018, BR-LMS-019)."""
from datetime import timedelta
from decimal import Decimal
import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.courses.models import (
    CourseAssignment,
    CourseGrade,
    CourseGradeAudit,
    CourseSubmission,
)
from modules.courses.permissions import P_WORKSPACE_MANAGE, P_WORKSPACE_VIEW
from modules.courses.tests.factories import add_member, make_workspace


def _auth_client(stub_iam, **session_kw):
    session_kw.setdefault("modules", ("courses",))
    stub_iam(make_session(**session_kw))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


@pytest.fixture(autouse=True)
def media_storage_temp(tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        yield


@pytest.fixture
def grade_setup():
    ws1 = make_workspace(code="CS401", title="Algorithms")
    ws2 = make_workspace(code="CS501", title="Compiler Design")

    # Faculty instructor: user 10
    add_member(ws1, user_id=10, role="instructor")
    # TA: user 20
    add_member(ws1, user_id=20, role="ta")
    # Student 1: user 30
    add_member(ws1, user_id=30, role="student")
    # Student 2: user 31
    add_member(ws1, user_id=31, role="student")
    # Observer: user 40
    add_member(ws1, user_id=40, role="observer")

    # ws2 members:
    add_member(ws2, user_id=99, role="instructor")
    add_member(ws2, user_id=98, role="student")

    # Assignment in ws1 with max_points 100.00
    now = timezone.now()
    asgn1 = CourseAssignment.objects.create(
        workspace=ws1,
        title="Dynamic Programming",
        description="Solve DP problems",
        instructions="Submit your solution",
        max_points=Decimal("100.00"),
        is_published=True,
        published_at=now - timedelta(days=2),
        due_at=now + timedelta(days=5),
        created_by_id=10,
    )

    # Student 30 submission
    sub1 = CourseSubmission.objects.create(
        workspace=ws1,
        assignment=asgn1,
        student_id=30,
        submission_type="text",
        content="DP solution in O(N^2)",
        submitted_at=now - timedelta(hours=2),
        is_late=False,
        attempt_number=1,
        status="submitted",
    )

    # Assignment in ws2
    asgn2 = CourseAssignment.objects.create(
        workspace=ws2,
        title="Parser Generation",
        max_points=Decimal("50.00"),
        is_published=True,
        created_by_id=99,
    )
    sub2 = CourseSubmission.objects.create(
        workspace=ws2,
        assignment=asgn2,
        student_id=98,
        submission_type="text",
        content="LR(1) grammar",
        submitted_at=now - timedelta(hours=1),
        is_late=False,
        attempt_number=1,
        status="submitted",
    )

    return {
        "ws1": ws1,
        "ws2": ws2,
        "asgn1": asgn1,
        "asgn2": asgn2,
        "sub1": sub1,
        "sub2": sub2,
    }


@pytest.mark.django_db
def test_faculty_grades_submission(stub_iam, grade_setup):
    """Faculty can grade submission, saving score and feedback in draft state (UC-LMS-012, BR-LMS-015, BR-LMS-016)."""
    ws = grade_setup["ws1"]
    asgn = grade_setup["asgn1"]
    sub = grade_setup["sub1"]

    client = _auth_client(
        stub_iam,
        user_id=10,
        permissions=[P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE],
    )

    url = f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade"
    res = client.post(url, {"score": "88.50", "feedback": "Good memoization strategy."}, format="json")

    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["score"] == "88.50"
    assert data["feedback"] == "Good memoization strategy."
    assert data["status"] == "draft"
    assert data["grader_id"] == 10

    # Verify database persistence
    grade = CourseGrade.objects.get(submission=sub)
    assert grade.score == Decimal("88.50")
    assert grade.status == "draft"
    assert grade.grader_id == 10

    # Verify initial audit trail
    assert CourseGradeAudit.objects.filter(grade=grade, action="graded", actor_id=10).exists()


@pytest.mark.django_db
def test_ta_grades_submission_with_attribution(stub_iam, grade_setup):
    """TA can grade submission, with grading action explicitly attributed to the TA (BR-LMS-015)."""
    ws = grade_setup["ws1"]
    asgn = grade_setup["asgn1"]
    sub = grade_setup["sub1"]

    client = _auth_client(
        stub_iam,
        user_id=20,
        permissions=[P_WORKSPACE_VIEW],
    )

    url = f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade"
    res = client.post(url, {"score": "92.00", "feedback": "Clear test cases included."}, format="json")

    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["score"] == "92.00"
    assert data["grader_id"] == 20  # Explicit TA attribution
    assert data["status"] == "draft"

    grade = CourseGrade.objects.get(submission=sub)
    assert grade.grader_id == 20


@pytest.mark.django_db
def test_student_and_observer_cannot_grade(stub_iam, grade_setup):
    """Students and observers are strictly prohibited from grading (BR-LMS-003, BR-LMS-015)."""
    ws = grade_setup["ws1"]
    asgn = grade_setup["asgn1"]
    sub = grade_setup["sub1"]
    url = f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade"

    # Student attempt
    client_student = _auth_client(stub_iam, user_id=30, permissions=[P_WORKSPACE_VIEW])
    res_student = client_student.post(url, {"score": "100.00", "feedback": "Self full marks"}, format="json")
    assert res_student.status_code == status.HTTP_403_FORBIDDEN

    # Observer attempt
    client_obs = _auth_client(stub_iam, user_id=40, permissions=[P_WORKSPACE_VIEW])
    res_obs = client_obs.post(url, {"score": "75.00", "feedback": "Observer comment"}, format="json")
    assert res_obs.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_score_validation(stub_iam, grade_setup):
    """Score must be non-negative and not exceed maximum points possible."""
    ws = grade_setup["ws1"]
    asgn = grade_setup["asgn1"]
    sub = grade_setup["sub1"]
    url = f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade"

    client = _auth_client(stub_iam, user_id=10, permissions=[P_WORKSPACE_VIEW])

    # Negative score
    res_neg = client.post(url, {"score": "-5.00", "feedback": "Negative marks"}, format="json")
    assert res_neg.status_code == status.HTTP_400_BAD_REQUEST

    # Exceeding max points (100.00)
    res_high = client.post(url, {"score": "150.00", "feedback": "Over max"}, format="json")
    assert res_high.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_cross_workspace_isolation(stub_iam, grade_setup):
    """Grading submission from another workspace must be rejected."""
    ws1 = grade_setup["ws1"]
    asgn1 = grade_setup["asgn1"]
    sub2 = grade_setup["sub2"]  # Sub2 is in ws2!

    client = _auth_client(stub_iam, user_id=10, permissions=[P_WORKSPACE_VIEW])
    url = f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions/{sub2.id}/grade"
    res = client.post(url, {"score": "80.00", "feedback": "Wrong workspace"}, format="json")
    assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
def test_draft_grade_hidden_from_student(stub_iam, grade_setup):
    """Draft grades and feedback must be completely hidden from students (BR-LMS-016)."""
    ws = grade_setup["ws1"]
    asgn = grade_setup["asgn1"]
    sub = grade_setup["sub1"]

    # Grade submission in draft state
    faculty_client = _auth_client(stub_iam, user_id=10, permissions=[P_WORKSPACE_VIEW])
    faculty_client.post(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade",
        {"score": "78.00", "feedback": "Confidential draft notes"},
        format="json",
    )

    # Student retrieves own submission
    student_client = _auth_client(stub_iam, user_id=30, permissions=[P_WORKSPACE_VIEW])
    res = student_client.get(f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/mine")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["grade"] is None  # Must NOT leak unreleased grade!


@pytest.mark.django_db
def test_ta_cannot_release_grades(stub_iam, grade_setup):
    """TAs are explicitly prohibited from releasing grades (BR-LMS-017, UC-LMS-013)."""
    ws = grade_setup["ws1"]
    asgn = grade_setup["asgn1"]
    sub = grade_setup["sub1"]

    # Faculty grades
    faculty_client = _auth_client(stub_iam, user_id=10, permissions=[P_WORKSPACE_VIEW])
    faculty_client.post(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade",
        {"score": "85.00", "feedback": "Draft score"},
        format="json",
    )

    # TA attempts to release grades
    ta_client = _auth_client(stub_iam, user_id=20, permissions=[P_WORKSPACE_VIEW])
    res_ta = ta_client.post(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/release-grades",
        {},
        format="json",
    )
    assert res_ta.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_faculty_grade_release_and_student_read_only(stub_iam, grade_setup):
    """Faculty releases grades, making score and feedback visible to student in read-only form (UC-LMS-013, BR-LMS-018, UC-LMS-014)."""
    ws = grade_setup["ws1"]
    asgn = grade_setup["asgn1"]
    sub = grade_setup["sub1"]

    # 1. Faculty grades
    faculty_client = _auth_client(stub_iam, user_id=10, permissions=[P_WORKSPACE_VIEW])
    faculty_client.post(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade",
        {"score": "94.50", "feedback": "Excellent DP table formulation."},
        format="json",
    )

    # 2. Faculty releases grades
    rel_res = faculty_client.post(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/release-grades",
        {},
        format="json",
    )
    assert rel_res.status_code == status.HTTP_200_OK
    rel_data = rel_res.json()
    assert rel_data["released_count"] == 1

    # Database check
    grade = CourseGrade.objects.get(submission=sub)
    assert grade.status == "released"
    assert grade.released_by_id == 10
    assert grade.released_at is not None

    # 3. Student views own released grade (UC-LMS-014, BR-LMS-018)
    student_client = _auth_client(stub_iam, user_id=30, permissions=[P_WORKSPACE_VIEW])
    stu_res = student_client.get(f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/mine")
    assert stu_res.status_code == status.HTTP_200_OK
    stu_data = stu_res.json()
    assert stu_data["grade"] is not None
    assert stu_data["grade"]["score"] == "94.50"
    assert stu_data["grade"]["feedback"] == "Excellent DP table formulation."
    assert stu_data["grade"]["status"] == "released"

    # Other student (user 31) cannot see user 30's grade
    other_student = _auth_client(stub_iam, user_id=31, permissions=[P_WORKSPACE_VIEW])
    other_res = other_student.get(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}"
    )
    assert other_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_post_release_grade_change_audit(stub_iam, grade_setup):
    """Post-release grade modification logs an audit record recording who made the change and when (BR-LMS-019)."""
    ws = grade_setup["ws1"]
    asgn = grade_setup["asgn1"]
    sub = grade_setup["sub1"]

    faculty_client = _auth_client(stub_iam, user_id=10, permissions=[P_WORKSPACE_VIEW])

    # Grade and release
    faculty_client.post(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade",
        {"score": "80.00", "feedback": "Original evaluation."},
        format="json",
    )
    faculty_client.post(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/release-grades",
        {},
        format="json",
    )

    # Modify grade after release
    mod_res = faculty_client.post(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade",
        {"score": "88.00", "feedback": "Re-evaluated after reviewing corner cases."},
        format="json",
    )
    assert mod_res.status_code == status.HTTP_200_OK

    # Verify audit record
    audit = CourseGradeAudit.objects.filter(
        grade__submission=sub,
        action="updated_post_release",
    ).first()
    assert audit is not None
    assert audit.actor_id == 10
    assert audit.score_before == Decimal("80.00")
    assert audit.score_after == Decimal("88.00")
    assert audit.feedback_before == "Original evaluation."
    assert audit.feedback_after == "Re-evaluated after reviewing corner cases."

    # Verify audit API access
    audit_res = faculty_client.get(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade-audit"
    )
    assert audit_res.status_code == status.HTTP_200_OK
    audit_list = audit_res.json()
    assert len(audit_list) >= 1

    # Student cannot view audit logs
    student_client = _auth_client(stub_iam, user_id=30, permissions=[P_WORKSPACE_VIEW])
    stu_audit = student_client.get(
        f"/api/v1/courses/workspaces/{ws.id}/assignments/{asgn.id}/submissions/{sub.id}/grade-audit"
    )
    assert stu_audit.status_code == status.HTTP_403_FORBIDDEN
