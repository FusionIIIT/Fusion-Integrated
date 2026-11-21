"""Unit tests for SPACS business rules (BR-SPACS-001 through BR-SPACS-023)."""

from datetime import date, datetime, timedelta
import pytest
from modules.spacs.domain import rules
from modules.spacs.domain.errors import (
    CompletenessError,
    DocumentReuseError,
    DuplicateApplicationError,
    EligibilityError,
    RenewalEligibilityError,
    UnauthorizedActionError,
)


def test_br_001_eligibility():
    # Pass
    rules.validate_eligibility(student_cpi=8.5, student_family_income=300000, min_cpi=7.0, max_family_income=500000)

    # CPI failure
    with pytest.raises(EligibilityError, match="below the required minimum"):
        rules.validate_eligibility(student_cpi=6.5, student_family_income=300000, min_cpi=7.0)

    # Income failure
    with pytest.raises(EligibilityError, match="exceeds maximum threshold"):
        rules.validate_eligibility(student_cpi=8.5, student_family_income=600000, min_cpi=7.0, max_family_income=500000)


def test_br_002_duplicate_prevention():
    # Active application exists
    with pytest.raises(DuplicateApplicationError):
        rules.check_no_duplicate(["submitted"])

    # Permitted if previous application was withdrawn or rejected
    rules.check_no_duplicate(["withdrawn"])
    rules.check_no_duplicate(["rejected"])


def test_br_003_document_reuse():
    today = date.today()
    # Valid reuse
    rules.validate_document_reuse(
        doc_user_id=101,
        applicant_user_id=101,
        doc_type="income_cert",
        required_doc_type="income_cert",
        doc_valid_until=today + timedelta(days=30),
        reference_date=today,
    )

    # Other student's document
    with pytest.raises(DocumentReuseError, match="belonging to another user"):
        rules.validate_document_reuse(
            doc_user_id=999,
            applicant_user_id=101,
            doc_type="income_cert",
            required_doc_type="income_cert",
        )

    # Expired document
    with pytest.raises(DocumentReuseError, match="expired"):
        rules.validate_document_reuse(
            doc_user_id=101,
            applicant_user_id=101,
            doc_type="income_cert",
            required_doc_type="income_cert",
            doc_valid_until=today - timedelta(days=1),
            reference_date=today,
        )


def test_br_004_completeness():
    # Complete
    rules.validate_completeness(
        application_data={"name": "Alice", "bank_account": "12345"},
        mandatory_fields=["name", "bank_account"],
        uploaded_doc_types=["income_cert", "grade_sheet"],
        required_doc_types=["income_cert"],
    )

    # Missing mandatory field
    with pytest.raises(CompletenessError, match="field"):
        rules.validate_completeness(
            application_data={"name": "Alice"},
            mandatory_fields=["name", "bank_account"],
            uploaded_doc_types=["income_cert"],
            required_doc_types=["income_cert"],
        )

    # Missing document
    with pytest.raises(CompletenessError, match="document"):
        rules.validate_completeness(
            application_data={"name": "Alice", "bank_account": "12345"},
            mandatory_fields=["name", "bank_account"],
            uploaded_doc_types=[],
            required_doc_types=["income_cert"],
        )


def test_br_009_and_010_withdrawal_and_ownership():
    # Cannot withdraw after final approval
    with pytest.raises(UnauthorizedActionError, match="terminal state"):
        rules.validate_can_withdraw("approved")

    # Non-owner cannot withdraw
    with pytest.raises(UnauthorizedActionError, match="not the owner"):
        rules.assert_ownership(applicant_user_id=100, acting_user_id=200)


def test_br_013_sla_escalation():
    now = datetime(2026, 11, 4, 12, 0)
    created_recent = now - timedelta(hours=20)
    created_old = now - timedelta(hours=50)

    assert rules.is_sla_breached(created_recent, sla_hours=48, now=now) is False
    assert rules.is_sla_breached(created_old, sla_hours=48, now=now) is True
