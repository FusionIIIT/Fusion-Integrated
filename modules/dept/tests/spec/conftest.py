"""Shared fixtures and test helpers for specification-based test suites."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.dept.models import Department

pytestmark = pytest.mark.django_db


@pytest.fixture
def cse_dept(db):
    dept, _ = Department.objects.get_or_create(
        code="CSE",
        defaults={
            "name": "Computer Science and Engineering",
            "description": "Department of Computer Science and Engineering",
        },
    )
    return dept


@pytest.fixture
def auth_client(stub_iam):
    def _make(
        role="student",
        user_id=101,
        username="user101",
        permissions=None,
        department="CSE",
    ):
        if permissions is None:
            r = role.lower()
            if r in ("student",):
                permissions = (
                    "dept.announcement.view",
                    "dept.feedback.create",
                    "dept.feedback.view",
                    "dept.profile.view",
                    "dept.timetable.view",
                    "dept.academic_program.view",
                )
            elif r in ("faculty",):
                permissions = (
                    "dept.announcement.view",
                    "dept.announcement.create",
                    "dept.stock_request.view",
                    "dept.stock_request.create",
                    "dept.feedback.create",
                    "dept.feedback.view",
                    "dept.profile.view",
                    "dept.lab_resource.view",
                    "dept.timetable.view",
                )
            elif r in ("dept_admin", "admin"):
                permissions = (
                    "dept.announcement.view",
                    "dept.announcement.create",
                    "dept.inventory.view",
                    "dept.inventory.create",
                    "dept.stock_request.view",
                    "dept.stock_request.issue",
                    "dept.feedback.review",
                    "dept.feedback.resolve",
                    "dept.feedback.view",
                    "dept.profile.view",
                    "dept.profile.manage",
                    "dept.timetable.view",
                    "dept.timetable.manage",
                    "dept.lab_resource.view",
                    "dept.lab_resource.manage",
                    "dept.detail.view",
                    "dept.detail.update",
                )
            elif r in ("hod",):
                permissions = (
                    "dept.announcement.view",
                    "dept.announcement.create",
                    "dept.announcement.manage",
                    "dept.stock_request.view",
                    "dept.stock_request.approve",
                    "dept.feedback.resolve",
                    "dept.feedback.view",
                    "dept.profile.view",
                    "dept.detail.view",
                    "dept.detail.approve",
                )
            elif r in ("institute admin", "institute_admin"):
                permissions = (
                    "dept.role_assignment.view",
                    "dept.role_assignment.manage",
                )
            else:
                permissions = ()

        session = make_session(
            user_id=user_id,
            modules=("dept",),
            permissions=permissions,
            roles=(role,),
            active_role=role,
        )
        stub_iam(session)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {username}_token")
        client.activate = lambda: stub_iam(session)
        return client

    return _make
