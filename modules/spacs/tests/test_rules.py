"""Unit tests for SPACS business rules (BR-SPACS-001 through BR-SPACS-023)."""

from datetime import date, datetime, timedelta

import pytest

from modules.spacs.domain import rules
from modules.spacs.domain.errors import (
    CompletenessError,
    DocumentReuseError,
    DuplicateApplicationError,
    EligibilityError,
    UnauthorizedActionError,
)


def test_br_001_eligibility():
    # Pass
    rules.validate_eligibility(
        student_cpi=8.5, student_family_income=300000, min_cpi=7.0, max_family_income=500000
    )

    # CPI failure
    with pytest.raises(EligibilityError, match="below the required minimum"):
        rules.validate_eligibility(student_cpi=6.5, student_family_income=300000, min_cpi=7.0)

    # Income failure
    with pytest.raises(EligibilityError, match="exceeds maximum threshold"):
        rules.validate_eligibility(
            student_cpi=8.5, student_family_income=600000, min_cpi=7.0, max_family_income=500000
        )


def test_br_002_duplicate_prevention():
    # Active application exists
    with pytest.raises(DuplicateApplicationError):
        rules.check_no_duplicate(["submitted"])

    # Permitted if previous application was withdrawn or rejected
    rules.check_no_duplicate(["withdrawn"])
    rules.check_no_duplicate(["rejected"])


