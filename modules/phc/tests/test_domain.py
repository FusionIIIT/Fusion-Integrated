"""Domain rules with no database: every branch of every rule."""
from datetime import date
from decimal import Decimal

import pytest

from modules.phc.domain import pdf, reports, rules


# PHC-BR-04
def test_employees_may_claim_phc_br_04():
    rules.require_employee("faculty")
    rules.require_employee("staff")


# PHC-BR-04
@pytest.mark.parametrize("kind", ["student", "", None, "recruiter"])
def test_everyone_else_is_refused_phc_br_04(kind):
    with pytest.raises(rules.RuleViolation) as exc:
        rules.require_employee(kind)
    assert exc.value.code == "not_an_employee"


WINDOW_INCLUSIVE = rules.SubmissionWindow(days=30, includes_last_day=True)
WINDOW_EXCLUSIVE = rules.SubmissionWindow(days=30, includes_last_day=False)


# PHC-BR-06
def test_same_day_and_last_day_are_inside_an_inclusive_window_phc_br_06():
    rules.check_submission_window(date(2026, 11, 1), date(2026, 11, 1), WINDOW_INCLUSIVE)
    rules.check_submission_window(date(2026, 11, 1), date(2026, 12, 1), WINDOW_INCLUSIVE)


# PHC-BR-06
def test_last_day_is_outside_an_exclusive_window_phc_br_06():
    rules.check_submission_window(date(2026, 11, 1), date(2026, 11, 30), WINDOW_EXCLUSIVE)
    with pytest.raises(rules.RuleViolation) as exc:
        rules.check_submission_window(date(2026, 11, 1), date(2026, 12, 1), WINDOW_EXCLUSIVE)
    assert exc.value.code == "outside_submission_window"


# PHC-BR-06
def test_a_day_past_the_window_is_refused_phc_br_06():
    with pytest.raises(rules.RuleViolation) as exc:
        rules.check_submission_window(date(2026, 11, 1), date(2026, 12, 2), WINDOW_INCLUSIVE)
    assert exc.value.code == "outside_submission_window"


# PHC-BR-06
def test_a_future_expense_is_refused_phc_br_06():
    with pytest.raises(rules.RuleViolation) as exc:
        rules.check_submission_window(date(2026, 12, 2), date(2026, 12, 1), WINDOW_INCLUSIVE)
    assert exc.value.code == "expense_in_future"


# PHC-BR-07
@pytest.mark.parametrize(("level", "threshold", "low"), [
    ("49", "50", True), ("50", "50", False), ("51", "50", False), ("0", "0", False),
])
def test_low_stock_is_strictly_below_threshold_phc_br_07(level, threshold, low):
    assert rules.is_low_stock(Decimal(level), Decimal(threshold)) is low


# AFR-PHC-024
def test_stock_change_adds_and_deducts_afr_phc_024():
    assert rules.apply_stock_change(Decimal("10"), Decimal("5")) == Decimal("15")
    assert rules.apply_stock_change(Decimal("10"), Decimal("-10")) == Decimal("0")


def test_stock_cannot_go_negative_or_change_by_zero():
    with pytest.raises(rules.RuleViolation) as exc:
        rules.apply_stock_change(Decimal("10"), Decimal("-11"))
    assert exc.value.code == "insufficient_stock"
    with pytest.raises(rules.RuleViolation) as exc:
        rules.apply_stock_change(Decimal("10"), Decimal("0"))
    assert exc.value.code == "zero_adjustment"


# PHC-UC-13
def test_report_request_validation_phc_uc_13():
    req = reports.validate_request("utilization", date(2026, 1, 1), date(2026, 1, 31))
    assert req.category == "utilization"
    with pytest.raises(reports.ReportParameterError):
        reports.validate_request("salaries", date(2026, 1, 1), date(2026, 1, 31))
    with pytest.raises(reports.ReportParameterError):
        reports.validate_request("inventory", date(2026, 2, 1), date(2026, 1, 31))


# PHC-BR-12
def test_small_counts_are_suppressed_phc_br_12():
    assert reports.suppress(0) == 0
    assert reports.suppress(1) == "<5"
    assert reports.suppress(4) == "<5"
    assert reports.suppress(5) == 5
    assert reports.anonymised_counts(["staff"] * 6 + ["student"]) == {"staff": 6,
                                                                      "student": "<5"}


# AFR-PHC-011
def test_pdf_is_well_formed_and_paginates_afr_phc_011():
    body = pdf.render([f"line {i} (with parens)" for i in range(120)])
    assert body.startswith(b"%PDF-1.4")
    assert body.rstrip().endswith(b"%%EOF")
    assert b"/Count 3" in body
    assert b"\\(with parens\\)" in body


def test_empty_pdf_still_has_one_page():
    assert b"/Count 1" in pdf.render([])
