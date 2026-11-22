"""Query budgets for LMS endpoints to ensure zero N+1 queries (R1-16)."""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.domain.constants import (
    CourseRole,
    MaterialStatus,
    MaterialType,
    MembershipStatus,
)
from modules.lms.models import (
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, uid=4001):
    stub_iam(
        make_session(
            user_id=uid,
            kind="faculty",
            permissions=(
                "lms.workspace.view",
                "lms.material.view",
                "lms.announcement.view",
                "lms.assignment.view",
            ),
            modules=("lms",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_courses_list_query_count_does_not_scale_with_rows(stub_iam):
    client = _client(stub_iam, uid=4001)

    # 1. Setup 2 courses
    for i in range(1, 3):
        CourseWorkspace.objects.create(
            course_id=100 + i,
            course_code=f"CS{100 + i}",
            title=f"Course {i}",
        )
        CourseMembership.objects.create(
            course_id=100 + i,
            user_id=4001,
            role=CourseRole.INSTRUCTOR,
            status=MembershipStatus.ACTIVE,
        )

    with CaptureQueriesContext(connection) as first:
        res = client.get("/api/v1/lms/courses/")
        assert res.status_code == 200

    q_count_first = len(first.captured_queries)

    # 2. Add 5 more courses
    for i in range(3, 8):
        CourseWorkspace.objects.create(
            course_id=100 + i,
            course_code=f"CS{100 + i}",
            title=f"Course {i}",
        )
        CourseMembership.objects.create(
            course_id=100 + i,
            user_id=4001,
            role=CourseRole.INSTRUCTOR,
            status=MembershipStatus.ACTIVE,
        )

    with CaptureQueriesContext(connection) as second:
        res = client.get("/api/v1/lms/courses/")
        assert res.status_code == 200

    q_count_second = len(second.captured_queries)
    assert q_count_first == q_count_second, (
        f"Query count scaled with course rows: {q_count_first} vs {q_count_second}"
    )


def test_materials_list_query_count_does_not_scale_with_rows(stub_iam):
    client = _client(stub_iam, uid=4001)
    course_id = 201
    CourseWorkspace.objects.create(
        course_id=course_id,
        course_code="CS201",
        title="Data Structures",
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=4001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )

    now = timezone.now()
    for i in range(1, 3):
        CourseMaterial.objects.create(
            course_id=course_id,
            title=f"Mat {i}",
            material_type=MaterialType.NOTE,
            content_text="Notes",
            status=MaterialStatus.PUBLISHED,
            release_date=now - timedelta(days=1),
            uploaded_by=4001,
        )

    with CaptureQueriesContext(connection) as first:
        res = client.get(f"/api/v1/lms/materials/?course_id={course_id}")
        assert res.status_code == 200

    q_count_first = len(first.captured_queries)

    for i in range(3, 8):
        CourseMaterial.objects.create(
            course_id=course_id,
            title=f"Mat {i}",
            material_type=MaterialType.NOTE,
            content_text="Notes",
            status=MaterialStatus.PUBLISHED,
            release_date=now - timedelta(days=1),
            uploaded_by=4001,
        )

    with CaptureQueriesContext(connection) as second:
        res = client.get(f"/api/v1/lms/materials/?course_id={course_id}")
        assert res.status_code == 200

    q_count_second = len(second.captured_queries)
    assert q_count_first == q_count_second, (
        f"Query count scaled with material rows: {q_count_first} vs {q_count_second}"
    )
