"""Specification use case tests for LMS Assignment Authoring and Publishing.

Covers:
- TC-UC-018 / UC-LMS-007 Main Flow: Faculty creates new assignment in Draft state
- TC-UC-019 / UC-LMS-007 Alternative A1: Faculty edits existing Draft assignment
- TC-UC-020 / UC-LMS-007 Exception E1: Non-Faculty assignment authoring/editing rejected
- TC-UC-021 / UC-LMS-008 Main Flow: Faculty publishes Draft assignment immediately
- TC-UC-022 / UC-LMS-008 Alternative A1: Publishing Draft with future release sets Scheduled
- TC-UC-023 / UC-LMS-008 Exception E1: Invalid Draft assignment cannot be published
- TC-UC-024 / UC-LMS-009 Main Flow: Student views assignment details
- TC-UC-025 / UC-LMS-009 Alternative A1: Future-dated unreleased assignments omitted from students
- TC-UC-026 / UC-LMS-009 Exception E1: Unauthorized user denied access to assignments
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db.utils import IntegrityError
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
from modules.lms.registry import _FACULTY, _OBSERVER, _STUDENT, _TA
from modules.lms.services.assignments import publish_assignment

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
        title="Computer Architecture",
        syllabus="Pipelining, Cache Hierarchies",
        schedule_info="MWF 14:00",
    )
    # Faculty F1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=101,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA T1
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=201,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
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
    return ws


def test_tc_uc_018_faculty_creates_draft_assignment(stub_iam):
    """Test ID: TC-UC-018.

    Source ID: UC-LMS-007 Main Flow
    Purpose: Verify that assigned Faculty can create a new assignment with
    required configuration and save it in Draft state.
    """
    _setup_assignments_world(101)
    client = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    due_dt = timezone.now() + timedelta(days=10)
    resp = client.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Homework 1",
            "instructions": "Complete homework 1",
            "points_possible": "100.00",
            "submission_type": SubmissionType.FILE,
            "due_date": due_dt.isoformat(),
        },
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["title"] == "Homework 1"
    assert data["instructions"] == "Complete homework 1"
    assert Decimal(str(data["points_possible"])) == Decimal("100.00")
    assert data["submission_type"] == SubmissionType.FILE
    assert data["status"] == AssignmentStatus.DRAFT

    asg = Assignment.objects.get(id=data["id"])
    assert asg.status == AssignmentStatus.DRAFT
    assert asg.created_by == 101


def test_tc_uc_019_faculty_edits_draft_assignment(stub_iam):
    """Test ID: TC-UC-019.

    Source ID: UC-LMS-007 Alternative A1
    Purpose: Verify that assigned Faculty can edit an existing Draft assignment.
    """
    _setup_assignments_world(101)
    client = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Draft Lab 1",
        instructions="Initial instructions",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    resp = client.patch(
        f"/api/v1/lms/assignments/{asg.id}/",
        data={
            "instructions": "Updated instructions with rubric",
            "points_possible": "50.00",
        },
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["instructions"] == "Updated instructions with rubric"
    assert Decimal(str(data["points_possible"])) == Decimal("50.00")
    assert data["status"] == AssignmentStatus.DRAFT

    asg.refresh_from_db()
    assert asg.instructions == "Updated instructions with rubric"
    assert asg.points_possible == Decimal("50.00")
    assert asg.status == AssignmentStatus.DRAFT


def test_tc_uc_020_non_faculty_assignment_authoring_rejected(stub_iam):
    """Test ID: TC-UC-020.

    Source ID: UC-LMS-007 Exception E1
    Purpose: Verify that assignment authoring or editing attempts by non-Faculty
    users (TA, Student, or Observer) are rejected.
    """
    _setup_assignments_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Faculty Assignment",
        instructions="Complete tasks",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    non_faculty_roles = [
        (201, _TA, "student", "teaching_assistant"),
        (301, _STUDENT, "student", "student"),
        (401, _OBSERVER, "student", "course_observer"),
    ]

    for uid, perms, kind, role in non_faculty_roles:
        client = _make_client(stub_iam, user_id=uid, perms=perms, kind=kind, role=role)

        # Attempt create
        resp_create = client.post(
            "/api/v1/lms/assignments/",
            data={
                "course_id": 101,
                "title": f"Created by {role}",
                "instructions": "Attempted instructions",
                "points_possible": "100.00",
                "submission_type": SubmissionType.TEXT,
                "due_date": (now + timedelta(days=3)).isoformat(),
            },
            format="json",
        )
        assert resp_create.status_code == 403

        # Attempt edit
        resp_edit = client.patch(
            f"/api/v1/lms/assignments/{asg.id}/",
            data={"title": f"Modified by {role}"},
            format="json",
        )
        assert resp_edit.status_code == 403

    # Existing assignment unchanged
    asg.refresh_from_db()
    assert asg.title == "Faculty Assignment"
    assert Assignment.objects.filter(course_id=101).count() == 1


def test_tc_uc_021_faculty_publishes_assignment_immediately(stub_iam):
    """Test ID: TC-UC-021.

    Source ID: UC-LMS-008 Main Flow
    Purpose: Verify that assigned Faculty can publish a valid Draft assignment
    for immediate release, making it Available to Students.
    """
    _setup_assignments_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Lab 2: Caching",
        instructions="Implement direct-mapped cache",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    # Publish assignment immediately
    resp_pub = client_fac.post(f"/api/v1/lms/assignments/{asg.id}/publish/")
    assert resp_pub.status_code == 200
    assert resp_pub.json()["status"] == AssignmentStatus.PUBLISHED

    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.PUBLISHED

    # Available to students
    client_student = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = client_student.get("/api/v1/lms/assignments/?course_id=101")
    assert resp_student.status_code == 200
    ids = [a["id"] for a in resp_student.json()]
    assert asg.id in ids


def test_tc_uc_022_publish_draft_with_future_release_schedules_it(stub_iam):
    """Test ID: TC-UC-022.

    Source ID: UC-LMS-008 Alternative A1
    Purpose: Verify that publishing a Draft assignment configured with future-dated
    release marks it Scheduled for Release awaiting automated release processing.
    """
    _setup_assignments_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )

    now = timezone.now()
    future_release = now + timedelta(days=3)
    future_due = now + timedelta(days=10)

    asg = Assignment.objects.create(
        course_id=101,
        title="Lab 3: Virtual Memory",
        instructions="Implement paging table",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        release_date=future_release,
        due_date=future_due,
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    resp_pub = client_fac.post(
        f"/api/v1/lms/assignments/{asg.id}/publish/",
        data={},
        format="json",
    )
    assert resp_pub.status_code == 200
    assert resp_pub.json()["status"] == AssignmentStatus.SCHEDULED

    asg.refresh_from_db()
    assert asg.status == AssignmentStatus.SCHEDULED

    # Withheld from students until release processing
    client_student = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )
    resp_student = client_student.get("/api/v1/lms/assignments/?course_id=101")
    assert resp_student.status_code == 200
    ids = [a["id"] for a in resp_student.json()]
    assert asg.id not in ids


def test_tc_uc_023_invalid_draft_assignment_cannot_be_published(stub_iam):
    """Test ID: TC-UC-023.

    Source ID: UC-LMS-008 Exception E1
    Purpose: Verify that an invalid Draft assignment cannot be published.
    """
    _setup_assignments_world(101)
    client_fac = _make_client(
        stub_iam, user_id=101, perms=_FACULTY, kind="faculty", role="instructor"
    )
    from types import SimpleNamespace

    faculty_principal = SimpleNamespace(
        user_id=101, erp_user_id=101, roles=["instructor"], permissions=_FACULTY
    )

    now = timezone.now()
    # 1. API rejects creating assignment with invalid configuration (negative points)
    resp_inv_create = client_fac.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": 101,
            "title": "Invalid Config Asg",
            "instructions": "Invalid points",
            "points_possible": "-15.00",
            "submission_type": SubmissionType.FILE,
            "due_date": (now + timedelta(days=5)).isoformat(),
        },
        format="json",
    )
    assert resp_inv_create.status_code == 400

    # 2. Domain configuration validation check
    with pytest.raises(DomainValidationError):
        validate_assignment_config(
            title="",
            instructions="Missing title",
            points_possible=100,
            submission_type=SubmissionType.FILE,
            due_date=now + timedelta(days=5),
            release_date=None,
        )

    with pytest.raises(DomainValidationError):
        validate_assignment_config(
            title="Invalid Points",
            instructions="Points cannot be negative",
            points_possible=-10,
            submission_type=SubmissionType.FILE,
            due_date=now + timedelta(days=5),
            release_date=None,
        )

    # 3. Assignment with release date violating deadline constraint cannot be published
    asg_inv = Assignment.objects.create(
        course_id=101,
        title="Invalid Schedule Assignment",
        instructions="Instructions",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=2),
        status=AssignmentStatus.DRAFT,
        created_by=101,
    )

    # Attempt to publish with release_date occurring after due_date
    invalid_release = now + timedelta(days=5)
    with pytest.raises(IntegrityError):
        publish_assignment(
            assignment_id=asg_inv.id,
            release_date=invalid_release,
            principal=faculty_principal,
        )

    # Assignment remains in Draft state
    asg_inv.refresh_from_db()
    assert asg_inv.status == AssignmentStatus.DRAFT


def test_tc_uc_024_student_views_assignment_details(stub_iam):
    """Test ID: TC-UC-024.

    Source ID: UC-LMS-009 Main Flow
    Purpose: Verify that an enrolled Student can view assignment details and
    download content for a published and released assignment.
    """
    _setup_assignments_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Project 1: Shell Implementation",
        instructions="Implement a POSIX compliant shell with pipes",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=14),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    client_student = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # Student views assignment list
    resp_list = client_student.get("/api/v1/lms/assignments/?course_id=101")
    assert resp_list.status_code == 200
    assert any(a["id"] == asg.id for a in resp_list.json())

    # Student views assignment details
    resp_detail = client_student.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp_detail.status_code == 200
    data = resp_detail.json()
    assert data["id"] == asg.id
    assert data["title"] == "Project 1: Shell Implementation"
    assert data["instructions"] == "Implement a POSIX compliant shell with pipes"
    assert Decimal(str(data["points_possible"])) == Decimal("100.00")
    assert data["submission_type"] == SubmissionType.FILE


def test_tc_uc_025_future_unreleased_assignments_omitted_from_students(stub_iam):
    """Test ID: TC-UC-025.

    Source ID: UC-LMS-009 Alternative A1
    Purpose: Verify that future-dated unreleased assignments are omitted and
    not shown to Students.
    """
    _setup_assignments_world(101)
    now = timezone.now()

    # Published and available
    asg_available = Assignment.objects.create(
        course_id=101,
        title="Available Assignment",
        instructions="Start working",
        points_possible=Decimal("50.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    # Scheduled with future release date
    asg_future = Assignment.objects.create(
        course_id=101,
        title="Future Unreleased Assignment",
        instructions="Confidential until release",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=20),
        release_date=now + timedelta(days=7),
        status=AssignmentStatus.SCHEDULED,
        created_by=101,
    )

    client_student = _make_client(
        stub_iam, user_id=301, perms=_STUDENT, kind="student", role="student"
    )

    # List assignments for course
    resp_list = client_student.get("/api/v1/lms/assignments/?course_id=101")
    assert resp_list.status_code == 200
    returned_ids = [a["id"] for a in resp_list.json()]
    assert asg_available.id in returned_ids
    assert asg_future.id not in returned_ids

    # Detail access directly to unreleased assignment returns 404
    resp_detail = client_student.get(f"/api/v1/lms/assignments/{asg_future.id}/")
    assert resp_detail.status_code == 404


def test_tc_uc_026_unauthorized_user_denied_assignments(stub_iam):
    """Test ID: TC-UC-026.

    Source ID: UC-LMS-009 Exception E1
    Purpose: Verify that an unauthorized user not enrolled in the course is denied
    access to view or download course assignments.
    """
    _setup_assignments_world(101)
    now = timezone.now()
    asg = Assignment.objects.create(
        course_id=101,
        title="Restricted Architecture Assignment",
        instructions="Confidential instructions",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=101,
    )

    # User U_unauth (user_id 777) is not enrolled in Course 101
    client_unauth = _make_client(
        stub_iam, user_id=777, perms=_STUDENT, kind="student", role="student"
    )

    # List assignments
    resp_list = client_unauth.get("/api/v1/lms/assignments/?course_id=101")
    assert resp_list.status_code == 200
    assert resp_list.json() == []

    # Detail access
    resp_detail = client_unauth.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert resp_detail.status_code == 404
