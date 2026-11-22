"""HTTP surface: authentication, status codes, and — above all — scope.

A foreign row is *absent*, not forbidden (BR-042), so the assertion everywhere is on the
rows that come back."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.mms.tests import factories as f
from modules.mms.tests.helpers import (
    ADMIN,
    CARETAKER,
    OTHER_STUDENT_ID,
    ROLES,
    STUDENT,
    STUDENT_ID,
    WARDEN,
    grants,
)

pytestmark = pytest.mark.django_db

ENDPOINTS = {
    "menu": "/api/v1/mms/menu/",
    "announcements": "/api/v1/mms/announcements/",
    "registrations": "/api/v1/mms/registrations/",
    "deregistrations": "/api/v1/mms/deregistrations/",
    "rebates": "/api/v1/mms/rebates/",
    "special-food": "/api/v1/mms/special-food/",
    "bills": "/api/v1/mms/bills/",
    "feedback": "/api/v1/mms/feedback/",
}
_USER = {ADMIN: 9001, CARETAKER: 9002, WARDEN: 9003, STUDENT: STUDENT_ID}


@pytest.fixture
def client_as(stub_iam):
    def _as(role):
        stub_iam(make_session(user_id=_USER[role], permissions=grants(role), modules=("mms",),
                              kind="student" if role == STUDENT else "staff",
                              roles=(role,), active_role=role))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token abc")
        return c
    return _as


@pytest.fixture
def world():
    """Two students' worth of every kind of row, so scope has something to leak."""
    for uid in (STUDENT_ID, OTHER_STUDENT_ID):
        reg = f.RegistrationFactory(user_id=uid, approved=True)
        f.DeregistrationFactory(user_id=uid, registration=reg)
        f.RebateFactory(user_id=uid)
        f.SpecialFoodFactory(user_id=uid)
        f.BillFactory(user_id=uid)
        f.FeedbackFactory(user_id=uid)
    f.MenuFactory()
    f.AnnouncementFactory()


def _rows(resp):
    body = resp.json()
    return body["results"] if isinstance(body, dict) and "results" in body else body


@pytest.mark.parametrize("path", ENDPOINTS.values(), ids=ENDPOINTS.keys())
def test_every_endpoint_requires_authentication(stub_iam, path):
    stub_iam(None)
    assert APIClient().get(path).status_code in (401, 403)


@pytest.mark.parametrize("path", ENDPOINTS.values(), ids=ENDPOINTS.keys())
def test_every_endpoint_rejects_writes_for_now(client_as, path):
    """The list views are read-only; a POST must be 405, never a 500 or a silent create."""
    assert client_as(CARETAKER).post(path, {}).status_code == 405


@pytest.mark.parametrize("path", ENDPOINTS.values(), ids=ENDPOINTS.keys())
@pytest.mark.parametrize("role", ROLES)
def test_no_endpoint_ever_500s_for_any_role(client_as, world, role, path):
    assert client_as(role).get(path).status_code == 200


@pytest.mark.parametrize("name", ["registrations", "deregistrations", "rebates",
                                  "special-food", "bills", "feedback"])
def test_br042_a_student_only_ever_receives_their_own_rows(client_as, world, name):
    rows = _rows(client_as(STUDENT).get(ENDPOINTS[name]))
    assert rows and {r["user_id"] for r in rows} == {STUDENT_ID}


@pytest.mark.parametrize("name", ["registrations", "deregistrations", "rebates",
                                  "special-food", "bills", "feedback"])
def test_br005_the_mess_admin_gets_an_empty_list_for_operational_data(client_as, world, name):
    assert _rows(client_as(ADMIN).get(ENDPOINTS[name])) == []


@pytest.mark.parametrize("name", ["registrations", "rebates", "special-food", "bills", "feedback"])
def test_the_caretaker_sees_both_students(client_as, world, name):
    rows = _rows(client_as(CARETAKER).get(ENDPOINTS[name]))
    assert {r["user_id"] for r in rows} == {STUDENT_ID, OTHER_STUDENT_ID}


def test_the_warden_oversees_registrations_but_not_bills(client_as, world):
    assert len(_rows(client_as(WARDEN).get(ENDPOINTS["registrations"]))) == 2
    assert _rows(client_as(WARDEN).get(ENDPOINTS["bills"])) == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("name", ["menu", "announcements"])
def test_br033_br038_menu_and_announcements_are_readable_by_every_mms_role(
        client_as, world, role, name):
    assert len(_rows(client_as(role).get(ENDPOINTS[name]))) == 1


def test_the_payload_exposes_the_documented_bill_fields(client_as, world):
    row = _rows(client_as(STUDENT).get(ENDPOINTS["bills"]))[0]
    assert {"billing_month", "base_amount", "rebate_discount", "special_food_amount",
            "total_amount", "status"} <= set(row)


def test_money_is_serialised_as_a_string_not_a_float(client_as, world):
    """Binary floats cannot hold 0.10; a bill that renders 2849.9999999 is a support ticket."""
    row = _rows(client_as(STUDENT).get(ENDPOINTS["bills"]))[0]
    assert isinstance(row["total_amount"], str)
