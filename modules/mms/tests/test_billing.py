"""Monthly billing — MMS-UC-030 (generate), MMS-UC-010 (finalize/publish), MMS-UC-011 (view).
BR-MMS-016..019, 030, 040. Workflow BW-MMS-16."""
from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import PermissionDeniedError
from modules.mms.models import MessBill
from modules.mms.services import operations as svc
from modules.mms.tests.factories import (
    BillFactory,
    RebateFactory,
    RegistrationFactory,
    SpecialFoodFactory,
)
from modules.mms.tests.helpers import (
    CARETAKER_ID,
    OTHER_STUDENT_ID,
    STUDENT_ID,
    admin,
    caretaker,
    student,
    warden,
)

pytestmark = pytest.mark.django_db
D = Decimal
MAY = date(2026, 5, 1)
BASE, RATE = D("3000.00"), D("100.00")


def _bill(user=STUDENT_ID, month=MAY, **kw):
    bills = svc.generate_monthly_bills(billing_month=month, **kw)
    return next(b for b in bills if b.user_id == user)


@pytest.fixture
def registered():
    return RegistrationFactory(approved=True)


# ---- who gets a bill ----------------------------------------------------------
def test_br016_only_registered_students_are_billed():
    RegistrationFactory(user_id=1, approved=True)
    RegistrationFactory(user_id=2, status="submitted")
    RegistrationFactory(user_id=3, rejected=True)
    assert [b.user_id for b in svc.generate_monthly_bills(billing_month=MAY)] == [1]


def test_a_student_with_two_registrations_gets_one_bill():
    RegistrationFactory(approved=True)
    RegistrationFactory(approved=True)
    assert len(svc.generate_monthly_bills(billing_month=MAY)) == 1


def test_no_registered_students_no_bills():
    assert svc.generate_monthly_bills(billing_month=MAY) == []


# ---- BR-MMS-017: components ---------------------------------------------------
def test_bw16_a_plain_bill_is_the_base_amount_in_generated_state(registered):
    b = _bill()
    assert (b.base_amount, b.special_food_amount, b.rebate_discount, b.total_amount) == (
        BASE, D("0"), D("0"), BASE)
    assert b.status == "generated"                      # BR-018: not visible until published
    assert b.generated_at is not None and b.published_at is None


def test_base_amount_is_a_caller_supplied_policy_input(registered):
    """BR-MMS-036: rates belong to the institute, MMS only consumes them."""
    assert _bill(base_amount=D("4500.00")).total_amount == D("4500.00")


@pytest.mark.parametrize("status", ["approved", "served"])
def test_br030_approved_and_served_special_food_is_charged(registered, status):
    SpecialFoodFactory(status=status, requested_date=date(2026, 5, 10), cost=D("75.00"))
    b = _bill()
    assert (b.special_food_amount, b.total_amount) == (D("75.00"), BASE + D("75.00"))


@pytest.mark.parametrize("status", ["requested", "rejected"])
def test_br030_unapproved_special_food_is_not_charged(registered, status):
    SpecialFoodFactory(status=status, requested_date=date(2026, 5, 10))
    assert _bill().special_food_amount == D("0")


def test_br030_cancelled_special_food_is_not_charged(registered):
    """CHARACTERISATION. The spec leaves this open (ISS-MMS-015: does a later Cancelled
    reverse the charge?). The code excludes cancelled requests; if the institute rules
    otherwise, this is the test to change."""
    SpecialFoodFactory(cancelled=True, requested_date=date(2026, 5, 10))
    assert _bill().special_food_amount == D("0")


def test_special_food_charges_accumulate(registered):
    for cost in ("50.00", "60.00", "70.25"):
        SpecialFoodFactory(approved=True, requested_date=date(2026, 5, 10), cost=D(cost))
    assert _bill().special_food_amount == D("180.25")


@pytest.mark.parametrize("requested", [date(2026, 5, 1), date(2026, 5, 31)])
def test_br016_special_food_on_the_first_and_last_day_of_the_month_is_in(registered, requested):
    SpecialFoodFactory(approved=True, requested_date=requested)
    assert _bill().special_food_amount == D("50.00")


@pytest.mark.parametrize("requested", [date(2026, 4, 30), date(2026, 6, 1)])
def test_br016_special_food_in_a_neighbouring_month_is_out(registered, requested):
    SpecialFoodFactory(approved=True, requested_date=requested)
    assert _bill().special_food_amount == D("0")


def test_another_students_special_food_never_leaks_into_my_bill(registered):
    SpecialFoodFactory(user_id=OTHER_STUDENT_ID, approved=True, requested_date=date(2026, 5, 10))
    assert _bill().special_food_amount == D("0")


# ---- BR-MMS-019: rebates ------------------------------------------------------
def test_br019_an_approved_rebate_deducts_days_times_rate(registered):
    RebateFactory(approved=True, start_date=date(2026, 5, 10), end_date=date(2026, 5, 14),
                  duration_days=5)
    b = _bill(per_day_rebate_rate=RATE)
    assert (b.rebate_discount, b.total_amount) == (D("500.00"), BASE - D("500.00"))


@pytest.mark.parametrize("kind", ["submitted", "rejected"])
def test_br019_pending_and_rejected_rebates_do_not_adjust_the_bill(registered, kind):
    RebateFactory(status=kind, start_date=date(2026, 5, 10), end_date=date(2026, 5, 14),
                  duration_days=5)
    assert _bill().rebate_discount == D("0")


