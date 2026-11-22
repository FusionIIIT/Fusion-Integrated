"""`contracts.py` is the only door other modules may use (ADR-0010). Plural, read-only."""
from decimal import Decimal

import pytest

from modules.mms import contracts
from modules.mms.tests.factories import BillFactory, RegistrationFactory

pytestmark = pytest.mark.django_db
D = Decimal


# ---- get_student_mess_statuses -----------------------------------------------
def test_empty_input_is_an_empty_answer_without_touching_the_database(django_assert_num_queries):
    with django_assert_num_queries(0):
        assert contracts.get_student_mess_statuses([]) == {}


def test_every_requested_id_gets_an_answer_even_if_unknown():
    out = contracts.get_student_mess_statuses([1, 2, 3])
    assert set(out) == {1, 2, 3}
    assert not any(s.is_registered for s in out.values())


def test_an_approved_registration_means_registered_and_names_the_registration():
    reg = RegistrationFactory(user_id=1, approved=True)
    s = contracts.get_student_mess_statuses([1])[1]
    assert (s.user_id, s.is_registered, s.active_registration_id) == (1, True, reg.pk)


@pytest.mark.parametrize("status", ["submitted", "rejected", "deregistered"])
def test_only_approved_counts_as_registered(status):
    RegistrationFactory(user_id=1, status=status)
    s = contracts.get_student_mess_statuses([1])[1]
    assert (s.is_registered, s.active_registration_id) == (False, None)


def test_none_and_duplicate_ids_are_tolerated_and_numeric_strings_coerced():
    RegistrationFactory(user_id=7, approved=True)
    out = contracts.get_student_mess_statuses([7, 7, None, "7"])
    assert set(out) == {7} and out[7].is_registered


def test_statuses_cost_one_query_regardless_of_how_many_students(django_assert_num_queries):
    for uid in range(1, 21):
        RegistrationFactory(user_id=uid, approved=True)
    with django_assert_num_queries(1):
        out = contracts.get_student_mess_statuses(range(1, 21))
    assert all(s.is_registered for s in out.values())


def test_the_dto_is_immutable():
    s = contracts.get_student_mess_statuses([1])[1]
    with pytest.raises(AttributeError):
        s.is_registered = True


# ---- get_student_mess_bills ---------------------------------------------------
def test_empty_bill_input_is_empty():
    assert contracts.get_student_mess_bills([]) == {}


def test_a_student_with_no_bills_owes_zero():
    s = contracts.get_student_mess_bills([1])[1]
    assert (s.total_billed, s.total_outstanding) == (D("0.00"), D("0.00"))


def test_only_published_bills_are_visible_to_other_modules():
    """BR-018: a bill the caretaker has not finalised must not leak outwards."""
    BillFactory(user_id=1, status="draft", total_amount=D("100"), billing_month="2026-02-01")
    BillFactory(user_id=1, status="generated", total_amount=D("200"), billing_month="2026-03-01")
    BillFactory(user_id=1, published=True, total_amount=D("2850.50"), billing_month="2026-04-01")
    s = contracts.get_student_mess_bills([1])[1]
    assert s.total_billed == D("2850.50")


def test_published_bills_sum_across_months():
    BillFactory(user_id=1, published=True, total_amount=D("1000.10"), billing_month="2026-03-01")
    BillFactory(user_id=1, published=True, total_amount=D("2000.20"), billing_month="2026-04-01")
    assert contracts.get_student_mess_bills([1])[1].total_billed == D("3000.30")


def test_students_never_see_each_others_totals():
    BillFactory(user_id=1, published=True, total_amount=D("10"))
    BillFactory(user_id=2, published=True, total_amount=D("20"))
    out = contracts.get_student_mess_bills([1, 2])
    assert (out[1].total_billed, out[2].total_billed) == (D("10"), D("20"))


def test_outstanding_equals_billed_because_mms_does_not_collect_payment():
    """BR-040 / PS 3.3.3: payment is outside MMS, so nothing is ever netted off."""
    BillFactory(user_id=1, published=True, total_amount=D("500"))
    s = contracts.get_student_mess_bills([1])[1]
    assert s.total_outstanding == s.total_billed
