"""Where the generated code departs from the specification.

Each test below states what the SPEC requires (citing the clause) and is expected to FAIL
against the current code. They are `xfail(strict=True)`:

  * the suite stays green today and the gap is visible in the report (`-rxX`);
  * the moment someone fixes the gap the test XPASSes, strict mode turns that into a
    failure, and the fixer deletes the marker — the test then guards the fix forever.

Do not loosen a test to make it pass. Either fix the code or, if the spec is what is wrong,
change the spec reference and say why in the commit.
"""
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.mms import contracts
from modules.mms.domain.state_machine import RuleViolation
from modules.mms.models import MessBill, MessRegistration, MessRoleAssignment
from modules.mms.services import operations as svc
from modules.mms.tests import factories as f
from modules.mms.tests.helpers import (
    STUDENT_ID,
    caretaker,
    student,
)
from modules.mms.tests.helpers import (
    days_from_today as day,
)

pytestmark = pytest.mark.django_db
D = Decimal


def gap(n, why):
    return pytest.mark.xfail(strict=True, reason=f"GAP-{n}: {why}")


# =============================================================================
# Notifications the spec requires and the code never sends  (BR-MMS-035)
# =============================================================================
@gap(1, "BR-MMS-015 / UC-008 step 6: menu updates must notify Students")
def test_publishing_a_menu_notifies_students(sent):
    f.RegistrationFactory(approved=True)
    svc.publish_or_update_menu(actor=caretaker(), day_of_week="monday", meal_type="lunch",
                               items=["Dal"])
    assert sent(user_id=STUDENT_ID)


@gap(2, "BR-MMS-035 / UC-016 step 4: survey creation must notify registered Students")
def test_creating_a_vacation_survey_notifies_registered_students(sent):
    f.RegistrationFactory(approved=True)
    svc.create_vacation_survey(
        actor=caretaker(), title="Winter", vacation_start_date=date(2026, 12, 20),
        vacation_end_date=date(2027, 1, 5), response_deadline=timezone.now())
    assert sent(user_id=STUDENT_ID)


@gap(3, "UC-022 step 4 / PS 3.3.8: new announcements must notify Students")
def test_publishing_an_announcement_notifies_students(sent):
    f.RegistrationFactory(approved=True)
    svc.publish_announcement(actor=caretaker(), title="T", content="C")
    assert sent(user_id=STUDENT_ID)


@gap(4, "UC-021 step 5: Served/Cancelled must notify the requesting Student")
@pytest.mark.parametrize("status", ["served", "cancelled"])
def test_a_fulfilment_update_notifies_the_student(status, sent):
    r = f.SpecialFoodFactory(approved=True)
    svc.update_special_food_fulfillment(actor=caretaker(), request_id=r.pk, status=status)
    assert sent(user_id=STUDENT_ID)


# =============================================================================
# Validation the spec requires
# =============================================================================
@gap(5, "BR-MMS-024: a rebate request MUST specify a reason")
@pytest.mark.parametrize("blank", ["", "   "])
def test_a_rebate_without_a_reason_is_refused(blank):
    with pytest.raises(Exception) as e:
        svc.submit_rebate_request(actor=student(), start_date=day(5), end_date=day(8),
                                  reason=blank)
    assert isinstance(e.value, (DomainError, RuleViolation))


@gap(6, "UC-017 / BW-MMS-08: a response is recorded 'before the deadline' — late ones refused")
def test_a_response_after_the_deadline_is_refused():
    f.RegistrationFactory(approved=True)
    late = f.VacationSurveyFactory(
        response_deadline=timezone.now().replace(year=2026, month=5, day=12))
    with pytest.raises((ConflictError, RuleViolation)):
        svc.respond_to_vacation_survey(actor=student(), survey_id=late.pk, requires_food=True)


@gap(7, "BR-MMS-016 + BR-MMS-019: a bill deducts only the rebate days inside ITS calendar month")
def test_a_rebate_spanning_two_months_is_split_between_the_two_bills():
    f.RegistrationFactory(approved=True)
    f.RebateFactory(approved=True, start_date=date(2026, 1, 30), end_date=date(2026, 2, 3),
                    duration_days=5)                           # Jan 30,31 | Feb 1,2,3
    feb = next(iter(svc.generate_monthly_bills(billing_month=date(2026, 2, 1),
                                               per_day_rebate_rate=D("100.00"))))
    jan = next(iter(svc.generate_monthly_bills(billing_month=date(2026, 1, 1),
                                               per_day_rebate_rate=D("100.00"))))
    assert (jan.rebate_discount, feb.rebate_discount) == (D("200.00"), D("300.00"))


@gap(8, "BR-MMS-014: meal type is one of breakfast/lunch/dinner — special food included")
def test_special_food_rejects_an_unknown_meal_type():
    with pytest.raises((DomainError, RuleViolation)):
        svc.submit_special_food_request(actor=student(), requested_date=day(3),
                                        meal_type="midnight snack", food_details="x", reason="y")


@gap(9, "BR-MMS-023: a caretaker's date modification must not create an overlap")
def test_modified_rebate_dates_may_not_overlap_the_students_other_rebate():
    f.RebateFactory(approved=True, start_date=day(10), end_date=day(14), duration_days=5)
    pending = f.RebateFactory(start_date=day(5), end_date=day(8), duration_days=4)
    with pytest.raises((DomainError, RuleViolation)):
        svc.review_rebate_request(actor=caretaker(), rebate_id=pending.pk, action="approve",
                                  modified_end_date=day(12))


