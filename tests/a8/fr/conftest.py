"""Local conftest for FR strategy — mirrors root conftest helpers."""
from datetime import timedelta

import pytest
from django.utils import timezone

from conftest import make_session
from modules.lms.models import Course, CourseMembership


def _login(stub_iam, user_id, kind="student", roles=("student",), permissions=()):
    session = make_session(
        user_id=user_id,
        kind=kind,
        roles=roles,
        permissions=permissions,
        modules=("lms",),
    )
    stub_iam(session)
    from rest_framework.test import APIClient

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token tok-{user_id}")
    return c


@pytest.fixture
def course_factory():
    def _make(code="CS101", name="Test Course", **kw):
        return Course.objects.create(code=code, name=name, **kw)

    return _make


@pytest.fixture
def membership_factory():
    def _make(course, user_id, role="student", **kw):
        return CourseMembership.objects.create(
            course=course, user_id=user_id, role=role, **kw
        )

    return _make


def make_future(days=5):
    return timezone.now() + timedelta(days=days)


def make_past(days=1):
    return timezone.now() - timedelta(days=days)
