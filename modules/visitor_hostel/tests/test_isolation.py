"""Indenter A never reaches Indenter B's booking — by id, list, filter, or a write."""
import pytest

from modules.visitor_hostel.models import CancellationRequest, ModificationRequest
from modules.visitor_hostel.tests.conftest import (
    BASE,
    INDENTER,
    INDENTER_ID,
    OTHER_INDENTER_ID,
    make_booking,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls("modules.visitor_hostel.tests.urls")]


@pytest.fixture
def two(world):
    return make_booking(indenter=INDENTER_ID), make_booking(indenter=OTHER_INDENTER_ID)


def test_the_list_holds_only_ones_own(act, two):
    mine, _ = two
    rows = act(INDENTER_ID, INDENTER).get(f"{BASE}/bookings").data["results"]
    assert [r["id"] for r in rows] == [mine.pk]


def test_a_filter_does_not_widen_the_scope(act, two):
    rows = act(INDENTER_ID, INDENTER).get(f"{BASE}/bookings?status=pending").data
    assert {r["indenter_user_id"] for r in rows["results"]} == {INDENTER_ID}


def test_someone_elses_booking_is_a_404_not_a_403(act, two):
    _, theirs = two
    assert act(INDENTER_ID, INDENTER).get(f"{BASE}/bookings/{theirs.pk}").status_code == 404


def test_someone_elses_booking_cannot_be_cancelled_or_modified(act, two):
    _, theirs = two
    client = act(INDENTER_ID, INDENTER)
    assert client.post(f"{BASE}/bookings/{theirs.pk}/cancellation").status_code == 404
    assert client.post(f"{BASE}/bookings/{theirs.pk}/modifications",
                       {"occupants": 2}, format="json").status_code == 404
    assert not CancellationRequest.objects.exists()
    assert not ModificationRequest.objects.exists()


def test_an_indenter_sees_no_other_bills(act, two):
    rows = act(INDENTER_ID, INDENTER).get(f"{BASE}/bills")
    assert rows.status_code == 403          # bills are an office screen


def test_the_plain_student_can_book_and_see_their_booking(act, world):
    """The ordinary user: nothing but the student grant."""
    from modules.visitor_hostel import registry
    from modules.visitor_hostel.tests.conftest import requisition

    student = act(2001, tuple(registry.ROLE_GRANTS["student"]), kind="student")
    r = student.post(f"{BASE}/bookings", requisition(), format="json")
    assert r.status_code == 201
    assert student.get(f"{BASE}/bookings/{r.data['id']}").status_code == 200
