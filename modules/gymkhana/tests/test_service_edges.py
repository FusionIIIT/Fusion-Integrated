"""Refusals reachable only by calling a service directly, and filter edges."""
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import BadRequestError, DomainError, PermissionDeniedError
from fusion_auth.client import IamUnavailable
from modules.gymkhana.models import Booking
from modules.gymkhana.selectors import scoping
from modules.gymkhana.services import authz, memberships, people
from modules.gymkhana.services.errors import IdentityUnavailableError
from modules.gymkhana.tests.conftest import COORD, MEMBER, STUDENT, join
from modules.gymkhana.tests.conftest import people as users

pytestmark = pytest.mark.django_db
API = "/api/v1/gymkhana"


def test_authz_refuses_no_actor_and_an_actor_with_no_permission_check():
    with pytest.raises(PermissionDeniedError, match="Authentication"):
        authz.require(None, "gymkhana.club.view")
    with pytest.raises(PermissionDeniedError):
        authz.require(SimpleNamespace(user_id=1), "gymkhana.club.view")


def test_an_actor_without_an_id_sees_nothing():
    nobody = SimpleNamespace(has_permission=lambda c: True)
    assert not scoping.led_clubs(nobody).exists()
    assert not scoping.member_clubs(nobody).exists()
    assert not scoping.councillor_clubs(nobody).exists()
    assert not scoping.memberships_for(nobody).exists()


def test_approve_many_caps_the_batch_and_the_remarks(club):
    head = make_principal(user_id=COORD, permissions=STUDENT, modules=("gymkhana",))
    with pytest.raises(BadRequestError):
        memberships.approve_many(actor=head, ids=list(range(101)))
    with pytest.raises(DomainError):
        memberships.approve_many(actor=head, ids=[1], remarks="x" * 1001)


def test_cohort_of_a_non_student_is_empty(stub_iam):
    stub_iam(users=users())
    assert people.cohort_of(2001) == (None, "")
    assert people.cohort_of(1003) == (2023, "CSE")


def test_people_search_reports_an_unreachable_directory(stub_iam, club):
    fake = stub_iam(users=users())

    def down(**kw):
        raise IamUnavailable("down")
    fake.search_users = down
    head = make_principal(user_id=COORD, permissions=STUDENT, modules=("gymkhana",))
    with pytest.raises(IdentityUnavailableError):
        people.search(actor=head, q="stu", kind="student")


def test_people_search_for_student_admin(stub_iam):
    stub_iam(users=users())
    admin = make_principal(user_id=9001, permissions=("gymkhana.club.create",
                                                      "gymkhana.club.approve"),
                           modules=("gymkhana",), kind="staff")
    assert [p["user_id"] for p in people.search(actor=admin, q="fac", kind="faculty")] \
        == [2001, 2002]


def test_booking_list_date_filters(actors, club):
    join(club, MEMBER)
    today = timezone.localdate()
    for d in (1, 5, 9):
        Booking.objects.create(club=club, kind="session", venue_name="V",
                               date=today + timedelta(days=d), start_time="10:00",
                               end_time="11:00", description="d", created_by_user_id=COORD)
    c = actors.student(MEMBER)
    rows = c.get(f"{API}/bookings?club={club.pk}&from={(today + timedelta(days=2)).isoformat()}"
                 f"&to={(today + timedelta(days=6)).isoformat()}").json()["results"]
    assert [r["date"] for r in rows] == [(today + timedelta(days=5)).isoformat()]


def test_managed_polls_club_filter(actors, club, other_club):
    c = actors.student(COORD)
    assert c.get(f"{API}/polls/managed?club={other_club.pk}").json()["results"] == []
    assert c.get(f"{API}/polls/managed?club={club.pk}").status_code == 200


def test_r2_02_a_missing_report_says_what_to_do(actors, club):
    r = actors.faculty().get(f"{API}/event-reports/999999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "report_not_found"
    assert "report list" in r.json()["error"]["message"]


def test_r2_03_a_bad_batch_year_names_the_accepted_range():
    from modules.gymkhana.domain import rules
    with pytest.raises(rules.RuleViolation) as exc:
        rules.check_targets([rules.Target(1800)])
    assert "from 2000 to 2100" in exc.value.message
