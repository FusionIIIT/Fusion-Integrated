"""A balance is scoped like a request list, not like a public figure."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.leave.domain.categories import Category
from modules.leave.tests import factories

pytestmark = pytest.mark.django_db

CSE_STAFF, ECE_STAFF = 501, 502
CSE_HEAD, REGISTRAR = 601, 701


@pytest.fixture
def people():
    for uid, dept in ((CSE_STAFF, "CSE"), (ECE_STAFF, "ECE"),
                      (CSE_HEAD, "CSE"), (REGISTRAR, "Registrar Office")):
        UserRef.objects.create(user_id=uid, username=f"u{uid}",
                               display_name=f"U{uid}", kind="faculty", department=dept)
    factories.make_policy()
    for uid in (CSE_STAFF, ECE_STAFF):
        factories.credit(uid, Category.CL, 8)


def client(stub_iam, user_id, permissions):
    stub_iam(make_session(user_id=user_id, kind="faculty", modules=("leave",),
                          permissions=permissions))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


HEAD = ("leave.request.review", "leave.balance.view")
ESTABLISHMENT = ("leave.request.route", "leave.balance.view")


class TestAUnitHeadIsScopedToTheirUnit:
    def test_they_can_read_their_own_units_balances(self, stub_iam, people):
        c = client(stub_iam, CSE_HEAD, HEAD)

        r = c.get("/api/v1/leave/balances", {"user_id": CSE_STAFF})

        assert r.status_code == 200
        assert [b["category"] for b in r.json()] == ["CL"]

    def test_they_cannot_read_another_units(self, stub_iam, people):
        c = client(stub_iam, CSE_HEAD, HEAD)

        r = c.get("/api/v1/leave/balances", {"user_id": ECE_STAFF})

        # 404, not 403: a refusal confirms the person has an account here.
        assert r.status_code == 404

    def test_a_head_with_no_department_reads_nobody(self, stub_iam, people):
        UserRef.objects.filter(user_id=CSE_HEAD).update(department="")
        c = client(stub_iam, CSE_HEAD, HEAD)

        assert c.get("/api/v1/leave/balances",
                     {"user_id": CSE_STAFF}).status_code == 404


class TestTheEstablishmentSeesTheInstitute:
    def test_it_reads_any_unit(self, stub_iam, people):
        c = client(stub_iam, REGISTRAR, ESTABLISHMENT)

        for uid in (CSE_STAFF, ECE_STAFF):
            assert c.get("/api/v1/leave/balances",
                         {"user_id": uid}).status_code == 200


class TestQueryParametersAreValidated:
    def test_a_missing_user_id_is_a_400(self, stub_iam, people):
        c = client(stub_iam, REGISTRAR, ESTABLISHMENT)

        r = c.get("/api/v1/leave/balances")

        assert r.status_code == 400
        assert r.json()["error"]["code"] == "missing_parameter"

    def test_a_non_numeric_user_id_is_a_400_not_a_500(self, stub_iam, people):
        c = client(stub_iam, REGISTRAR, ESTABLISHMENT)

        r = c.get("/api/v1/leave/balances", {"user_id": "../etc"})

        assert r.status_code == 400
        assert "whole number" in r.json()["error"]["message"]

    def test_a_bad_year_is_a_400_not_a_500(self, stub_iam, people):
        c = client(stub_iam, CSE_STAFF, ("leave.request.view_self",))

        r = c.get("/api/v1/leave/me/balances", {"year": "last"})

        assert r.status_code == 400

    def test_an_unknown_category_is_a_400_not_a_500(self, stub_iam, people):
        c = client(stub_iam, CSE_STAFF, ("leave.request.view_self",))

        r = c.get("/api/v1/leave/me/statement/NOPE")

        assert r.status_code == 400
        assert r.json()["error"]["code"] == "unknown_category"
