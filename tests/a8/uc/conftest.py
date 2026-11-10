"""Local conftest for UC strategy."""

import pytest

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
    def _make(code="UC101", name="UC Course", **kw):
        return Course.objects.create(code=code, name=name, **kw)

    return _make


def _mk_course(code="UC101", name="UC Course", **kw):
    return Course.objects.create(code=code, name=name, **kw)


def _mem(course, user_id, role):
    return CourseMembership.objects.create(course=course, user_id=user_id, role=role)
