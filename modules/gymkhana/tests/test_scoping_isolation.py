"""Person A never sees person B's rows: by id, by filter, or by download."""
import datetime

import pytest

from modules.gymkhana.models import (
    ClubBudgetRequest,
    ClubEventReport,
    ClubMembership,
    PollVote,
)
from modules.gymkhana.tests.support import (
    ADMIN,
    API,
    COUNCILLOR,
    HEAD,
    OTHER_CO_HEAD,
    OTHER_FACULTY,
    OTHER_HEAD,
    OTHER_STUDENT,
    STUDENT,
    make_club,
    make_poll,
    now,
    people,
    sign_in,
    upload,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def two_clubs():
    people()
    mine = make_club()
    theirs = make_club("Music Club", heads=(OTHER_HEAD, OTHER_CO_HEAD), councillor=OTHER_FACULTY)
    return mine, theirs


def ids(response):
    assert response.status_code == 200
    return [row["id"] for row in response.json()["results"]]


def test_br_gym_004_an_open_club_is_invisible_to_outsiders(stub_iam, two_clubs):
    club = make_club("Drama Club", status="open")
    assert club.pk not in ids(sign_in(stub_iam, STUDENT).get(f"{API}/clubs/"))
    for uid, role, seen in ((STUDENT, "student", 404), (OTHER_FACULTY, "faculty", 404),
                            (HEAD, "student", 200), (COUNCILLOR, "faculty", 200),
                            (ADMIN, "student_admin", 200)):
        client = sign_in(stub_iam, uid, role)
        assert client.get(f"{API}/clubs/{club.pk}/").status_code == seen, uid


def test_br_gym_010_another_clubs_applications_are_not_found(stub_iam, two_clubs):
    mine, _ = two_clubs
    row = ClubMembership.objects.create(club=mine, student_id=STUDENT)
    client = sign_in(stub_iam, OTHER_HEAD)
    assert client.post(f"{API}/memberships/{row.pk}/approve/", {}).status_code == 404
    assert ids(client.get(f"{API}/memberships/?club_id={mine.pk}")) == []
    row.refresh_from_db()
    assert row.status == "open"


def test_a_student_sees_only_their_own_applications(stub_iam, two_clubs):
    mine, theirs = two_clubs
    own = ClubMembership.objects.create(club=mine, student_id=STUDENT)
    ClubMembership.objects.create(club=mine, student_id=OTHER_STUDENT)
    ClubMembership.objects.create(club=theirs, student_id=STUDENT)
    client = sign_in(stub_iam, STUDENT)
    assert ids(client.get(f"{API}/memberships/?club_id={mine.pk}")) == [own.pk]


def test_br_gym_010_nobody_approves_their_own_application(stub_iam, two_clubs):
    mine, _ = two_clubs
    row = ClubMembership.objects.create(club=mine, student_id=HEAD)
    response = sign_in(stub_iam, HEAD).post(f"{API}/memberships/{row.pk}/approve/", {})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "own_application"


def test_br_gym_013_a_poll_reaches_only_its_own_batch_and_branch(stub_iam, two_clubs):
    mine, _ = two_clubs
    poll = make_poll(mine, ("2024", "CSE"))
    assert ids(sign_in(stub_iam, STUDENT).get(f"{API}/polls/")) == [poll.pk]
    outsider = sign_in(stub_iam, OTHER_STUDENT)
    assert ids(outsider.get(f"{API}/polls/")) == []
    assert outsider.get(f"{API}/polls/{poll.pk}/").status_code == 404


def test_br_gym_013_batch_and_branch_must_match_in_the_same_group(stub_iam, two_clubs):
    """2023 ECE is in neither 2023 CSE nor 2024 ECE, though each half matches one of them."""
    mine, _ = two_clubs
    poll = make_poll(mine, ("2023", "CSE"), ("2024", "ECE"))
    client = sign_in(stub_iam, OTHER_STUDENT)
    assert ids(client.get(f"{API}/polls/")) == []
    body = {"choice_id": poll.choices.first().pk}
    assert client.post(f"{API}/polls/{poll.pk}/vote/", body).status_code == 403
    assert not PollVote.objects.exists()


def test_br_gym_014_an_expired_poll_is_closed_to_voters_but_not_to_its_club(stub_iam, two_clubs):
    mine, _ = two_clubs
    poll = make_poll(mine, expires_in=-datetime.timedelta(minutes=1))
    assert sign_in(stub_iam, STUDENT).get(f"{API}/polls/{poll.pk}/").status_code == 404
    assert sign_in(stub_iam, HEAD).get(f"{API}/polls/{poll.pk}/").status_code == 200


def test_another_clubs_budget_is_not_found(stub_iam, two_clubs):
    mine, _ = two_clubs
    row = ClubBudgetRequest.objects.create(
        club=mine, submitted_by_id=HEAD, amount=5, purpose="x", supporting_file=upload())
    for uid in (OTHER_HEAD, STUDENT):
        client = sign_in(stub_iam, uid)
        assert ids(client.get(f"{API}/budgets/")) == []
        for path in (f"budgets/{row.pk}/", f"budgets/{row.pk}/file/",
                     f"budgets/?club_id={mine.pk}"):
            assert client.get(f"{API}/{path}").status_code == 404, path


def test_br_gym_021_only_the_assigned_councillor_reads_a_report(stub_iam, two_clubs):
    mine, _ = two_clubs
    row = ClubEventReport.objects.create(
        club=mine, submitted_by_id=HEAD, student_incharge_id=HEAD, event_name="x",
        event_date=now(), report_file=upload())
    paths = (f"reports/{row.pk}/", f"reports/{row.pk}/file/", f"reports/?club_id={mine.pk}")
    councillor = sign_in(stub_iam, COUNCILLOR, "faculty")
    other = sign_in(stub_iam, OTHER_FACULTY, "faculty")
    assert ids(other.get(f"{API}/reports/")) == []
    for path in paths:
        assert other.get(f"{API}/{path}").status_code == 404, path
    councillor = sign_in(stub_iam, COUNCILLOR, "faculty")
    for path in paths:
        assert councillor.get(f"{API}/{path}").status_code == 200, path
    admin = sign_in(stub_iam, ADMIN, "student_admin")
    assert admin.get(f"{API}/reports/").status_code == 403
