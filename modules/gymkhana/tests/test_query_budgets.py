"""The same number of queries for 2 rows and for 20, so an N+1 fails the build."""
import datetime

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.directory.models import UserRef
from modules.gymkhana.models import (
    ClubBudgetRequest,
    ClubEventReport,
    ClubMembership,
    VenueBooking,
)
from modules.gymkhana.tests.support import (
    API,
    COUNCILLOR,
    HEAD,
    STUDENT,
    make_club,
    make_poll,
    now,
    people,
    sign_in,
)

pytestmark = pytest.mark.django_db


def clubs(club, n):
    make_club(f"Club {n}")


def bookings(club, n):
    VenueBooking.objects.create(
        club=club, venue="Hall 1", booking_date=datetime.date(2027, 1, 1 + n), booked_by_id=HEAD,
        start_time=datetime.time(10), end_time=datetime.time(11))


def memberships(club, n):
    UserRef.objects.create(user_id=2000 + n, username=f"m{n}", display_name=f"M{n}", kind="student")
    ClubMembership.objects.create(club=club, student_id=2000 + n)


def polls(club, n):
    make_poll(club, ("2024", "CSE"), ("2023", "ECE"), title=f"Poll {n}")


def budgets(club, n):
    ClubBudgetRequest.objects.create(
        club=club, submitted_by_id=HEAD, amount=n, purpose="x", supporting_file="budgets/x.pdf")


def reports(club, n):
    ClubEventReport.objects.create(
        club=club, submitted_by_id=HEAD, student_incharge_id=HEAD, event_name=f"E{n}",
        event_date=now(), report_file="reports/x.pdf")


CASES = [
    (clubs, "clubs/", STUDENT, "student", 4),
    (bookings, "bookings/", STUDENT, "student", 1),
    (memberships, "memberships/?club_id={club}", HEAD, "student", 4),
    (polls, "polls/", STUDENT, "student", 5),
    (budgets, "budgets/?club_id={club}", HEAD, "student", 2),
    (reports, "reports/?club_id={club}", COUNCILLOR, "faculty", 4),
]


@pytest.mark.parametrize(("add", "path", "user", "role", "budget"), CASES,
                         ids=[c[0].__name__ for c in CASES])
def test_a_list_costs_the_same_at_2_rows_and_at_20(stub_iam, add, path, user, role, budget):
    people()
    club = make_club()
    client = sign_in(stub_iam, user, role)
    url = f"{API}/{path.format(club=club.pk)}"

    def cost():
        with CaptureQueriesContext(connection) as queries:
            assert client.get(url).status_code == 200
        return len(queries)

    for n in range(2):
        add(club, n)
    small = cost()
    for n in range(2, 20):
        add(club, n)
    assert cost() == small
    assert small <= budget
