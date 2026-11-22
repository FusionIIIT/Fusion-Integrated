"""CSRF protection tests for cookie-authenticated write requests (R1-17)."""

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from conftest import make_session
from core.api import csrf
from modules.lms.domain.constants import CourseRole, MembershipStatus
from modules.lms.models import CourseMembership, CourseWorkspace

pytestmark = pytest.mark.django_db


def test_cookie_write_without_csrf_token_returns_403(stub_iam):
    cookie_token = "synthetic-session-token-42"
    stub_iam(
        make_session(
            user_id=4001,
            kind="faculty",
            permissions=("lms.announcement.create", "lms.announcement.view"),
            modules=("lms",),
        )
    )

    course_id = 801
    CourseWorkspace.objects.create(
        course_id=course_id,
        course_code="CS801",
        title="Security & Cryptography",
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=4001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )

    client = APIClient()
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = cookie_token

    # 1. Unsafe write WITHOUT X-CSRF-Token -> 403 Forbidden
    response_no_csrf = client.post(
        "/api/v1/lms/announcements/",
        data={"course_id": course_id, "title": "Test", "content": "Body"},
        format="json",
    )
    assert response_no_csrf.status_code == 403
    assert "csrf" in str(response_no_csrf.data).lower()

    # 2. Unsafe write WITH valid X-CSRF-Token -> succeeds (201 Created)
    response_with_csrf = client.post(
        "/api/v1/lms/announcements/",
        data={"course_id": course_id, "title": "Test", "content": "Body"},
        format="json",
        HTTP_X_CSRF_TOKEN=csrf.token_for(cookie_token),
    )
    assert response_with_csrf.status_code == 201
