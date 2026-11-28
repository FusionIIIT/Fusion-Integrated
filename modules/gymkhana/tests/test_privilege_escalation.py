"""Both gates on every endpoint, the role switch, and the refusals each endpoint can give."""
import pathlib
import re

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from conftest import make_session
from core.api import csrf
from modules.gymkhana import registry
from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.models import Club, Membership
from modules.gymkhana.tests.conftest import (
    COORD,
    FACULTY,
    PLAIN,
    STUDENT,
    STUDENT_ADMIN,
    join,
    make_club,
    session_body,
)

pytestmark = pytest.mark.django_db
API = "/api/v1/gymkhana"

# (method, path, permission it needs)
ENDPOINTS = [
    ("get", "clubs", "gymkhana.club.view"),
    ("post", "clubs/create", "gymkhana.club.create"),
    ("post", "clubs/1/approve", "gymkhana.club.approve"),
    ("get", "me/clubs", "gymkhana.club.view"),
    ("post", "clubs/1/leadership", "gymkhana.leadership.assign"),
    ("get", "memberships", "gymkhana.membership.view"),
    ("post", "memberships/apply", "gymkhana.membership.create"),
    ("post", "memberships/approve", "gymkhana.membership.approve"),
    ("get", "venues", "gymkhana.booking.create"),
    ("get", "bookings", "gymkhana.booking.view"),
    ("post", "sessions", "gymkhana.booking.create"),
    ("post", "events", "gymkhana.booking.create"),
    ("get", "polls", "gymkhana.poll.view"),
    ("get", "polls/managed", "gymkhana.poll.create"),
    ("post", "polls/create", "gymkhana.poll.create"),
    ("post", "polls/1/votes", "gymkhana.vote.create"),
    ("get", "budget-requests", "gymkhana.budget_request.view"),
    ("post", "budget-requests/create", "gymkhana.budget_request.create"),
    ("get", "event-reports", "gymkhana.event_report.view"),
    ("get", "event-reports/1", "gymkhana.event_report.view"),
    ("post", "event-reports/create", "gymkhana.event_report.create"),
    ("get", "people", "gymkhana.leadership.assign"),
]
ALL = tuple(code for code, _ in registry.PERMISSIONS)


def _client(stub_iam, permissions, modules=("gymkhana",), uid=PLAIN):
    stub_iam(make_session(user_id=uid, permissions=permissions, modules=modules))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_every_url_is_covered_here():
    from modules.gymkhana.api.urls import urlpatterns
    assert len(urlpatterns) == len(ENDPOINTS)


@pytest.mark.parametrize("method,path,code", ENDPOINTS)
def test_module_grant_without_the_permission_is_403(stub_iam, method, path, code):
    others = tuple(c for c in ALL if c != code
                   and not (path.startswith("event-reports") and c.startswith(
                       "gymkhana.event_report.review"))
                   and not (path == "people" and c in ("gymkhana.club.create",
                                                       "gymkhana.event_report.create")))
    r = getattr(_client(stub_iam, others), method)(f"{API}/{path}", {}, format="json")
    assert r.status_code == 403


@pytest.mark.parametrize("method,path,code", ENDPOINTS)
def test_permission_without_the_module_grant_is_403(stub_iam, method, path, code):
    r = getattr(_client(stub_iam, ALL, modules=("placement_cell",)), method)(
        f"{API}/{path}", {}, format="json")
    assert r.status_code == 403
    assert r.json()["error"]["message"] == "This module is not available to your role."


@pytest.mark.parametrize("method,path,code", ENDPOINTS)
def test_no_session_is_401(stub_iam, method, path, code):
    stub_iam(None)
    r = getattr(APIClient(), method)(f"{API}/{path}", {}, format="json")
    assert r.status_code in (401, 403)
    assert r.status_code == 401 or r.json()["error"]["code"] == "not_authenticated"


def test_every_permission_used_in_these_tests_is_declared():
    declared = set(ALL)
    used = set()
    for path in pathlib.Path(__file__).parent.glob("test_*.py"):
        used |= set(re.findall(r"[\"'](gymkhana\.[a-z_]+\.[a-z_]+)[\"']",
                               path.read_text()))
    assert used <= declared, used - declared
    for role in registry.ROLE_GRANTS.values():
        assert set(role) <= declared


def test_a_plain_student_holds_no_student_admin_power(stub_iam):
    """The ordinary account: `student` alone cannot create or confirm a club."""
    pending = make_club("Pending", status=sm.OPEN)
    c = _client(stub_iam, STUDENT)
    assert c.post(f"{API}/clubs/create", {}, format="json").status_code == 403
    assert c.post(f"{API}/clubs/{pending.pk}/approve").status_code == 403
    pending.refresh_from_db()
    assert pending.status == "open"


