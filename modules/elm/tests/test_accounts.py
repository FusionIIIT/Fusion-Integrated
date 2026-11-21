"""Tests for transactional ELM leave-account operations."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.models import (
    LeaveAccountTransaction,
    LeaveApplication,
    LeaveBalance,
)
from modules.elm.services.accounts import post_transaction

pytestmark = pytest.mark.django_db

TODAY = date(2026, 10, 27)


@pytest.fixture
def balance():
    return LeaveBalance.objects.create(
        user_id=1001,
        leave_year=2026,
        category="EL",
        annual_entitlement=Decimal("30.00"),
    )


def make_application(*, user_id=1001, category="EL", status="approved"):
    return LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        start_date=TODAY,
        end_date=TODAY + timedelta(days=2),
        requested_days=Decimal("3.00"),
        purpose="Test application",
        status=status,
    )


def test_empty_account_has_zero_current_balance(balance):
    assert balance.current_balance == Decimal("0.00")


def test_grant_and_debit_update_the_ledger(balance):
    post_transaction(
        balance_id=balance.pk,
        delta="30.00",
        transaction_type="annual_grant",
        effective_date=TODAY,
        actor_user_id=9,
    )
    application = make_application()

    post_transaction(
        balance_id=balance.pk,
        application_id=application.pk,
        delta="-3.00",
        transaction_type="leave_debit",
        effective_date=TODAY,
        actor_user_id=9,
    )

    balance.refresh_from_db()
    assert balance.current_balance == Decimal("27.00")
    assert LeaveAccountTransaction.objects.count() == 2


def test_rejects_debit_that_would_make_balance_negative(balance):
    post_transaction(
        balance_id=balance.pk,
        delta="2.00",
        transaction_type="annual_grant",
        effective_date=TODAY,
    )
    application = make_application()

    with pytest.raises(ConflictError):
        post_transaction(
            balance_id=balance.pk,
            application_id=application.pk,
            delta="-3.00",
            transaction_type="leave_debit",
            effective_date=TODAY,
        )

    balance.refresh_from_db()
    assert balance.current_balance == Decimal("2.00")
    assert LeaveAccountTransaction.objects.count() == 1


def test_leave_debit_requires_an_approved_application(balance):
    application = make_application(status="awaiting_unit_head_review")

    with pytest.raises(ConflictError):
        post_transaction(
            balance_id=balance.pk,
            application_id=application.pk,
            delta="-1.00",
            transaction_type="leave_debit",
            effective_date=TODAY,
        )

    assert LeaveAccountTransaction.objects.count() == 0


def test_application_must_belong_to_same_employee_and_category(balance):
    application = make_application(user_id=2002)

    with pytest.raises(ConflictError):
        post_transaction(
            balance_id=balance.pk,
            application_id=application.pk,
            delta="-1.00",
            transaction_type="leave_debit",
            effective_date=TODAY,
        )


def test_leave_debit_requires_an_application(balance):
    with pytest.raises(ConflictError):
        post_transaction(
            balance_id=balance.pk,
            delta="-1.00",
            transaction_type="leave_debit",
            effective_date=TODAY,
        )


@pytest.mark.parametrize("amount", ["0", "NaN", "Infinity", "1.234"])
def test_rejects_zero_nonfinite_or_overprecise_amounts(balance, amount):
    with pytest.raises(ConflictError):
        post_transaction(
            balance_id=balance.pk,
            delta=amount,
            transaction_type="annual_grant",
            effective_date=TODAY,
        )


def test_transaction_sign_must_match_type(balance):
    with pytest.raises(ConflictError):
        post_transaction(
            balance_id=balance.pk,
            delta="-5.00",
            transaction_type="annual_grant",
            effective_date=TODAY,
        )


def test_manual_adjustment_requires_a_note(balance):
    with pytest.raises(ConflictError):
        post_transaction(
            balance_id=balance.pk,
            delta="1.00",
            transaction_type="manual_adjustment",
            effective_date=TODAY,
        )


def test_offline_sanction_requires_reference(balance):
    with pytest.raises(ConflictError):
        post_transaction(
            balance_id=balance.pk,
            delta="-1.00",
            transaction_type="offline_sanction",
            effective_date=TODAY,
        )


def test_missing_balance_is_rejected():
    with pytest.raises(NotFoundError) as error:
        post_transaction(
            balance_id=999999,
            delta="1.00",
            transaction_type="annual_grant",
            effective_date=TODAY,
        )

    assert "Leave balance not found" in str(error.value)
