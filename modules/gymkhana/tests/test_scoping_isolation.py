"""Person A never sees person B's rows: not by list, filter or id (test_recruiter_isolation's model)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.models import Booking, BudgetRequest, EventReport, Poll
from modules.gymkhana.tests.conftest import (
    COORD,
    COUNCILLOR,
    DRIVE,
    MEMBER,
    OTHER_COORD,
    OTHER_FACULTY,
    PLAIN,
    join,
    poll_body,
)

pytestmark = pytest.mark.django_db
API = "/api/v1/gymkhana"


@pytest.fixture
def two_clubs(club, other_club):
    tomorrow = timezone.localdate() + timedelta(days=1)
    for c in (club, other_club):
        Booking.objects.create(club=c, kind="session", venue_name=f"V{c.pk}", date=tomorrow,
                               start_time="10:00", end_time="11:00", description="d",
                               created_by_user_id=COORD)
        BudgetRequest.objects.create(club=c, purpose="p", description="d", amount=1,
                                     document_link=DRIVE, document_file_id="1AbCdEfGhIjK",
                                     submitted_by_user_id=COORD)
        EventReport.objects.create(club=c, student_incharge_user_id=MEMBER, event_name="e",
                                   event_at=timezone.now(), description="d",
                                   report_link=DRIVE, report_file_id="1AbCdEfGhIjK",
                                   submitted_by_user_id=COORD)
    join(club, MEMBER)
    join(other_club, PLAIN, status=sm.OPEN)
    return club, other_club


def ids(response):
    return [r["id"] for r in response.json()["results"]]


def test_a_club_head_sees_only_their_clubs_budget_requests(actors, two_clubs):
    club, other = two_clubs
    head = actors.student(COORD)
    assert ids(head.get(f"{API}/budget-requests")) == [club.budget_requests.get().pk]
    assert ids(head.get(f"{API}/budget-requests?club={other.pk}")) == []


def test_a_member_cannot_see_budget_requests(actors, two_clubs):
    assert ids(actors.student(MEMBER).get(f"{API}/budget-requests")) == []


def test_a_club_head_sees_only_their_clubs_reports_by_list_filter_and_id(actors, two_clubs):
    club, other = two_clubs
    head = actors.student(COORD)
    assert ids(head.get(f"{API}/event-reports")) == [club.reports.get().pk]
    assert ids(head.get(f"{API}/event-reports?club={other.pk}")) == []
    assert head.get(f"{API}/event-reports/{other.reports.get().pk}").status_code == 404


def test_br_gym_021_a_councillor_sees_only_their_assigned_club(actors, two_clubs):
    club, other = two_clubs
    mine = actors.faculty(COUNCILLOR)
    assert ids(mine.get(f"{API}/event-reports")) == [club.reports.get().pk]
    assert mine.get(f"{API}/event-reports/{other.reports.get().pk}").status_code == 404
    theirs = actors.faculty(OTHER_FACULTY)
    assert ids(theirs.get(f"{API}/event-reports")) == [other.reports.get().pk]


def test_student_admin_is_not_a_report_reader(actors, two_clubs):
    """Ruling R8: not Student Admin."""
    assert actors.admin().get(f"{API}/event-reports").status_code == 403


def test_bookings_reach_only_leaders_and_confirmed_members(actors, two_clubs):
    club, other = two_clubs
    assert ids(actors.student(MEMBER).get(f"{API}/bookings")) == [club.bookings.get().pk]
    assert ids(actors.student(PLAIN).get(f"{API}/bookings")) == []
    assert ids(actors.student(OTHER_COORD).get(f"{API}/bookings")) == [other.bookings.get().pk]
    assert ids(actors.student(COORD).get(f"{API}/bookings?club={other.pk}")) == []


def test_memberships_own_plus_led_clubs_only(actors, two_clubs):
    _, other = two_clubs
    assert {m["user_id"] for m in actors.student(COORD).get(f"{API}/memberships")
            .json()["results"]} == {MEMBER}
    assert {m["club"] for m in actors.student(PLAIN).get(f"{API}/memberships")
            .json()["results"]} == {other.pk}
    assert ids(actors.student(MEMBER).get(f"{API}/memberships?club={other.pk}")) == []


def test_poll_counts_reach_only_the_creating_clubs_leaders(actors, two_clubs):
    club, _ = two_clubs
    actors.student(COORD).post(f"{API}/polls/create", poll_body(club.pk), format="json")
    assert ids(actors.student(OTHER_COORD).get(f"{API}/polls/managed")) == []
    assert len(ids(actors.student(COORD).get(f"{API}/polls/managed"))) == 1
    student_view = actors.student(PLAIN).get(f"{API}/polls").json()["results"][0]
    assert "votes" not in student_view["choices"][0]
    assert "total_votes" not in student_view


def test_a_club_head_cannot_create_a_poll_for_another_club(actors, two_clubs):
    _, other = two_clubs
    r = actors.student(COORD).post(f"{API}/polls/create", poll_body(other.pk), format="json")
    assert r.status_code == 404
    assert not Poll.objects.exists()


def test_a_club_head_cannot_submit_for_another_club(actors, two_clubs):
    _, other = two_clubs
    head = actors.student(COORD)
    assert head.post(f"{API}/budget-requests/create",
                     {"club_id": other.pk, "purpose": "p", "description": "d",
                      "amount": "1.00", "document_url": DRIVE},
                     format="json").status_code == 404
    assert head.post(f"{API}/event-reports/create",
                     {"club_id": other.pk, "student_incharge_user_id": MEMBER,
                      "event_name": "e", "event_at": timezone.now().isoformat(),
                      "description": "d", "report_url": DRIVE},
                     format="json").status_code == 404
