from decimal import Decimal

import pytest

from modules.elm.models import LeaveBalance, LeaveLedgerEntry
from modules.elm.services.balances import (
    LeaveBalanceError,
    convert_vl_balance_to_el,
    post_balance_entry,
)

pytestmark = pytest.mark.django_db


def make_balance(user_id, leave_type, *, entitlement="0", accrued="0", used="0"):
    return LeaveBalance.objects.create(
        user_id=user_id,
        leave_year=2026,
        leave_type=leave_type,
        annual_entitlement=Decimal(entitlement),
        accrued=Decimal(accrued),
        used=Decimal(used),
    )


def test_credit_updates_balance_and_creates_ledger_entry():
    balance = make_balance(101, "CL", entitlement="8")

    entry = post_balance_entry(
        balance_id=balance.pk,
        entry_type="credit",
        amount="2.5",
        reference_key="test-credit-1",
    )

    balance.refresh_from_db()
    assert balance.accrued == Decimal("2.50")
    assert entry.entry_type == "credit"
    assert entry.amount == Decimal("2.50")
    assert LeaveLedgerEntry.objects.filter(balance=balance).count() == 1


def test_debit_updates_used_balance():
    balance = make_balance(102, "EL", entitlement="10")

    post_balance_entry(
        balance_id=balance.pk,
        entry_type="debit",
        amount="3.5",
        reference_key="test-debit-1",
    )

    balance.refresh_from_db()
    assert balance.used == Decimal("3.50")
    assert balance.available_balance == Decimal("6.50")


def test_debit_rejects_insufficient_balance_without_ledger_entry():
    balance = make_balance(103, "CL", entitlement="2")

    with pytest.raises(LeaveBalanceError, match="Insufficient"):
        post_balance_entry(
            balance_id=balance.pk,
            entry_type="debit",
            amount="3",
            reference_key="test-debit-too-large",
        )

    balance.refresh_from_db()
    assert balance.used == Decimal("0")
    assert not LeaveLedgerEntry.objects.filter(balance=balance).exists()


def test_zero_amount_is_rejected():
    balance = make_balance(104, "RH", entitlement="2")

    with pytest.raises(LeaveBalanceError, match="greater than zero"):
        post_balance_entry(
            balance_id=balance.pk,
            entry_type="credit",
            amount="0",
        )

    assert not LeaveLedgerEntry.objects.filter(balance=balance).exists()


def test_vl_to_el_conversion_credits_half_unused_vl():
    vl = make_balance(105, "VL", entitlement="15", used="3")
    el = make_balance(105, "EL", entitlement="30")

    entry = convert_vl_balance_to_el(
        vl_balance_id=vl.pk,
        el_balance_id=el.pk,
        reference_key="vl-to-el:2026:user:105",
    )

    vl.refresh_from_db()
    el.refresh_from_db()

    assert vl.available_balance == Decimal("0")
    assert el.accrued == Decimal("6.00")
    assert entry.amount == Decimal("6.00")
    assert LeaveLedgerEntry.objects.filter(
        balance=vl, entry_type="conversion"
    ).count() == 1
    assert LeaveLedgerEntry.objects.filter(
        balance=el, entry_type="conversion"
    ).count() == 1


def test_repeated_vl_to_el_conversion_does_not_credit_twice():
    vl = make_balance(106, "VL", entitlement="10")
    el = make_balance(106, "EL", entitlement="30")
    reference = "vl-to-el:2026:user:106"

    first = convert_vl_balance_to_el(
        vl_balance_id=vl.pk,
        el_balance_id=el.pk,
        reference_key=reference,
    )
    second = convert_vl_balance_to_el(
        vl_balance_id=vl.pk,
        el_balance_id=el.pk,
        reference_key=reference,
    )

    el.refresh_from_db()
    assert first.pk == second.pk
    assert el.accrued == Decimal("5.00")
    assert LeaveLedgerEntry.objects.filter(
        balance=el, entry_type="conversion", reference_key=reference
    ).count() == 1


def test_ledger_failure_rolls_back_balance_update(monkeypatch):
    balance = make_balance(107, "CL", entitlement="8")

    def fail_ledger_create(*args, **kwargs):
        raise RuntimeError("Simulated ledger failure")

    monkeypatch.setattr(
        LeaveLedgerEntry.objects,
        "create",
        fail_ledger_create,
    )

    with pytest.raises(RuntimeError, match="Simulated ledger failure"):
        post_balance_entry(
            balance_id=balance.pk,
            entry_type="credit",
            amount="2",
            reference_key="test-rollback-1",
        )

    balance.refresh_from_db()
    assert balance.accrued == Decimal("0")
    assert not LeaveLedgerEntry.objects.filter(balance=balance).exists()

def test_repeated_reference_does_not_double_credit():
    balance = make_balance(108, "CL", entitlement="8")

    first = post_balance_entry(
        balance_id=balance.pk,
        entry_type="credit",
        amount="2",
        reference_key="credit-once-108",
    )
    second = post_balance_entry(
        balance_id=balance.pk,
        entry_type="credit",
        amount="2",
        reference_key="credit-once-108",
    )

    balance.refresh_from_db()
    assert first.pk == second.pk
    assert balance.accrued == Decimal("2")
    assert LeaveLedgerEntry.objects.filter(
        balance=balance,
        reference_key="credit-once-108",
    ).count() == 1


def test_reference_reuse_with_different_amount_is_rejected():
    balance = make_balance(109, "CL", entitlement="8")

    post_balance_entry(
        balance_id=balance.pk,
        entry_type="credit",
        amount="2",
        reference_key="credit-conflict-109",
    )

    with pytest.raises(LeaveBalanceError, match="different transaction"):
        post_balance_entry(
            balance_id=balance.pk,
            entry_type="credit",
            amount="3",
            reference_key="credit-conflict-109",
        )

    balance.refresh_from_db()
    assert balance.accrued == Decimal("2")