# =============================================================================
# Billing lifecycle  (BR-MMS-018, BW-MMS-16: Generated -> Published, one way)
# =============================================================================
@gap(10, "BR-MMS-018: only a Generated bill can be published — republishing must be refused")
def test_a_published_bill_cannot_be_published_again(sent):
    b = f.BillFactory(published=True)
    with pytest.raises(ConflictError):
        svc.finalize_and_publish_bill(actor=caretaker(), bill_id=b.pk)
    assert sent() == []                                         # no second "bill published" email


@gap(11, "BR-MMS-018: regenerating a month must not silently un-publish a bill students can see")
def test_regenerating_a_month_does_not_revert_a_published_bill():
    f.RegistrationFactory(approved=True)
    [bill] = svc.generate_monthly_bills(billing_month=date(2026, 5, 1))
    svc.finalize_and_publish_bill(actor=caretaker(), bill_id=bill.pk)
    svc.generate_monthly_bills(billing_month=date(2026, 5, 1))
    assert MessBill.objects.get(pk=bill.pk).status == "published"


# =============================================================================
# Data integrity
# =============================================================================
@gap(12, "UC-027 postcondition: activation records a VALID registration status")
def test_activation_leaves_the_registration_with_a_status_the_model_allows():
    dr = f.DeregistrationFactory(approved=True)
    svc.activate_approved_deregistration(deregistration_id=dr.pk)
    dr.registration.refresh_from_db()
    try:
        dr.registration.full_clean()
    except ValidationError as e:          # status 'deregistered' is not in STATUS_CHOICES
        pytest.fail(str(e))


@gap(13, "an unknown id is a 404 (NotFoundError), not an unhandled DoesNotExist (HTTP 500)")
@pytest.mark.parametrize("call", [
    lambda: svc.review_registration_request(actor=caretaker(), request_id=999_999, action="approve"),
    lambda: svc.review_rebate_request(actor=caretaker(), rebate_id=999_999, action="approve"),
    lambda: svc.finalize_and_publish_bill(actor=caretaker(), bill_id=999_999),
    lambda: svc.respond_to_vacation_survey(actor=student(), survey_id=999_999, requires_food=True),
], ids=["registration", "rebate", "bill", "survey"])
def test_unknown_ids_raise_not_found(call):
    with pytest.raises(NotFoundError):
        call()


@gap(14, "business-rule failures must reach HTTP clients as 4xx — core's handler only maps "
         "DomainError, so RuleViolation/InvalidTransition from a service would be a 500")
@pytest.mark.parametrize("call", [
    lambda: svc.submit_rebate_request(actor=student(), start_date=day(5), end_date=day(6),
                                      reason="medical"),
    lambda: svc.update_special_food_fulfillment(
        actor=caretaker(), request_id=f.SpecialFoodFactory().pk, status="served"),
], ids=["rule-violation", "invalid-transition"])
def test_service_failures_are_domain_errors_the_api_can_render(call):
    with pytest.raises(DomainError):
        call()


# ---- the database should be the backstop, not just the service ----------------
@gap(15, "BR-MMS-003: exactly one active Caretaker — nothing in the DB enforces it")
def test_the_database_refuses_two_active_caretakers():
    mk = {"role_name": "mess_caretaker", "start_date": day(0), "end_date": day(30),
          "is_active": True, "assigned_by_user_id": 1}
    MessRoleAssignment.objects.create(assigned_user_id=10, **mk)
    with pytest.raises(IntegrityError), transaction.atomic():
        MessRoleAssignment.objects.create(assigned_user_id=11, **mk)


@gap(16, "BR-MMS-004: exactly one active Warden — nothing in the DB enforces it")
def test_the_database_refuses_two_active_wardens():
    mk = {"role_name": "mess_warden", "start_date": day(0), "end_date": day(30),
          "is_active": True, "assigned_by_user_id": 1}
    MessRoleAssignment.objects.create(assigned_user_id=10, **mk)
    with pytest.raises(IntegrityError), transaction.atomic():
        MessRoleAssignment.objects.create(assigned_user_id=11, **mk)


@gap(17, "BR-MMS-009: submit-then-insert is check-then-act; two live registrations for one "
         "student need a partial unique index to be impossible under concurrency")
def test_the_database_refuses_two_live_registrations_for_one_student():
    f.RegistrationFactory(status="submitted")
    with pytest.raises(IntegrityError), transaction.atomic():
        MessRegistration.objects.create(user_id=STUDENT_ID, status="approved")


# =============================================================================
# Performance contract  (testing-strategy.md: query budgets are constant in row count)
# =============================================================================
@gap(18, "get_student_mess_bills issues one query per student (N+1); a plural contract "
         "exists precisely so callers can batch")
def test_bill_contract_query_count_is_constant_in_the_number_of_students(
        django_assert_max_num_queries):
    for uid in range(1, 11):
        f.BillFactory(user_id=uid, published=True)
    with django_assert_max_num_queries(2):
        contracts.get_student_mess_bills(range(1, 11))
