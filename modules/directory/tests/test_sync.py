"""A bad upstream row must not take the whole projection down with it."""
import pytest

from modules.directory.models import UserRef
from modules.directory.services.sync import unstorable, upsert

pytestmark = pytest.mark.django_db


def ref(user_id, username="asha", kind="staff"):
    return UserRef(user_id=user_id, username=username,
                   display_name="Asha", kind=kind)


def test_a_row_that_fits_is_stored():
    assert upsert([ref(1)]) == 1
    assert UserRef.objects.filter(user_id=1).exists()


def test_an_oversized_username_is_identified_rather_than_raising():
    assert "username is 116 characters" in unstorable(ref(2, username="x" * 116))


def test_a_row_that_fits_reports_no_problem():
    assert unstorable(ref(3)) == ""


def test_one_bad_row_does_not_lose_the_good_ones():
    rejected = []

    # Real upstream data: an entire import line pasted into a username.
    written = upsert([ref(1), ref(2, username="x" * 116), ref(3)], rejected=rejected)

    assert written == 2
    assert sorted(UserRef.objects.values_list("user_id", flat=True)) == [1, 3]
    assert [r[0] for r in rejected] == [2]


def test_the_username_is_not_truncated_to_make_it_fit():
    upsert([ref(2, username="x" * 116)])

    # A shortened identifier is a wrong identifier, and could collide.
    assert not UserRef.objects.filter(user_id=2).exists()