def test_br_003_document_reuse():
    today = date.today()
    # Valid reuse without expiry
    rules.validate_document_reuse(
        doc_user_id=101,
        applicant_user_id=101,
        doc_type="income_cert",
        required_doc_type="income_cert",
        doc_valid_until=None,
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


def test_br_001_eligibility_backlogs():
    with pytest.raises(EligibilityError, match="Active backlogs"):
        rules.validate_eligibility(
            student_cpi=8.5,
            student_family_income=300000,
            active_backlogs=2,
            max_backlogs=0,
        )


def test_br_003_document_reuse_mismatch():
    today = date.today()
    with pytest.raises(DocumentReuseError, match="does not match required type"):
        rules.validate_document_reuse(
            doc_user_id=101,
            applicant_user_id=101,
            doc_type="grade_sheet",
            required_doc_type="income_cert",
            doc_valid_until=today + timedelta(days=30),
            reference_date=today,
        )


def test_br_005_and_006_review_access_and_assistant_action():
    rules.check_application_review_access(["spacs_assistant"])
    rules.check_application_review_access(["spacs_convener"])
    with pytest.raises(UnauthorizedActionError, match="Access denied"):
        rules.check_application_review_access(["student"])

    rules.assert_assistant_action_permitted("verify")
    rules.assert_assistant_action_permitted("request_correction")
    with pytest.raises(UnauthorizedActionError, match="cannot perform final sanction"):
        rules.assert_assistant_action_permitted("approve")


def test_br_007_and_008_draft_and_notifications():
    merged = rules.preserve_draft_payload({"a": 1}, {"b": 2})
    assert merged == {"a": 1, "b": 2}

    assert rules.should_notify_event("submitted") is True
    assert rules.should_notify_event("random_unknown") is False


def test_br_009_and_010_withdrawal_and_ownership():
    # Cannot withdraw after final approval
    with pytest.raises(UnauthorizedActionError, match="terminal state"):
        rules.validate_can_withdraw("approved")

    # Non-withdrawable state
    with pytest.raises(UnauthorizedActionError, match="is not withdrawable"):
        rules.validate_can_withdraw("unknown_nonwithdrawable_state")

    # Convener review locked
    with pytest.raises(UnauthorizedActionError, match="withdrawal is locked"):
        rules.validate_can_withdraw("verified", convener_review_started=True)

    # Valid withdrawal
    rules.validate_can_withdraw("submitted")
    rules.validate_can_withdraw("under_verification")
    rules.validate_can_withdraw("verified", convener_review_started=False)

    # Non-owner cannot withdraw
    with pytest.raises(UnauthorizedActionError, match="not the owner"):
        rules.assert_ownership(applicant_user_id=100, acting_user_id=200)

    # Owner passes
    rules.assert_ownership(applicant_user_id=100, acting_user_id=100)


def test_br_011_can_modify():
    rules.validate_can_modify("draft")
    rules.validate_can_modify("correction_required")
    with pytest.raises(UnauthorizedActionError, match="Modification not permitted"):
        rules.validate_can_modify("submitted")


def test_br_012_download_access():
    # Owner
    rules.validate_download_access(applicant_user_id=10, acting_user_id=10, user_roles=["student"])
    # Staff
    rules.validate_download_access(
        applicant_user_id=10, acting_user_id=20, user_roles=["spacs_assistant"]
    )
    # Unauthorized
    with pytest.raises(UnauthorizedActionError, match="Unauthorized export"):
        rules.validate_download_access(
            applicant_user_id=10, acting_user_id=20, user_roles=["student"]
        )


def test_br_014_catalogue_publication_windows():
    now = datetime(2026, 11, 4, 12, 0)
    # Status not published
    with pytest.raises(EligibilityError, match="not active"):
        rules.validate_catalogue_published_and_open("draft", None, None, now)

    # Before window
    start = now + timedelta(days=1)
    with pytest.raises(EligibilityError, match="not yet opened"):
        rules.validate_catalogue_published_and_open("published", start, None, now)

    # After window
    end = now - timedelta(days=1)
    with pytest.raises(EligibilityError, match="closed"):
        rules.validate_catalogue_published_and_open("published", None, end, now)

    # Open
    rules.validate_catalogue_published_and_open(
        "published", now - timedelta(days=1), now + timedelta(days=1), now
    )


def test_br_015_publication_prerequisites():
    today = date.today()
    with pytest.raises(rules.AwardPolicyError, match="reference is mandatory"):
        rules.validate_catalogue_publication_prerequisites("", today)

    with pytest.raises(rules.AwardPolicyError, match="start date is mandatory"):
        rules.validate_catalogue_publication_prerequisites("REF-1", None)

    with pytest.raises(rules.AwardPolicyError, match="cannot precede"):
        rules.validate_catalogue_publication_prerequisites(
            "REF-1", today, today - timedelta(days=5)
        )

    rules.validate_catalogue_publication_prerequisites(
        "REF-1", today, today + timedelta(days=30)
    )


def test_br_016_verification_recording():
    with pytest.raises(CompletenessError, match="findings and notes must be recorded"):
        rules.validate_document_verification_recording(True, "")

    rules.validate_document_verification_recording(True, "All original documents verified.")


def test_br_017_renewal_conditions():
    now = datetime(2026, 11, 4, 12, 0)
    with pytest.raises(rules.RenewalEligibilityError, match="does not permit renewals"):
        rules.validate_renewal_conditions("approved", False, None, None, now)

    with pytest.raises(rules.RenewalEligibilityError, match="Only previously approved"):
        rules.validate_renewal_conditions("rejected", True, None, None, now)

    with pytest.raises(rules.RenewalEligibilityError, match="not opened yet"):
        rules.validate_renewal_conditions(
            "approved", True, now + timedelta(days=1), None, now
        )

    with pytest.raises(rules.RenewalEligibilityError, match="has closed"):
        rules.validate_renewal_conditions(
            "approved", True, None, now - timedelta(days=1), now
        )

    rules.validate_renewal_conditions(
        "approved", True, now - timedelta(days=1), now + timedelta(days=1), now
    )


def test_br_018_to_023_convener_awards_audit():
    # 018
    rules.assert_decision_authority(["spacs_convener"])
    with pytest.raises(UnauthorizedActionError, match="Access denied"):
        rules.assert_decision_authority(["spacs_assistant"])

    # 019
    with pytest.raises(rules.AwardPolicyError, match="Cannot publish award"):
        rules.validate_award_publication_allowed("open", "REF-EVID")

    with pytest.raises(rules.AwardPolicyError, match="Institutional approval evidence"):
        rules.validate_award_publication_allowed(rules.READY_FOR_PUBLICATION, "")

    rules.validate_award_publication_allowed(rules.READY_FOR_PUBLICATION, "INST-APPROVAL-2026")

    # 020
    with pytest.raises(rules.AwardPolicyError, match="Criteria version mismatch"):
        rules.validate_award_criteria_version(2, 1)
    rules.validate_award_criteria_version(2, 2)

    # 021
    with pytest.raises(rules.AuditProtectionError, match="immutable"):
        rules.assert_audit_modification_prohibited()

    # 022
    tasks = [{"id": 1, "status": "pending"}, {"id": 2, "status": "completed"}]
    assert rules.filter_reassignable_tasks(tasks) == [{"id": 1, "status": "pending"}]

    # 023
    candidates = [
        {"id": 1, "cpi": 8.5, "is_submitted": True},
        {"id": 2, "cpi": 6.0, "is_submitted": False},
    ]
    sys_pool = rules.filter_eligible_candidates(candidates, "system_pool", min_cpi=7.0)
    assert len(sys_pool) == 1 and sys_pool[0]["id"] == 1

    app_pool = rules.filter_eligible_candidates(candidates, "application")
    assert len(app_pool) == 1 and app_pool[0]["id"] == 1

    fallback_pool = rules.filter_eligible_candidates(candidates, "unknown_source")
    assert fallback_pool == candidates


def test_br_013_sla_escalation():
    now = datetime(2026, 11, 4, 12, 0)
    created_recent = now - timedelta(hours=20)
    created_old = now - timedelta(hours=50)

    assert rules.is_sla_breached(created_recent, sla_hours=48, now=now) is False
    assert rules.is_sla_breached(created_old, sla_hours=48, now=now) is True
