"""Ways out of the states a request can get stuck in.

Every one of these has a service and a serializer; some had no route, so the
only exit from a declined nomination was to abandon the request. For an
extension there was no exit at all -- withdrawing an extension is not the same
as abandoning leave that is already running.
"""
from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import State
from modules.leave.services import decisions
from modules.leave.services import requests as service
from modules.leave.tests import factories
from modules.leave.tests.factories import YEAR

pytestmark = pytest.mark.django_db

APPLICANT, FIRST, SECOND = 701, 702, 703
EMPLOYEE_PERMS = ("leave.request.create", "leave.request.view_self",
                  "leave.request.withdraw", "leave.substitute.respond")


@pytest.fixture
def people():
    for uid in (APPLICANT, FIRST, SECOND):
        UserRef.objects.create(user_id=uid, username=f"u{uid}",
                               display_name=f"U{uid}", kind="faculty", department="CSE")
    factories.setup_all(999)
    factories.credit(APPLICANT, Category.CL, 8)


def client(stub_iam, user_id=APPLICANT, permissions=EMPLOYEE_PERMS):
    stub_iam(make_session(user_id=user_id, kind="faculty", modules=("leave",),
                          permissions=permissions))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def declined():
    r = service.submit(user_id=APPLICANT, category=Category.CL,
                       starts_on=date(YEAR, 3, 2), ends_on=date(YEAR, 3, 3),
                       reason="x", unit="CSE", faculty=False,
                       designations=frozenset({"Assistant Professor"}),
                       substitute_user_id=FIRST)
    return decisions.substitute_responds(request=r, substitute_user_id=FIRST,
                                         accepted=False)


class TestRenominatingThroughTheApi:
    def test_the_route_exists(self, stub_iam, people):
        r = declined()
        assert r.state == State.APPLICANT_ACTION_REQUIRED.value
        c = client(stub_iam)

        response = c.post(f"/api/v1/leave/requests/{r.pk}/renominate",
                          {"substitute_user_id": SECOND}, format="json")

        assert response.status_code == 200
        assert response.json()["state"] == State.AWAITING_SUBSTITUTE.value

    def test_the_new_nomination_supersedes_the_old_one(self, stub_iam, people):
        r = declined()
        c = client(stub_iam)

        c.post(f"/api/v1/leave/requests/{r.pk}/renominate",
               {"substitute_user_id": SECOND}, format="json")

        latest = r.nominations.order_by("-id").first()
        assert latest.substitute_user_id == SECOND
        assert latest.supersedes_id is not None

    def test_the_second_substitute_can_accept_and_the_request_moves_on(
        self, stub_iam, people
    ):
        r = declined()
        c = client(stub_iam)
        c.post(f"/api/v1/leave/requests/{r.pk}/renominate",
               {"substitute_user_id": SECOND}, format="json")

        second = client(stub_iam, user_id=SECOND)
        response = second.post(f"/api/v1/leave/nominations/{r.pk}/respond",
                               {"accepted": True}, format="json")

        assert response.status_code == 200
        assert response.json()["state"] == State.AWAITING_UNIT_HEAD.value

    def test_you_cannot_renominate_somebody_elses_request(self, stub_iam, people):
        r = declined()
        c = client(stub_iam, user_id=SECOND)

        response = c.post(f"/api/v1/leave/requests/{r.pk}/renominate",
                          {"substitute_user_id": FIRST}, format="json")

        assert response.status_code == 404

    def test_you_cannot_nominate_yourself(self, stub_iam, people):
        r = declined()
        c = client(stub_iam)

        response = c.post(f"/api/v1/leave/requests/{r.pk}/renominate",
                          {"substitute_user_id": APPLICANT}, format="json")

        assert response.status_code == 409

    def test_withdrawing_is_still_available_as_the_other_way_out(
        self, stub_iam, people
    ):
        r = declined()
        c = client(stub_iam)

        response = c.post(f"/api/v1/leave/requests/{r.pk}/withdraw")

        assert response.status_code == 200
        assert response.json()["state"] == State.WITHDRAWN.value
