"""Specification business rule tests for LMS Assignment Configuration and Visibility.

Covers:
- TC-BR-019 / BR-LMS-009 permitted: Mandatory assignment configuration accepted and published
- TC-BR-020 / BR-LMS-009 prohibited: Incomplete assignment configuration rejected
- TC-BR-021 / BR-LMS-010 permitted: Created assignment remains in Draft until explicit publish
- TC-BR-022 / BR-LMS-010 prohibited: Draft assignment concealed from students
- TC-BR-023 / BR-LMS-011 permitted: Released assignment visible to students
- TC-BR-024 / BR-LMS-011 prohibited: Future-dated assignment withheld prior to release
"""

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
from modules.lms.domain.validators import DomainValidationError, validate_assignment_config
from modules.lms.models import Assignment, CourseMembership, CourseWorkspace
from modules.lms.registry import _FACULTY, _STUDENT

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


def _setup_assignments_world(course_id: int = 101):
    ws = CourseWorkspace.objects.create(
        course_id=course_id,
        course_code=f"CS{course_id}",
        title="Database Systems",
        syllabus="Query Optimization and Storage",
        schedule_info="MWF 13:00",
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=101,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=301,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    return ws


def test_tc_br_019_mandatory_assignment_configuration_published(stub_iam):
    """Test ID: TC-BR-019.

    Source ID: BR-LMS-009 permitted
    Purpose: Verify that an assignment defining due date, instructions,
    submission type, and points possible is accepted and published.
    """
    _setup_assignments_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    now = timezone.now()
    due_dt = now + timedelta(days=14)

    # 1. Create with all four mandatory fields
    resp_create = client_fac.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "B+ Tree Project",
            "instructions": "Implement buffer pool and B+ tree index",
            "points_possible": "100.00",
            "submission_type": SubmissionType.FILE,
            "due_date": due_dt.isoformat(),
        },
        format="json",
    )
    assert resp_create.status_code == 201
    asg_id = resp_create.json()["id"]

    # 2. Publish
    resp_pub = client_fac.post(f"/api/v1/lms/assignments/{asg_id}/publish/")
    assert resp_pub.status_code == 200
    assert resp_pub.json()["status"] == AssignmentStatus.PUBLISHED

    asg = Assignment.objects.get(id=asg_id)
    assert asg.status == AssignmentStatus.PUBLISHED


def test_tc_br_020_incomplete_assignment_configuration_rejected(stub_iam):
    """Test ID: TC-BR-020.

    Source ID: BR-LMS-009 prohibited
    Purpose: Verify that assignment publication is rejected when one or more
    required fields (due date, instructions, submission type, points possible)
    are missing or invalid.
    """
    _setup_assignments_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    now = timezone.now()

    # 1. API rejects non-positive points possible
    resp_bad_pts = client_fac.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Invalid Points Asg",
            "instructions": "Some instructions",
            "points_possible": "0.00",
            "submission_type": SubmissionType.FILE,
            "due_date": (now + timedelta(days=5)).isoformat(),
        },
        format="json",
    )
    assert resp_bad_pts.status_code == 400

    # 2. Domain validator rejects empty instructions
    with pytest.raises(DomainValidationError):
        validate_assignment_config(
            title="Valid Title",
            instructions="",
            points_possible=100,
            submission_type=SubmissionType.FILE,
            due_date=now + timedelta(days=5),
            release_date=None,
        )

    # 3. Domain validator rejects due date before release date
    with pytest.raises(DomainValidationError):
        validate_assignment_config(
            title="Valid Title",
            instructions="Valid instructions",
            points_possible=100,
            submission_type=SubmissionType.FILE,
            due_date=now + timedelta(days=1),
            release_date=now + timedelta(days=5),
        )


def test_tc_br_021_created_assignment_remains_in_draft_until_published(stub_iam):
    """Test ID: TC-BR-021.

    Source ID: BR-LMS-010 permitted
    Purpose: Verify that a newly created or edited assignment remains in Draft
    state until Faculty explicitly executes the publish action.
    """
    _setup_assignments_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    now = timezone.now()
    resp = client_fac.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Query Optimizer Lab",
            "instructions": "Implement dynamic programming join ordering",
            "points_possible": "80.00",
            "submission_type": SubmissionType.TEXT,
            "due_date": (now + timedelta(days=10)).isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == AssignmentStatus.DRAFT

    asg = Assignment.objects.get(id=data["id"])
    assert asg.status == AssignmentStatus.DRAFT


def test_tc_br_022_draft_assignment_concealed_from_students(stub_iam):
    """Test ID: TC-BR-022.

    Source ID: BR-LMS-010 prohibited
    Purpose: Verify that an assignment in Draft state is prohibited from being
    visible to Students.
    """
    _setup_assignments_world(101)
    now = timezone.now()
    asg_draft = Assignment.objects.create(
        course_id=101,
        title="Unpublished Draft Asg",
        instructions="Secret draft assignment instructions",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=10),
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Omitted from assignment list
    resp_list = client_s1.get("/api/v1/lms/assignments/?course_id=101")
    assert resp_list.status_code == 200
    returned_ids = [a["id"] for a in resp_list.json()]
    assert asg_draft.id not in returned_ids

    # Detail access returns 404
    resp_detail = client_s1.get(f"/api/v1/lms/assignments/{asg_draft.id}/")
    assert resp_detail.status_code == 404


def test_tc_br_023_released_assignment_visible_to_students(stub_iam):
    """Test ID: TC-BR-023.

    Source ID: BR-LMS-011 permitted
    Purpose: Verify that a published assignment becomes visible to Students
    when its release date/time condition is satisfied.
    """
    _setup_assignments_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Released Assignment 1",
        instructions="Complete database transaction assignment",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # List shows assignment
    resp_list = client_s1.get("/api/v1/lms/assignments/?course_id=101")
    assert resp_list.status_code == 200
    assert any(a["id"] == asg.id for a in resp_list.json())

    # Detail shows full content
    resp_detail = client_s1.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp_detail.status_code == 200
    assert resp_detail.json()["title"] == "Released Assignment 1"
    assert resp_detail.json()["instructions"] == "Complete database transaction assignment"


def test_tc_br_024_future_dated_assignment_withheld_from_students(stub_iam):
    """Test ID: TC-BR-024.

    Source ID: BR-LMS-011 prohibited
    Purpose: Verify that a published assignment configured with a future release
    date/time remains withheld and invisible to Students prior to that release date.
    """
    _setup_assignments_world(101)
    now = timezone.now()
    future_release = now + timedelta(days=3)

    asg_sched = Assignment.objects.create(
        course_id=101,
        title="Future Release Asg",
        instructions="Upcoming assignment content",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        release_date=future_release,
        due_date=future_release + timedelta(days=7),
        status=AssignmentStatus.SCHEDULED,
        created_by=101,
    )

    client_s1 = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Omitted from list
    resp_list = client_s1.get("/api/v1/lms/assignments/?course_id=101")
    assert resp_list.status_code == 200
    returned_ids = [a["id"] for a in resp_list.json()]
    assert asg_sched.id not in returned_ids

    # Detail access returns 404
    resp_detail = client_s1.get(f"/api/v1/lms/assignments/{asg_sched.id}/")
    assert resp_detail.status_code == 404
