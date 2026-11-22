"""The composite workflows (05_MMS_Workflow_Specifications), played end to end through the
real services — no factories for the steps under test, so a break between two services
(not just inside one) shows up here.

CW-MMS-01 registration · CW-MMS-02 deregistration · CW-MMS-03 rebate
CW-MMS-04 vacation    · CW-MMS-05 special food     · BW-MMS-16 billing
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.mms import contracts
from modules.mms.models import MessBill
from modules.mms.services import operations as svc
from modules.mms.tests.helpers import (
    OTHER_STUDENT_ID,
    STUDENT_ID,
    TODAY,
    caretaker,
    student,
)
from modules.mms.tests.helpers import (
    days_from_today as day,
)

pytestmark = pytest.mark.django_db
D = Decimal


def _register(uid=STUDENT_ID):
    """CW-MMS-01 steps 1-3."""
    svc.open_registration_window(actor=caretaker(), academic_year="2026-27", semester="Autumn",
                                 start_date=TODAY, end_date=day(14))
    r = svc.submit_registration_request(actor=student(uid))
    svc.review_registration_request(actor=caretaker(), request_id=r.pk, action="approve")
    return r


def test_cw01_to_cw02_register_then_deregister_then_leave_the_mess():
    reg = _register()
    assert contracts.get_student_mess_statuses([STUDENT_ID])[STUDENT_ID].is_registered

    dr = svc.submit_deregistration_request(actor=student(), reason="moving out")
    dr = svc.review_deregistration_request(actor=caretaker(), request_id=dr.pk, action="approve")
    # Approved but not yet in force: still registered, still billable, until UC-027 fires.
    assert contracts.get_student_mess_statuses([STUDENT_ID])[STUDENT_ID].is_registered
    assert dr.effective_date == day(1)

    svc.activate_approved_deregistration(deregistration_id=dr.pk)
    assert not contracts.get_student_mess_statuses([STUDENT_ID])[STUDENT_ID].is_registered
    assert svc.generate_monthly_bills(billing_month=date(2026, 6, 1)) == []
    reg.refresh_from_db()


def test_cw02_a_rejected_deregistration_leaves_the_student_registered_and_billed():
    _register()
    dr = svc.submit_deregistration_request(actor=student(), reason="x")
    svc.review_deregistration_request(actor=caretaker(), request_id=dr.pk, action="reject")
    assert contracts.get_student_mess_statuses([STUDENT_ID])[STUDENT_ID].is_registered
    assert len(svc.generate_monthly_bills(billing_month=date(2026, 6, 1))) == 1


def test_cw03_a_rebate_flows_through_to_the_published_bill():
    _register()
    rebate = svc.submit_rebate_request(actor=student(), start_date=date(2026, 5, 20),
                                       end_date=date(2026, 5, 24), reason="medical")
    svc.review_rebate_request(actor=caretaker(), rebate_id=rebate.pk, action="approve")

    [bill] = svc.generate_monthly_bills(billing_month=date(2026, 5, 1),
                                        per_day_rebate_rate=D("100.00"))
    assert bill.rebate_discount == D("500.00")
    published = svc.finalize_and_publish_bill(actor=caretaker(), bill_id=bill.pk)
    assert [b.total_amount for b in svc.view_monthly_bills(actor=student())] == [D("2500.00")]
    assert contracts.get_student_mess_bills([STUDENT_ID])[STUDENT_ID].total_billed == D("2500.00")
    assert published.status == "published"


def test_cw03_a_rejected_rebate_changes_nothing_on_the_bill():
    _register()
    rebate = svc.submit_rebate_request(actor=student(), start_date=date(2026, 5, 20),
                                       end_date=date(2026, 5, 24), reason="medical")
    svc.review_rebate_request(actor=caretaker(), rebate_id=rebate.pk, action="reject")
    [bill] = svc.generate_monthly_bills(billing_month=date(2026, 5, 1))
    assert bill.rebate_discount == D("0") and bill.total_amount == D("3000.00")


def test_cw03_overlap_is_checked_against_the_students_own_history_only():
    _register(STUDENT_ID)
    _register(OTHER_STUDENT_ID)
    args = {"start_date": day(5), "end_date": day(9), "reason": "medical"}
    svc.submit_rebate_request(actor=student(STUDENT_ID), **args)
    svc.submit_rebate_request(actor=student(OTHER_STUDENT_ID), **args)       # no clash


def test_cw04_vacation_yes_no_and_default_no_in_one_survey():
    third = 3003
    for uid in (STUDENT_ID, OTHER_STUDENT_ID, third):
        _register(uid)
    survey = svc.create_vacation_survey(
        actor=caretaker(), title="Winter", vacation_start_date=date(2026, 12, 20),
        vacation_end_date=date(2027, 1, 5), response_deadline=timezone.now() + timedelta(days=2))

    svc.respond_to_vacation_survey(actor=student(STUDENT_ID), survey_id=survey.pk,
                                   requires_food=True)
    svc.respond_to_vacation_survey(actor=student(OTHER_STUDENT_ID), survey_id=survey.pk,
                                   requires_food=False)
    assert svc.apply_default_vacation_responses(survey_id=survey.pk) == 1

    from modules.mms.models import VacationFoodResponse as R
    got = {r.user_id: (r.requires_food, r.is_default) for r in R.objects.filter(survey=survey)}
    assert got == {STUDENT_ID: (True, False), OTHER_STUDENT_ID: (False, False),
                   third: (False, True)}


def test_cw05_approved_then_served_request_is_billed_but_a_default_rejected_one_is_not():
    _register()
    served = svc.submit_special_food_request(
        actor=student(), requested_date=date(2026, 5, 20), meal_type="dinner",
        food_details="Khichdi", reason="fever", cost=D("80.00"))
    ignored = svc.submit_special_food_request(
        actor=student(), requested_date=date(2026, 5, 21), meal_type="lunch",
        food_details="Soup", reason="fever", cost=D("60.00"))
    svc.review_special_food_request(actor=caretaker(), request_id=served.pk, action="approve")
    svc.update_special_food_fulfillment(actor=caretaker(), request_id=served.pk, status="served")
    svc.default_reject_special_food_request(request_id=ignored.pk)

    [bill] = svc.generate_monthly_bills(billing_month=date(2026, 5, 1))
    assert bill.special_food_amount == D("80.00")
    assert bill.total_amount == D("3080.00")


def test_bw16_the_student_cannot_see_a_bill_until_the_caretaker_publishes_it():
    """BR-MMS-018 as a user would experience it. The ROW is visible through the selector
    (that is the caretaker's review queue) but the cross-module contract exposes nothing."""
    _register()
    [bill] = svc.generate_monthly_bills(billing_month=date(2026, 5, 1))
    assert contracts.get_student_mess_bills([STUDENT_ID])[STUDENT_ID].total_billed == D("0")
    svc.finalize_and_publish_bill(actor=caretaker(), bill_id=bill.pk)
    assert contracts.get_student_mess_bills([STUDENT_ID])[STUDENT_ID].total_billed == D("3000.00")
    assert MessBill.objects.filter(status="published").count() == 1
