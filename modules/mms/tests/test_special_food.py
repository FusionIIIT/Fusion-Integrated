"""Special food — MMS-UC-019, 020, 021, 029. BR-MMS-028..031.
Workflows BW-MMS-11..15, CW-MMS-05."""
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.mms.domain.state_machine import InvalidTransition, RuleViolation
from modules.mms.models import SpecialFoodRequest
from modules.mms.services import operations as svc
from modules.mms.tests.factories import SpecialFoodFactory
from modules.mms.tests.helpers import (
    CARETAKER_ID,
    STUDENT_ID,
    admin,
    caretaker,
    student,
    warden,
)
from modules.mms.tests.helpers import (
    days_from_today as day,
)

pytestmark = pytest.mark.django_db


def _submit(lead=3, **kw):
    return svc.submit_special_food_request(
        actor=kw.pop("who", None) or student(), requested_date=day(lead), meal_type="dinner",
        food_details="Khichdi", reason="Fever", **kw)


# ---- submission: BR-MMS-028 ---------------------------------------------------
def test_student_submits_a_request(sent):
    r = _submit()
    assert (r.status, r.user_id, r.cost) == ("requested", STUDENT_ID, Decimal("50.00"))
    assert r.is_default_rejected is False
    assert len(sent("special_food_requested")) == 1


def test_br028_exactly_one_day_ahead_is_accepted():
    assert _submit(lead=1).status == "requested"


@pytest.mark.parametrize("lead", [0, -1, -7])
def test_br028_same_day_or_past_is_refused(lead, sent):
    with pytest.raises(RuleViolation) as e:
        _submit(lead=lead)
    assert e.value.rule_id == "BR-MMS-028"
    assert SpecialFoodRequest.objects.count() == 0
    assert sent() == []


def test_the_caller_supplies_the_charge():
    """BR-MMS-036: rates are external policy, so cost is an input, not a constant."""
    assert _submit(cost=Decimal("120.50")).cost == Decimal("120.50")


@pytest.mark.parametrize("who", [caretaker, warden, admin])
def test_only_students_submit_special_food(who):
    with pytest.raises(PermissionDeniedError):
        _submit(who=who())


# ---- review: BW-MMS-11 / 13 ---------------------------------------------------
@pytest.mark.parametrize(("action", "status"), [("approve", "approved"), ("reject", "rejected")])
def test_caretaker_decides_a_request(action, status, sent):
    r = SpecialFoodFactory()
    out = svc.review_special_food_request(actor=caretaker(), request_id=r.pk, action=action,
                                          remarks="r")
    assert (out.status, out.reviewed_by_user_id, out.remarks) == (status, CARETAKER_ID, "r")
    assert out.reviewed_at is not None
    assert out.is_default_rejected is False          # a human decision is not a timeout
    assert len(sent(f"special_food_{status}")) == 1


@pytest.mark.parametrize("current", ["approved", "rejected", "served", "cancelled"])
def test_only_a_requested_request_can_be_decided(current):
    r = SpecialFoodFactory(status=current)
    with pytest.raises(ConflictError):
        svc.review_special_food_request(actor=caretaker(), request_id=r.pk, action="approve")
    r.refresh_from_db()
    assert r.status == current


@pytest.mark.parametrize("who", [warden, student, admin])
def test_only_the_caretaker_decides_special_food(who):
    r = SpecialFoodFactory()
    with pytest.raises(PermissionDeniedError):
        svc.review_special_food_request(actor=who(), request_id=r.pk, action="approve")


def test_an_unknown_action_changes_nothing():
    r = SpecialFoodFactory()
    with pytest.raises(BadRequestError):
        svc.review_special_food_request(actor=caretaker(), request_id=r.pk, action="serve")
    r.refresh_from_db()
    assert r.status == "requested"


# ---- fulfilment: BW-MMS-14 / 15 -----------------------------------------------
def test_bw14_approved_then_served_stamps_served_at():
    r = SpecialFoodFactory(approved=True)
    out = svc.update_special_food_fulfillment(actor=caretaker(), request_id=r.pk, status="served")
    assert out.status == "served"
    assert out.served_at is not None and out.cancelled_at is None


def test_bw15_approved_then_cancelled_stamps_cancelled_at():
    r = SpecialFoodFactory(approved=True)
    out = svc.update_special_food_fulfillment(actor=caretaker(), request_id=r.pk,
                                              status="cancelled")
    assert out.status == "cancelled"
    assert out.cancelled_at is not None and out.served_at is None


@pytest.mark.parametrize(("current", "target"), [
    ("requested", "served"),        # BR-031: Served only after Approved
    ("requested", "cancelled"),     # ... and so is Cancelled
    ("rejected", "served"),
    ("served", "cancelled"),
    ("cancelled", "served"),
    ("served", "served"),
    ("approved", "requested"),
    ("approved", "rejected"),
    ("approved", "nonsense"),
])
def test_br031_illegal_fulfilment_transitions_are_refused(current, target):
    r = SpecialFoodFactory(status=current)
    with pytest.raises(InvalidTransition):
        svc.update_special_food_fulfillment(actor=caretaker(), request_id=r.pk, status=target)
    r.refresh_from_db()
    assert r.status == current
    assert r.served_at is None and r.cancelled_at is None


@pytest.mark.parametrize("who", [warden, student, admin])
def test_only_the_caretaker_updates_fulfilment(who):
    r = SpecialFoodFactory(approved=True)
    with pytest.raises(PermissionDeniedError):
        svc.update_special_food_fulfillment(actor=who(), request_id=r.pk, status="served")


# ---- UC-029: default rejection -------------------------------------------------
def test_bw12_undecided_request_is_default_rejected(sent):
    r = SpecialFoodFactory()
    out = svc.default_reject_special_food_request(request_id=r.pk)
    assert (out.status, out.is_default_rejected) == ("rejected", True)
    assert out.reviewed_at is not None
    assert out.reviewed_by_user_id is None            # nobody decided it
    [n] = sent("special_food_default_rejected")
    assert n.recipient_user_id == STUDENT_ID


@pytest.mark.parametrize("current", ["approved", "rejected", "served", "cancelled"])
def test_default_rejection_never_touches_a_request_that_was_decided(current, sent):
    r = SpecialFoodFactory(status=current)
    out = svc.default_reject_special_food_request(request_id=r.pk)
    assert (out.status, out.is_default_rejected) == (current, False)
    assert sent() == []


def test_default_rejection_is_idempotent(sent):
    r = SpecialFoodFactory()
    svc.default_reject_special_food_request(request_id=r.pk)
    svc.default_reject_special_food_request(request_id=r.pk)
    assert len(sent("special_food_default_rejected")) == 1


def test_a_default_rejected_request_cannot_then_be_approved():
    r = SpecialFoodFactory()
    svc.default_reject_special_food_request(request_id=r.pk)
    with pytest.raises(ConflictError):
        svc.review_special_food_request(actor=caretaker(), request_id=r.pk, action="approve")


def test_cw05_full_lifecycle_request_to_served():
    r = _submit()
    svc.review_special_food_request(actor=caretaker(), request_id=r.pk, action="approve")
    svc.update_special_food_fulfillment(actor=caretaker(), request_id=r.pk, status="served")
    r.refresh_from_db()
    assert r.status == "served"
