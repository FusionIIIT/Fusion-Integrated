"""gymkhana's public contract, and the directory contract it added (ruling R9)."""
import pytest

from fusion_auth.client import IamUnavailable
from modules.directory import contracts as directory
from modules.gymkhana import contracts
from modules.gymkhana.tests.conftest import COORD, MEMBER, PLAIN, join, make_club


@pytest.mark.django_db
def test_get_club_affiliations_is_batched_and_complete():
    club = make_club()
    join(club, MEMBER)
    join(club, PLAIN, status="open")
    out = contracts.get_club_affiliations([COORD, MEMBER, PLAIN, None])
    assert out[COORD].leads == ("Robotics",) and out[COORD].member_of == ()
    assert out[MEMBER].member_of == ("Robotics",)
    assert out[PLAIN] == contracts.ClubAffiliationDTO(PLAIN, (), ())
    assert contracts.get_club_affiliations([]) == {}


def test_students_in_cohorts_pages_every_batch_and_branch(stub_iam):
    fake = stub_iam()
    pages = iter([{"count": 3, "results": [{"user_id": 1}, {"user_id": 2}]},
                  {"count": 3, "results": [{"user_id": 3}, {"user_id": None}]},
                  {"count": 1, "results": [{"user_id": 2}]}])
    fake.academic_directory = lambda **f: next(pages)
    assert directory.students_in_cohorts([2023, 2024], []) == [1, 2, 3]


def test_students_in_cohorts_stops_on_an_empty_page(stub_iam):
    fake = stub_iam()
    fake.directory = {"count": 99, "results": []}
    assert directory.students_in_cohorts([2023], ["CSE", " "]) == []


def test_students_in_cohorts_raises_rather_than_return_a_partial_audience(stub_iam):
    fake = stub_iam()
    fake.directory_error = IamUnavailable("down")
    with pytest.raises(IamUnavailable):
        directory.students_in_cohorts([2023], ["CSE"])
