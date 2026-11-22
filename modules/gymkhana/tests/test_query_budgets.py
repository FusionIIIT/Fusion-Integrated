"""List endpoints cost the same number of queries with 2 rows as with 20."""
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from modules.gymkhana.models import (
    Booking,
    BudgetRequest,
    EventReport,
    Membership,
    Poll,
    PollChoice,
    PollTarget,
    Vote,
)
from modules.gymkhana.tests.conftest import COORD, DRIVE, MEMBER, make_club

pytestmark = pytest.mark.django_db
API = "/api/v1/gymkhana"


def populate(n):
    for i in range(n):
        club = make_club(f"Club {i}-{n}", coord=COORD if i == 0 else 5000 + 2 * i + n * 100,
                         co=5001 + 2 * i + n * 100)
        Membership.objects.create(club=club, user_id=MEMBER, description="x",
                                  status="confirmed")
        Membership.objects.create(club=club, user_id=7000 + i + n * 100, description="x")
        day = timezone.localdate() + timedelta(days=1 + i)
        Booking.objects.create(club=club, kind="session", venue_name="V", date=day,
                               start_time="10:00", end_time="11:00", description="d",
                               created_by_user_id=COORD)
        BudgetRequest.objects.create(club=club, purpose="p", description="d", amount=1,
                                     document_link=DRIVE, document_file_id="x",
                                     submitted_by_user_id=COORD)
        EventReport.objects.create(club=club, student_incharge_user_id=MEMBER,
                                   event_name="e", event_at=timezone.now(), description="d",
                                   report_link=DRIVE, report_file_id="x",
                                   submitted_by_user_id=COORD)
        poll = Poll.objects.create(club=club, title="t", description="d",
                                   expires_on=timezone.localdate() + timedelta(days=5),
                                   created_by_user_id=COORD)
        a = PollChoice.objects.create(poll=poll, label="a", position=0)
        PollChoice.objects.create(poll=poll, label="b", position=1)
        PollTarget.objects.create(poll=poll, batch_year=2023, discipline="CSE")
        Vote.objects.create(poll=poll, choice=a, user_id=8000 + i + n * 100)


def leader_all_clubs():
    from modules.gymkhana.models import Club, LeadershipAssignment
    for club in Club.objects.exclude(leaders__user_id=COORD):
        LeadershipAssignment.objects.filter(club=club, role="coordinator").update(
            user_id=COORD)


LISTS = [("student", COORD, "clubs"), ("student", COORD, "me/clubs"),
         ("student", COORD, "memberships"), ("student", MEMBER, "bookings"),
         ("student", 1003, "polls"), ("student", COORD, "polls/managed"),
         ("student", COORD, "budget-requests"), ("student", COORD, "event-reports"),
         ("faculty", 2001, "event-reports"), ("admin", 9001, "clubs")]


def count(actors, who, uid, path):
    client = {"student": lambda: actors.student(uid), "faculty": lambda: actors.faculty(uid),
              "admin": actors.admin}[who]()
    # Warm the directory projection first; its one-off fill is not a per-row cost.
    client.get(f"{API}/{path}")
    with CaptureQueriesContext(connection) as ctx:
        assert client.get(f"{API}/{path}").status_code == 200
    return len(ctx)


@pytest.mark.parametrize("who,uid,path", LISTS)
def test_list_query_count_does_not_grow_with_rows(actors, who, uid, path):
    populate(2)
    leader_all_clubs()
    small = count(actors, who, uid, path)
    populate(20)
    leader_all_clubs()
    large = count(actors, who, uid, path)
    assert large == small, f"{path}: {small} queries for 2 clubs, {large} for 22"
    assert small <= 8, f"{path} uses {small} queries"
