from datetime import date, time
from decimal import Decimal

import pytest

from modules.phc.domain.inventory import is_low_stock, stock_after
from modules.phc.domain.reimbursements import (
    CLAIM_APPROVED_PAYMENT,
    CLAIM_PENDING_ACCOUNTS,
    CLAIM_PENDING_PHC,
    CLAIM_PENDING_SANCTION,
    CLAIM_REIMBURSED,
    CLAIM_REJECTED,
    CLAIM_TRANSITIONS,
    claim_transition,
    validate_claim_amount,
    validate_submission_date,
)
from modules.phc.domain.requisitions import REQUISITION_TRANSITIONS, requisition_transition
from modules.phc.domain.schedules import weekly_range


# PHC-BR-04; PHC-BR-05; PHC-BR-06; PHC-UC-04; CFR-PHC-003; AFR-PHC-013; AFR-PHC-014; AFR-PHC-015; AFR-PHC-016.
def test_phc_br_06_accepts_inclusive_thirtieth_calendar_day():
    validate_submission_date(date(2026, 1, 1), date(2026, 1, 31), 30)


@pytest.mark.parametrize("expense,submitted", [
    (date(2026, 1, 1), date(2026, 2, 1)),
    (date(2026, 2, 1), date(2026, 1, 31)),
])
def test_phc_br_06_refuses_late_or_future_expense(expense, submitted):
    with pytest.raises(ValueError):
        validate_submission_date(expense, submitted, 30)


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-0.01"), Decimal("NaN")])
def test_phc_br_04_reimbursement_amount_must_be_positive(amount):
    with pytest.raises(ValueError):
        validate_claim_amount(amount)


# PHC-BR-08; PHC-BR-14; CFR-PHC-004; AFR-PHC-017; AFR-PHC-018; AFR-PHC-019; AFR-PHC-020; AFR-PHC-021; AFR-PHC-038.
def test_phc_br_08_and_phc_br_14_claim_table_allows_only_declared_transitions():
    expected = {
        (CLAIM_PENDING_PHC, "review", "Compounder"): CLAIM_PENDING_ACCOUNTS,
        (CLAIM_PENDING_ACCOUNTS, "verify", "Accounts Admin"): CLAIM_PENDING_SANCTION,
        (CLAIM_PENDING_SANCTION, "approve", "Registrar"): CLAIM_APPROVED_PAYMENT,
        (CLAIM_PENDING_SANCTION, "reject", "Registrar"): CLAIM_REJECTED,
        (CLAIM_APPROVED_PAYMENT, "pay", "Accounts Admin"): CLAIM_REIMBURSED,
    }
    assert {(state, event, role): claim_transition(state, event, role)
            for state, event, role, _ in CLAIM_TRANSITIONS} == expected
    for state, event, role, _ in CLAIM_TRANSITIONS:
        with pytest.raises(PermissionError):
            claim_transition(state, event, "student")
        with pytest.raises(LookupError):
            claim_transition(state, "reopen", role)


# PHC-BR-07; PHC-UC-09; CFR-PHC-006; AFR-PHC-024; AFR-PHC-025.
def test_phc_br_07_stock_stays_nonnegative_and_alert_uses_strict_threshold():
    assert stock_after(5, -4) == 1
    assert stock_after(5, -5) == 0
    with pytest.raises(ValueError):
        stock_after(5, 0)
    with pytest.raises(ValueError):
        stock_after(5, -6)
    assert is_low_stock(9, 10)
    assert not is_low_stock(10, 10)


def test_phc_uc_22_schedule_uses_week_minutes_and_rejects_invalid_times():
    assert weekly_range(0, time(9), time(10, 30)) == (540, 630)
    for start, end in ((time(10), time(10)), (time(11), time(10)),
                       (time(9, 0, 1), time(10))):
        with pytest.raises(ValueError):
            weekly_range(0, start, end)
    with pytest.raises(ValueError):
        weekly_range(7, time(9), time(10))


# PHC-BR-10; PHC-BR-11; PHC-UC-10; PHC-UC-14; PHC-UC-16; CFR-PHC-007; AFR-PHC-027; AFR-PHC-028; AFR-PHC-029; AFR-PHC-030; AFR-PHC-031.
def test_phc_br_10_and_phc_br_11_requisition_table_rejects_unlisted_paths():
    for state, event, role, target in REQUISITION_TRANSITIONS:
        assert requisition_transition(state, event, role) == target
        with pytest.raises(PermissionError):
            requisition_transition(state, event, "student")
        with pytest.raises(LookupError):
            requisition_transition(state, "unlisted_event", role)
