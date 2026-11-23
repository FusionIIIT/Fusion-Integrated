"""Both gates, and only the acting role's permissions."""
import pytest
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from modules.gymkhana.registry import PERMISSIONS, ROLE_GRANTS
from modules.gymkhana.selectors.access import acting_permissions, may
from modules.gymkhana.tests.support import (
    ADMIN,
    API,
    COUNCILLOR,
    HEAD,
    STUDENT,
    make_club,
    people,
    sign_in,
    slot,
)

pytestmark = pytest.mark.django_db

READS = {
    "access/": "gymkhana.club.view", "venues/": "gymkhana.booking.view",
    "clubs/": "gymkhana.club.view", "bookings/": "gymkhana.booking.view",
    "memberships/": "gymkhana.membership.view", "polls/": "gymkhana.poll.view",
    "budgets/": "gymkhana.budget.view", "reports/": "gymkhana.report.view",
    "people/": "gymkhana.club.create", "poll-options/": "gymkhana.poll.create",
}
WRITES = {
    "clubs/": "gymkhana.club.create", "clubs/1/confirm/": "gymkhana.club.approve",
    "clubs/1/leadership/": "gymkhana.club.manage",
    "bookings/session/": "gymkhana.booking.create",
    "bookings/event/": "gymkhana.booking.create",
    "memberships/apply/": "gymkhana.membership.create",
    "memberships/1/approve/": "gymkhana.membership.approve",
    "polls/": "gymkhana.poll.create", "polls/1/vote/": "gymkhana.poll.vote",
    "budgets/": "gymkhana.budget.create", "reports/": "gymkhana.report.create",
}
ALL = {code for code, _ in PERMISSIONS}


def test_every_permission_named_here_is_declared():
    assert set(READS.values()) | set(WRITES.values()) <= ALL
    assert {c for codes in ROLE_GRANTS.values() for c in codes} <= ALL


@pytest.mark.parametrize("path", READS)
def test_a_read_needs_the_permission_and_the_module(stub_iam, path):
    lacking = sign_in(stub_iam, STUDENT, permissions=ALL - {READS[path], "gymkhana.club.manage"})
    assert lacking.get(f"{API}/{path}").status_code == 403
    ungranted = sign_in(stub_iam, STUDENT, permissions=ALL, modules=())
    assert ungranted.get(f"{API}/{path}").status_code == 403
    assert APIClient().get(f"{API}/{path}").status_code == 401


@pytest.mark.parametrize("path", WRITES)
def test_a_write_needs_the_permission_and_the_module(stub_iam, path):
    lacking = sign_in(stub_iam, STUDENT, permissions=ALL - {WRITES[path]})
    assert lacking.post(f"{API}/{path}", {}, format="json").status_code == 403
    ungranted = sign_in(stub_iam, STUDENT, permissions=ALL, modules=())
    assert ungranted.post(f"{API}/{path}", {}, format="json").status_code == 403
    assert APIClient().post(f"{API}/{path}", {}, format="json").status_code == 401


def test_the_plain_student_reaches_every_student_screen(stub_iam):
    """Acting as ug_student, a designation this module grants nothing to."""
    people()
    make_club()
    client = sign_in(stub_iam, STUDENT, "student", "ug_student")
    for path in ("access/", "clubs/", "memberships/", "polls/", "bookings/", "venues/"):
        assert client.get(f"{API}/{path}").status_code == 200, path


def test_acting_as_student_an_admin_cannot_approve_a_club(stub_iam):
    people()
    club = make_club(status="open")
    as_student = sign_in(stub_iam, ADMIN, "student", "student_admin", active="student")
    assert as_student.post(f"{API}/clubs/{club.pk}/confirm/").status_code == 403
    assert as_student.get(f"{API}/clubs/{club.pk}/").status_code == 404
    as_admin = sign_in(stub_iam, ADMIN, "student", "student_admin", active="student_admin")
    assert as_admin.post(f"{API}/clubs/{club.pk}/confirm/").status_code == 200


def test_acting_as_student_admin_the_student_permissions_do_not_count():
    principal = make_principal(
        roles=("student", "student_admin"), active_role="student_admin", kind="student",
        permissions=set(ROLE_GRANTS["student"]) | set(ROLE_GRANTS["student_admin"]),
    )
    assert acting_permissions(principal) == sorted(ROLE_GRANTS["student_admin"])
    assert not may(principal, "gymkhana.poll.vote")


def test_a_permission_the_session_lacks_is_never_granted_by_the_registry():
    principal = make_principal(roles=("student",), active_role="student", permissions=())
    assert acting_permissions(principal) == []


def test_access_names_the_clubs_led(stub_iam):
    people()
    club = make_club()
    assert sign_in(stub_iam, STUDENT).get(f"{API}/access/").json()["clubs_led"] == []
    led = sign_in(stub_iam, HEAD).get(f"{API}/access/").json()["clubs_led"]
    assert [c["id"] for c in led] == [club.pk]


def test_only_someone_who_assigns_people_may_search_them(stub_iam):
    people()
    make_club()
    assert sign_in(stub_iam, STUDENT).get(f"{API}/people/?q=u10").status_code == 404
    assert sign_in(stub_iam, HEAD).get(f"{API}/people/?q=u10").status_code == 200
    assert sign_in(stub_iam, COUNCILLOR, "faculty").get(f"{API}/people/?q=u1").status_code == 403


def test_a_people_search_is_never_an_enumeration(stub_iam):
    people()
    make_club()
    client = sign_in(stub_iam, HEAD)
    assert client.get(f"{API}/people/?q=").json() == {"results": []}
    assert client.get(f"{API}/people/?q=u1").json() == {"results": []}


def test_a_write_by_cookie_needs_the_csrf_header(stub_iam, settings):
    people()
    club = make_club()
    sign_in(stub_iam, HEAD)
    client = APIClient()
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = "abc"
    response = client.post(f"{API}/bookings/session/", slot(club), format="json")
    assert response.status_code == 403


def test_writes_are_throttled_and_reads_are_not(stub_iam, monkeypatch):
    from core.api.throttling import PrincipalScopedThrottle

    monkeypatch.setattr(PrincipalScopedThrottle, "THROTTLE_RATES",
                        {"gymkhana_write": "1/hour", "directory_search": "9/hour"})
    people()
    club = make_club()
    client = sign_in(stub_iam, STUDENT)
    body = {"club_id": club.pk, "description": "x"}
    assert client.post(f"{API}/memberships/apply/", body, format="json").status_code == 201
    assert client.post(f"{API}/memberships/apply/", body, format="json").status_code == 429
    assert client.get(f"{API}/memberships/").status_code == 200


@pytest.mark.parametrize("query", [
    "memberships/?club_id=abc", "polls/?club_id=-1", "budgets/?club_id=1.5",
    "reports/?club_id=%00", "bookings/?club_id=99999999999999999999999",
    "bookings/?booking_date=abc", "bookings/?booking_date=2026-13-40",
])
def test_an_unusable_filter_is_a_400(stub_iam, query):
    client = sign_in(stub_iam, HEAD, permissions=ALL)
    assert client.get(f"{API}/{query}").status_code == 400


def test_a_nul_in_a_text_filter_is_not_a_500(stub_iam):
    assert sign_in(stub_iam, HEAD).get(f"{API}/bookings/?venue=%00").status_code == 200


def test_sessions_are_built_the_way_the_iam_builds_them():
    session = make_session(roles=("student", "student_admin"), active_role="student")
    assert session.active_role in session.roles
