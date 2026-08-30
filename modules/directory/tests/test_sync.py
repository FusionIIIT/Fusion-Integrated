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


class TestRetiringStaleEmployees:
    """Upserting alone never removes anybody.

    Somebody reclassified upstream would stay an employee here forever and go
    on drawing leave entitlement, and nothing about the sync's output would
    suggest anything was wrong.
    """

    def test_the_projection_drops_people_who_stopped_being_employees(self, stub_iam):
        from io import StringIO

        from django.core.management import call_command

        from conftest import make_session
        upsert([ref(1), ref(2), ref(3)])
        fake = stub_iam(make_session())
        # Upstream now says 2 and 3 are employees; 1 has been reclassified.
        fake.employees = [ref(2), ref(3)]
        fake.users = {1: ref(1, kind="student")}

        out = StringIO()
        call_command("sync_directory", stdout=out)

        assert "retired   1" in out.getvalue()
        assert UserRef.objects.get(user_id=1).kind == "student"
        assert sorted(
            UserRef.objects.filter(kind__in=("faculty", "staff"))
            .values_list("user_id", flat=True)) == [2, 3]

    def test_it_reports_both_directions_of_disagreement(self, stub_iam):
        from conftest import make_session
        from modules.directory.contracts import employee_projection_disagreement

        upsert([ref(1), ref(2)])
        fake = stub_iam(make_session())
        fake.employees = [ref(2), ref(9)]

        missing, stale = employee_projection_disagreement()

        assert missing == [9]
        assert stale == [1]

    def test_an_unreachable_service_is_not_agreement(self, stub_iam):
        from conftest import make_session
        from fusion_auth.client import IamUnavailable
        from modules.directory.contracts import employee_projection_disagreement

        fake = stub_iam(make_session())

        def down(**kwargs):
            raise IamUnavailable("down")
            yield

        fake.iter_employees = down

        assert employee_projection_disagreement() is None
