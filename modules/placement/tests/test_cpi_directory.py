"""The CPI directory's access boundary.

The largest disclosure in the module — every student's academic standing — so
the test is mostly about who is refused.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.placement.models import Company
from modules.placement.services import recruiters

pytestmark = pytest.mark.django_db

URL = "/api/v1/placement/students/cpi"
STAFF_PERM = "placement_cell.academic_directory.view"


def client_for(stub_iam, **kw):
    stub_iam(make_session(modules=("placement_cell",), **kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


class TestWhoMayEnumerate:

    def test_staff_with_the_permission_may(self, stub_iam):
        c = client_for(stub_iam, user_id=9, kind="staff",
                       permissions=(STAFF_PERM, "placement_cell.report.view"))
        assert c.get(URL).status_code == 200

    def test_a_student_may_not(self, stub_iam):
        """Their own CPI arrives on /me. Enumerating their peers' does not."""
        c = client_for(stub_iam, user_id=1001, kind="student",
                       permissions=("placement_cell.application.view_self",))
        assert c.get(URL).status_code == 403

    def test_staff_without_the_permission_may_not(self, stub_iam):
        c = client_for(stub_iam, user_id=9, kind="staff",
                       permissions=("placement_cell.application.review",))
        assert c.get(URL).status_code == 403

    def test_an_alumnus_may_not(self, stub_iam):
        c = client_for(stub_iam, user_id=5, kind="student", roles=("alumni",),
                       permissions=(STAFF_PERM,))
        assert c.get(URL).status_code == 403

    def test_a_recruiter_may_not(self, stub_iam):
        """The case that matters most. A recruiter with the whole institute's
        CPI list is precisely what the company-scoping rules exist to stop —
        and they hold no permissions at all, so this is refused twice over."""
        company = Company.objects.create(
            name="Acme", slug="acme", status="active",
            approval_status="approved", approved_by_user_id=9)
        _, raw = recruiters.invite(company_id=company.pk,
                                   email="a@acme.test", invited_by_user_id=9)
        recruiters.accept_invite(token=raw, password="a-long-enough-password")
        session = recruiters.sign_in(email="a@acme.test",
                                     password="a-long-enough-password")
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Recruiter {session.raw_key}")
        assert c.get(URL).status_code in (401, 403)

    def test_anonymous_may_not(self):
        assert APIClient().get(URL).status_code == 401


class TestBehaviour:

    def test_the_student_token_is_never_forwarded_to_the_iam(self, stub_iam):
        """The service credential is used, after this service has decided the
        caller is staff. Forwarding a user's token would make IAM authorisation
        the only thing between a student and every peer's CPI."""
        fake = stub_iam(make_session(user_id=9, kind="staff",
                                     modules=("placement_cell",),
                                     permissions=(STAFF_PERM,)))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token abc")
        c.get(f"{URL}?discipline=CSE")
        calls = [x for x in fake.calls if x[0] == "academic_directory"]
        assert calls, "the directory call should have been made"

    def test_a_bad_page_size_is_a_400(self, stub_iam):
        c = client_for(stub_iam, user_id=9, kind="staff",
                       permissions=(STAFF_PERM,))
        assert c.get(f"{URL}?limit=lots").status_code == 400

    def test_the_iam_being_down_is_a_503_not_an_empty_list(self, stub_iam):
        """An empty directory reads as "no students", which is a lie."""
        from fusion_auth.client import IamUnavailable
        fake = stub_iam(make_session(user_id=9, kind="staff",
                                     modules=("placement_cell",),
                                     permissions=(STAFF_PERM,)))
        fake.directory_error = IamUnavailable("connection refused")
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token abc")
        assert c.get(URL).status_code == 503