def test_a_plain_student_is_not_a_club_head_of_anything(stub_iam, venues):
    """BR-GYM-010: holding the Club Head codes is not leading a club."""
    club = make_club()
    open_app = join(club, 1003, status=sm.OPEN)
    c = _client(stub_iam, STUDENT, uid=PLAIN)
    assert c.post(f"{API}/sessions", session_body(club.pk), format="json").status_code == 404
    assert c.post(f"{API}/clubs/{club.pk}/leadership",
                  {"coordinator_user_id": PLAIN, "co_coordinator_user_id": 1003},
                  format="json").status_code == 404
    assert c.post(f"{API}/memberships/approve", {"ids": [open_app.pk]},
                  format="json").json()[0]["code"] == "not_found"
    assert c.get(f"{API}/people?q=stu&kind=student").status_code == 403
    open_app.refresh_from_db()
    assert open_app.status == "open"


def test_faculty_reaches_only_report_review(stub_iam):
    c = _client(stub_iam, FACULTY, uid=2001)
    assert c.get(f"{API}/event-reports").status_code == 200
    assert c.get(f"{API}/clubs").status_code == 403
    assert c.post(f"{API}/event-reports/create", {}, format="json").status_code == 403


def test_role_switch_acting_as_student_admin_gets_no_club_head_power(stub_iam, venues):
    """One person, two designations: the acting role's permissions only."""
    club = make_club()
    stub_iam(make_session(user_id=COORD, permissions=STUDENT_ADMIN, modules=("gymkhana",),
                          roles=("student", "Student Admin"), active_role="Student Admin"))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    assert c.post(f"{API}/sessions", session_body(club.pk), format="json").status_code == 403
    assert c.get(f"{API}/memberships").status_code == 403
    assert c.get(f"{API}/clubs").status_code == 200


def test_an_open_clubs_leaders_cannot_act_until_it_is_confirmed(stub_iam, venues):
    """Ruling R10: every Club Head operation needs a confirmed club."""
    pending = make_club("Pending", status=sm.OPEN)
    c = _client(stub_iam, STUDENT, uid=COORD)
    assert c.post(f"{API}/sessions", session_body(pending.pk), format="json").status_code \
        == 404


def test_a_server_owned_field_in_the_body_is_ignored(stub_iam):
    club = make_club()
    c = _client(stub_iam, STUDENT, uid=PLAIN)
    r = c.post(f"{API}/memberships/apply",
               {"club_id": club.pk, "description": "x", "status": "confirmed",
                "user_id": 1003}, format="json")
    assert r.status_code == 201
    m = Membership.objects.get()
    assert (m.status, m.user_id) == ("open", PLAIN)


def test_unparseable_filters_are_400(stub_iam):
    c = _client(stub_iam, ALL)
    for path in ("clubs?status=closed", "clubs?category=x", "memberships?club=abc",
                 "bookings?from=yesterday", "bookings?club=1x", "polls/managed?club=x",
                 "budget-requests?club=x", "event-reports?club=x"):
        assert c.get(f"{API}/{path}").status_code == 400, path


def test_a_cookie_write_without_the_csrf_token_is_403(stub_iam):
    club = make_club()
    stub_iam(make_session(user_id=PLAIN, permissions=STUDENT, modules=("gymkhana",)))
    c = APIClient()
    c.cookies[settings.IAM_AUTH_COOKIE_NAME] = "tok-1"
    body = {"club_id": club.pk, "description": "x"}
    assert c.post(f"{API}/memberships/apply", body, format="json").status_code == 403
    r = c.post(f"{API}/memberships/apply", body, format="json",
               HTTP_X_CSRF_TOKEN=csrf.token_for("tok-1"))
    assert r.status_code == 201


def test_writes_are_throttled(stub_iam, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {
        **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "gymkhana_write": "2/hour"}}
    from rest_framework.throttling import SimpleRateThrottle
    SimpleRateThrottle.THROTTLE_RATES = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    try:
        c = _client(stub_iam, STUDENT)
        codes = [c.post(f"{API}/memberships/apply", {"club_id": 999, "description": "x"},
                        format="json").status_code for _ in range(3)]
        assert codes == [404, 404, 429]
    finally:
        from rest_framework.settings import api_settings
        SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES


def test_error_responses_carry_no_trace(stub_iam):
    c = _client(stub_iam, STUDENT_ADMIN)
    r = c.post(f"{API}/clubs/create", {"name": "x"}, format="json")
    assert r.status_code == 400
    assert "Traceback" not in r.content.decode() and "/home/" not in r.content.decode()


def test_ordinary_student_sees_no_open_club_by_id(stub_iam):
    pending = make_club("Pending", status=sm.OPEN)
    c = _client(stub_iam, STUDENT)
    assert [x["id"] for x in c.get(f"{API}/clubs").json()["results"]] == []
    assert Club.objects.filter(pk=pending.pk).exists()


@pytest.fixture
def venues(db):
    from datetime import timedelta

    from django.utils import timezone

    from modules.gymkhana.services.venues import seed_venue_list
    return seed_venue_list(names=["LHTC 101"],
                           effective_from=timezone.now() - timedelta(days=1))
