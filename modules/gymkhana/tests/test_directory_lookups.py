"""Directory lookups when the identity service answers sparsely, or not at all."""
import pytest

from fusion_auth.client import IamUnavailable, UserRef
from modules.gymkhana.selectors import people as lookups
from modules.gymkhana.tests.support import (
    API,
    HEAD,
    STUDENT,
    make_club,
    make_poll,
    people,
    sign_in,
)

pytestmark = pytest.mark.django_db


def person(user_id, **changes):
    fields = {"user_id": user_id, "username": f"stu{user_id}", "display_name": f"S{user_id}",
              "kind": "student", "email": "private@example.invalid", **changes}
    return UserRef(**fields)


class Search:
    def search_users(self, **kwargs):
        return [person(1), person(2, kind="faculty"), person(3, is_active=False)]


def test_a_search_returns_only_what_a_picker_needs(stub_iam, monkeypatch):
    people()
    make_club()
    client = sign_in(stub_iam, HEAD)
    monkeypatch.setattr(lookups, "get_client", Search)
    rows = client.get(f"{API}/people/?q=stu&kind=student").json()["results"]
    assert rows == [{"user_id": 1, "username": "stu1", "display_name": "S1"}]
    rows = client.get(f"{API}/people/?q=stu&kind=faculty").json()["results"]
    assert [r["user_id"] for r in rows] == [2]


def test_poll_options_are_the_groups_that_exist(stub_iam):
    people()
    make_club()
    client = sign_in(stub_iam, HEAD)
    stub = client.get(f"{API}/poll-options/")
    assert stub.json() == {"batches": [], "branches": []}


def test_poll_options_are_for_club_heads(stub_iam):
    people()
    make_club()
    assert sign_in(stub_iam, STUDENT).get(f"{API}/poll-options/").status_code == 404


class Down:
    def search_users(self, **kwargs):
        raise IamUnavailable("down")

    def academic_filters(self):
        raise IamUnavailable("down")


@pytest.mark.parametrize("path", ["people/?q=stu", "poll-options/"])
def test_an_unreachable_directory_is_a_503_that_says_so(stub_iam, monkeypatch, path):
    people()
    make_club()
    client = sign_in(stub_iam, HEAD)
    monkeypatch.setattr(lookups, "get_client", Down)
    response = client.get(f"{API}/{path}")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "directory_unavailable"


def test_poll_options_are_text(stub_iam, monkeypatch):
    class Filters:
        def academic_filters(self):
            return {"batch_years": [2024], "disciplines": ["CSE"]}

    people()
    make_club()
    client = sign_in(stub_iam, HEAD)
    monkeypatch.setattr(lookups, "get_client", Filters)
    assert client.get(f"{API}/poll-options/").json() == {"batches": ["2024"], "branches": ["CSE"]}


def test_br_gym_013_a_student_with_no_batch_matches_only_open_groups(stub_iam):
    people()
    unknown = 5555
    club = make_club()
    targeted, everyone = make_poll(club, ("2024", "CSE")), make_poll(club, ("all", "all"))
    rows = sign_in(stub_iam, unknown).get(f"{API}/polls/").json()["results"]
    assert [r["id"] for r in rows] == [everyone.pk]
    assert targeted.pk not in {r["id"] for r in rows}


def test_a_person_the_directory_does_not_hold_has_a_blank_name_not_an_error(stub_iam):
    make_club()
    row = sign_in(stub_iam, STUDENT).get(f"{API}/clubs/").json()["results"][0]
    assert row["coordinator_name"] == ""
