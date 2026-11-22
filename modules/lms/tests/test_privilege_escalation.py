"""Tests for LMS role boundaries and privilege escalation defenses."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    MembershipStatus,
    SubmissionType,
)
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseMembership,
    CourseWorkspace,
)
from modules.lms.registry import _FACULTY, _OBSERVER, _STUDENT, _TA

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_setup():
    now = timezone.now()
    # Course A
    ws_a = CourseWorkspace.objects.create(
        course_id=501,
        course_code="CS501",
        title="Course A",
        syllabus="Syllabus A",
    )
    # Course B
    ws_b = CourseWorkspace.objects.create(
        course_id=502,
        course_code="CS502",
        title="Course B",
        syllabus="Syllabus B",
    )

    # Memberships in Course A
    # Instructor: user 6001
    CourseMembership.objects.create(
        course_id=501,
        user_id=6001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA allowed: user 6002
    CourseMembership.objects.create(
        course_id=501,
        user_id=6002,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=True,
        can_grade=True,
    )
    # TA restricted: user 6003
    CourseMembership.objects.create(
        course_id=501,
        user_id=6003,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_post_announcement=False,
        can_grade=False,
    )
    # Student 1: user 7001
    CourseMembership.objects.create(
        course_id=501,
        user_id=7001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # Student 2: user 7002
    CourseMembership.objects.create(
        course_id=501,
        user_id=7002,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # Observer: user 8001
    CourseMembership.objects.create(
        course_id=501,
        user_id=8001,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )

    # Assignment in Course A
    ass_a = Assignment.objects.create(
        course_id=501,
        title="Assignment 1",
        instructions="Instructions A",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=6001,
    )
    # Submissions
    sub1 = AssignmentSubmission.objects.create(
        assignment=ass_a,
        student_id=7001,
        submission_type=SubmissionType.TEXT,
        content_text="Student 1 Work",
    )
    sub2 = AssignmentSubmission.objects.create(
        assignment=ass_a,
        student_id=7002,
        submission_type=SubmissionType.TEXT,
        content_text="Student 2 Work",
    )

    # Assignment and Submissions in Course B
    ass_b = Assignment.objects.create(
        course_id=502,
        title="Assignment B",
        instructions="Instructions B",
        points_possible=Decimal("50.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=9999,
    )
    sub_b = AssignmentSubmission.objects.create(
        assignment=ass_b,
        student_id=9001,
        submission_type=SubmissionType.TEXT,
        content_text="Student B Work",
    )

    return {
        "ws_a": ws_a,
        "ws_b": ws_b,
        "ass_a": ass_a,
        "ass_b": ass_b,
        "sub1": sub1,
        "sub2": sub2,
        "sub_b": sub_b,
    }


def _auth_client(stub_iam, uid, perms, kind="student", role="student"):
    stub_iam(
        make_session(
            user_id=uid,
            kind=kind,
            active_role=role,
            roles=(role,),
            modules=("lms",),
            permissions=perms,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_student_cannot_perform_staff_actions(stub_iam, test_setup):
    c = _auth_client(stub_iam, uid=7001, perms=_STUDENT, kind="student", role="student")
    ass_a = test_setup["ass_a"]
    sub2 = test_setup["sub2"]

    # Student cannot create assignments
    r = c.post(
        "/api/v1/lms/assignments/",
        {
            "course_id": 501,
            "title": "Hacked Assignment",
            "instructions": "None",
            "points_possible": 100,
            "submission_type": "TEXT",
            "due_date": timezone.now().isoformat(),
        },
    )
    assert r.status_code == 403

    # Student cannot publish assignments
    r = c.post(f"/api/v1/lms/assignments/{ass_a.id}/publish/", {})
    assert r.status_code == 403

    # Student cannot post announcements
    r = c.post(
        "/api/v1/lms/announcements/",
        {
            "course_id": 501,
            "title": "Spam",
            "content": "Spam content",
        },
    )
    assert r.status_code == 403

    # Student cannot upload materials
    r = c.post(
        "/api/v1/lms/materials/",
        {
            "course_id": 501,
            "title": "Spam Material",
            "material_type": "LINK",
            "external_url": "https://example.com",
        },
    )
    assert r.status_code == 403

    # Student cannot grade peer submissions
    r = c.post(
        f"/api/v1/lms/submissions/{sub2.id}/grade/",
        {
            "points_awarded": 100,
            "feedback_text": "Hacked",
        },
    )
    assert r.status_code == 403

    # Student cannot publish grades
    r = c.post(f"/api/v1/lms/assignments/{ass_a.id}/publish-grades/", {})
    assert r.status_code == 403

    # Student cannot inspect peer's submission detail
    r = c.get(f"/api/v1/lms/submissions/{sub2.id}/")
    assert r.status_code == 404


def test_ta_cannot_perform_faculty_actions(stub_iam, test_setup):
    c = _auth_client(stub_iam, uid=6002, perms=_TA, kind="student", role="teaching_assistant")
    ass_a = test_setup["ass_a"]

    # TA cannot publish grades (faculty-only BR-LMS-017)
    r = c.post(f"/api/v1/lms/assignments/{ass_a.id}/publish-grades/", {})
    assert r.status_code == 403

    # TA cannot create assignments
    r = c.post(
        "/api/v1/lms/assignments/",
        {
            "course_id": 501,
            "title": "TA Assignment",
            "instructions": "None",
            "points_possible": 100,
            "submission_type": "TEXT",
            "due_date": timezone.now().isoformat(),
        },
    )
    assert r.status_code == 403

    # TA cannot create materials
    r = c.post(
        "/api/v1/lms/materials/",
        {
            "course_id": 501,
            "title": "TA Material",
            "material_type": "LINK",
            "external_url": "https://example.com",
        },
    )
    assert r.status_code == 403


def test_ta_restricted_flags_enforced(stub_iam, test_setup):
    # TA 6003 has can_post_announcement=False and can_grade=False in course membership
    c = _auth_client(stub_iam, uid=6003, perms=_TA, kind="student", role="teaching_assistant")
    sub1 = test_setup["sub1"]

    # Attempting to post announcement fails with 403
    r = c.post(
        "/api/v1/lms/announcements/",
        {
            "course_id": 501,
            "title": "Unauthorized Announcement",
            "content": "Should be rejected",
        },
    )
    assert r.status_code == 403

    # Attempting to grade fails with 403
    r = c.post(
        f"/api/v1/lms/submissions/{sub1.id}/grade/",
        {
            "points_awarded": 85,
            "feedback_text": "Unauthorized grading",
        },
    )
    assert r.status_code == 403


def test_observer_read_only_and_data_isolation(stub_iam, test_setup):
    c = _auth_client(stub_iam, uid=8001, perms=_OBSERVER, kind="faculty", role="course_observer")
    ass_a = test_setup["ass_a"]
    sub1 = test_setup["sub1"]

    # Observer can view course workspace
    r = c.get("/api/v1/lms/courses/501/")
    assert r.status_code == 200

    # Observer CANNOT post announcements
    r = c.post(
        "/api/v1/lms/announcements/",
        {
            "course_id": 501,
            "title": "Observer Post",
            "content": "Observer test",
        },
    )
    assert r.status_code == 403

    # Observer CANNOT submit assignments
    r = c.post(
        f"/api/v1/lms/assignments/{ass_a.id}/submissions/",
        {
            "submission_type": "TEXT",
            "content_text": "Observer submission",
        },
    )
    assert r.status_code == 403

    # Observer querying submissions gets 403 Forbidden (no permission to view student submissions)
    r = c.get(f"/api/v1/lms/assignments/{ass_a.id}/submissions/")
    assert r.status_code == 403

    # Observer requesting individual submission detail gets 403 Forbidden
    r = c.get(f"/api/v1/lms/submissions/{sub1.id}/")
    assert r.status_code == 403


def test_cross_course_isolation(stub_iam, test_setup):
    # Instructor of Course A (user 6001) attempting to modify Course B
    c = _auth_client(stub_iam, uid=6001, perms=_FACULTY, kind="faculty", role="faculty")
    sub_b = test_setup["sub_b"]

    # Modify Course B workspace
    r = c.patch(
        "/api/v1/lms/courses/502/",
        {
            "syllabus": "Hacked Syllabus B",
        },
    )
    assert r.status_code == 403

    # Post announcement in Course B
    r = c.post(
        "/api/v1/lms/announcements/",
        {
            "course_id": 502,
            "title": "Cross Course Announcement",
            "content": "Intrusion",
        },
    )
    assert r.status_code == 403

    # Grade submission in Course B
    r = c.post(
        f"/api/v1/lms/submissions/{sub_b.id}/grade/",
        {
            "points_awarded": 50,
            "feedback_text": "Cross course grading",
        },
    )
    assert r.status_code == 403