def test_br019_rebates_add_up(registered):
    RebateFactory(approved=True, start_date=date(2026, 5, 5), end_date=date(2026, 5, 7),
                  duration_days=3)
    RebateFactory(approved=True, start_date=date(2026, 5, 20), end_date=date(2026, 5, 23),
                  duration_days=4)
    assert _bill(per_day_rebate_rate=RATE).rebate_discount == D("700.00")


def test_a_rebate_wholly_in_another_month_is_ignored(registered):
    RebateFactory(approved=True, start_date=date(2026, 6, 10), end_date=date(2026, 6, 14),
                  duration_days=5)
    assert _bill().rebate_discount == D("0")


def test_a_modified_rebate_bills_on_its_approved_dates(registered):
    """BR-025: approved dates are the dates used for billing adjustment."""
    r = RebateFactory(start_date=date(2026, 5, 10), end_date=date(2026, 5, 12), duration_days=3)
    from modules.mms.tests.helpers import caretaker as ct
    svc.review_rebate_request(actor=ct(), rebate_id=r.pk, action="approve",
                              modified_start_date=date(2026, 5, 10),
                              modified_end_date=date(2026, 5, 16))
    assert _bill(per_day_rebate_rate=RATE).rebate_discount == D("700.00")


def test_the_bill_never_goes_negative(registered):
    RebateFactory(approved=True, start_date=date(2026, 5, 1), end_date=date(2026, 5, 31),
                  duration_days=31)
    b = _bill(per_day_rebate_rate=D("1000.00"))
    assert b.total_amount == D("0.00")
    assert b.rebate_discount == D("31000.00")            # the deduction is still recorded in full


def test_special_food_and_rebate_combine(registered):
    SpecialFoodFactory(approved=True, requested_date=date(2026, 5, 3), cost=D("200.00"))
    RebateFactory(approved=True, start_date=date(2026, 5, 10), end_date=date(2026, 5, 12),
                  duration_days=3)
    assert _bill(per_day_rebate_rate=RATE).total_amount == BASE + D("200.00") - D("300.00")


# ---- month arithmetic ---------------------------------------------------------
@pytest.mark.parametrize(("given", "stored"), [
    (date(2026, 5, 1), date(2026, 5, 1)),
    (date(2026, 5, 17), date(2026, 5, 1)),        # any day in the month names the month
    (date(2026, 12, 31), date(2026, 12, 1)),
])
def test_billing_month_is_normalised_to_the_first(registered, given, stored):
    assert _bill(month=given).billing_month == stored


def test_december_rolls_into_january_without_error(registered):
    SpecialFoodFactory(approved=True, requested_date=date(2026, 12, 31))
    SpecialFoodFactory(approved=True, requested_date=date(2027, 1, 1))
    assert _bill(month=date(2026, 12, 1)).special_food_amount == D("50.00")


def test_a_leap_february_includes_the_29th(registered):
    SpecialFoodFactory(approved=True, requested_date=date(2028, 2, 29))
    SpecialFoodFactory(approved=True, requested_date=date(2028, 3, 1))
    assert _bill(month=date(2028, 2, 1)).special_food_amount == D("50.00")


# ---- idempotence --------------------------------------------------------------
def test_regenerating_a_month_updates_rather_than_duplicates(registered):
    _bill()
    SpecialFoodFactory(approved=True, requested_date=date(2026, 5, 10))
    again = _bill()
    assert MessBill.objects.filter(user_id=STUDENT_ID, billing_month=MAY).count() == 1
    assert again.special_food_amount == D("50.00")


def test_each_month_gets_its_own_bill(registered):
    _bill(month=date(2026, 4, 1))
    _bill(month=MAY)
    assert MessBill.objects.filter(user_id=STUDENT_ID).count() == 2


# ---- UC-010: finalize and publish --------------------------------------------
def test_br018_caretaker_publishes_a_generated_bill(sent):
    b = BillFactory(total_amount=D("2850.00"))
    out = svc.finalize_and_publish_bill(actor=caretaker(), bill_id=b.pk)
    assert (out.status, out.published_by_user_id) == ("published", CARETAKER_ID)
    assert out.published_at is not None
    [n] = sent("bill_published")
    assert (n.recipient_user_id, "April 2026" in n.message, "2850.00" in n.message) == (
        STUDENT_ID, True, True)


@pytest.mark.parametrize("who", [student, warden, admin])
def test_br018_only_the_caretaker_publishes(who, sent):
    b = BillFactory()
    with pytest.raises(PermissionDeniedError):
        svc.finalize_and_publish_bill(actor=who(), bill_id=b.pk)
    b.refresh_from_db()
    assert b.status == "generated"
    assert sent() == []


def test_bw16_generated_to_published_end_to_end(registered):
    b = _bill()
    assert b.status == "generated"
    out = svc.finalize_and_publish_bill(actor=caretaker(), bill_id=b.pk)
    assert out.status == "published"


# ---- UC-011: viewing ----------------------------------------------------------
def test_br040_a_student_sees_only_their_own_bills():
    BillFactory(user_id=STUDENT_ID)
    BillFactory(user_id=OTHER_STUDENT_ID)
    assert [b.user_id for b in svc.view_monthly_bills(actor=student())] == [STUDENT_ID]


def test_the_caretaker_sees_every_bill():
    BillFactory(user_id=STUDENT_ID)
    BillFactory(user_id=OTHER_STUDENT_ID)
    assert len(svc.view_monthly_bills(actor=caretaker())) == 2


@pytest.mark.parametrize("who", [warden, admin])
def test_br005_the_warden_and_admin_cannot_view_bills(who):
    BillFactory()
    with pytest.raises(PermissionDeniedError):
        svc.view_monthly_bills(actor=who())
