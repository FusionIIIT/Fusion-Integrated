"""Automated Backend Tests for Business Rules Strategy (BR: Business Rule Specifications).
Frozen Design: a8_design/BR_DESIGN.json
"""

from datetime import date, datetime, timedelta
import pytest
from django.utils import timezone

from modules.spacs.models import (
    SpacsApplication,
    SpacsAuditLog,
    SpacsCatalogueEntry,
    SpacsDocument,
    SpacsNotification,
    SpacsTask,
)
from modules.spacs.domain import rules
from modules.spacs.domain.errors import (
    AuditProtectionError,
    AwardPolicyError,
    CompletenessError,
    DocumentReuseError,
    DuplicateApplicationError,
    EligibilityError,
    RenewalEligibilityError,
    UnauthorizedActionError,
)
from modules.spacs.domain.state_machine import (
    AWAITING_INSTITUTIONAL_APPROVAL,
    READY_FOR_PUBLICATION,
)


def test_br_001_outcomes():
    """TEST-BR-001-PASS, FAIL-CPI, FAIL-INC: Eligibility Must Be Satisfied."""
    # Permitted outcome
    rules.validate_eligibility(student_cpi=7.5, student_family_income=400000.0, min_cpi=7.0, max_family_income=500000.0)

    # Threshold-side CPI failure
    with pytest.raises(EligibilityError, match="below the required minimum"):
        rules.validate_eligibility(student_cpi=6.9, student_family_income=400000.0, min_cpi=7.0)

    # Threshold-side Income failure
    with pytest.raises(EligibilityError, match="exceeds maximum threshold"):
        rules.validate_eligibility(student_cpi=7.5, student_family_income=500001.0, min_cpi=7.0, max_family_income=500000.0)


def test_br_002_outcomes():
    """TEST-BR-002-PASS, FAIL: No Duplicate Applications."""
    # Permitted: no active application
    rules.check_no_duplicate([])

    # Prohibited: active application exists
    with pytest.raises(DuplicateApplicationError):
        rules.check_no_duplicate(["submitted"])

    # Permitted: previous application withdrawn
    rules.check_no_duplicate(["withdrawn"])


def test_br_003_outcomes():
    """TEST-BR-003-PASS, FAIL-EXPIRED, FAIL-USER: Reuse of Previously Uploaded Documents."""
    today = date.today()
    # Permitted
    rules.validate_document_reuse(
        doc_user_id=701, applicant_user_id=701, doc_type="income_cert", required_doc_type="income_cert", doc_valid_until=today + timedelta(days=30), reference_date=today
    )

    # Prohibited: Expired
    with pytest.raises(DocumentReuseError, match="expired"):
        rules.validate_document_reuse(
            doc_user_id=701, applicant_user_id=701, doc_type="income_cert", required_doc_type="income_cert", doc_valid_until=today - timedelta(days=1), reference_date=today
        )

    # Prohibited: Different user
    with pytest.raises(DocumentReuseError, match="belonging to another user"):
        rules.validate_document_reuse(
            doc_user_id=999, applicant_user_id=701, doc_type="income_cert", required_doc_type="income_cert"
        )


def test_br_004_outcomes():
    """TEST-BR-004-PASS, FAIL: Application Completeness."""
    # Permitted
    rules.validate_completeness(
        application_data={"name": "Test", "bank": "1234"},
        mandatory_fields=["name", "bank"],
        uploaded_doc_types=["doc_a"],
        required_doc_types=["doc_a"],
    )

    # Prohibited: Missing mandatory field
    with pytest.raises(CompletenessError, match="field"):
        rules.validate_completeness(
            application_data={"name": "Test"},
            mandatory_fields=["name", "bank"],
            uploaded_doc_types=["doc_a"],
            required_doc_types=["doc_a"],
        )


def test_br_005_and_006_assistant_authorities():
    """TEST-BR-005, TEST-BR-006: Review Access and Assistant Authority Boundaries."""
    # BR-005: Permitted for assistant and convener
    rules.check_application_review_access(["spacs_assistant"])
    rules.check_application_review_access(["spacs_convener"])

    # BR-005: Prohibited for student
    with pytest.raises(UnauthorizedActionError):
        rules.check_application_review_access(["student"])

    # BR-006: Assistant permitted actions
    rules.assert_assistant_action_permitted("mark_verified")
    rules.assert_assistant_action_permitted("request_correction")

    # BR-006: Assistant prohibited from final sanction
    with pytest.raises(UnauthorizedActionError):
        rules.assert_assistant_action_permitted("approve")


def test_br_007_draft_preservation():
    """TEST-BR-007-PASS: Draft Preservation on Timeout/Error."""
    existing = {"field_1": "val1"}
    new_in = {"field_2": "val2"}
    merged = rules.preserve_draft_payload(existing, new_in)
    assert merged == {"field_1": "val1", "field_2": "val2"}


def test_br_008_significant_events():
    """TEST-BR-008-PASS: Notification on Significant Status Change."""
    assert rules.should_notify_event("submitted") is True
    assert rules.should_notify_event("approved") is True
    assert rules.should_notify_event("rejected") is True
    assert rules.should_notify_event("random_trivial_click") is False


def test_br_009_and_010_withdrawal_and_ownership():
    """TEST-BR-009, TEST-BR-010: Withdrawal and Ownership Constraints."""
    # BR-009: Permitted in submitted state
    rules.validate_can_withdraw("submitted")

    # BR-009: Prohibited in approved terminal state
    with pytest.raises(UnauthorizedActionError, match="terminal state"):
        rules.validate_can_withdraw("approved")

    # BR-010: Ownership matching
    rules.assert_ownership(100, 100)

    with pytest.raises(UnauthorizedActionError, match="not the owner"):
        rules.assert_ownership(100, 200)


def test_br_011_correction_and_revalidation():
    """TEST-BR-011-PASS, FAIL: Modification only in editable states."""
    rules.validate_can_modify("correction_required")
    rules.validate_can_modify("draft")

    with pytest.raises(UnauthorizedActionError, match="not editable"):
        rules.validate_can_modify("under_verification")


def test_br_012_download_print_access():
    """TEST-BR-012-PASS, FAIL: Download / Print Access."""
    # Student exports own
    rules.validate_download_access(701, 701, ["student"])

    # Staff exports
    rules.validate_download_access(701, 20, ["spacs_assistant"])

    # Student exports other
    with pytest.raises(UnauthorizedActionError):
        rules.validate_download_access(701, 702, ["student"])


def test_br_013_sla_escalation():
    """TEST-BR-013-PASS: SLA Breached Calculation."""
    now = datetime(2026, 11, 4, 12, 0)
    old = now - timedelta(hours=50)
    recent = now - timedelta(hours=10)

    assert rules.is_sla_breached(old, sla_hours=48, now=now) is True
    assert rules.is_sla_breached(recent, sla_hours=48, now=now) is False


def test_br_014_catalogue_publication_source_of_truth():
    """TEST-BR-014-PASS, FAIL: Published Catalogue Active Window."""
    now = datetime(2026, 11, 4, 12, 0)
    w_start = now - timedelta(days=5)
    w_end = now + timedelta(days=10)

    # Permitted
    rules.validate_catalogue_published_and_open("published", w_start, w_end, now)

    # Prohibited: Draft status
    with pytest.raises(EligibilityError, match="not active"):
        rules.validate_catalogue_published_and_open("draft", w_start, w_end, now)

    # Prohibited: Window closed
    with pytest.raises(EligibilityError, match="window is closed"):
        rules.validate_catalogue_published_and_open("published", w_start - timedelta(days=20), now - timedelta(days=1), now)


def test_br_015_catalogue_approved_policy_prerequisites():
    """TEST-BR-015-PASS, FAIL: Catalogue Must Reflect Approved Policy."""
    today = date.today()
    # Permitted
    rules.validate_catalogue_publication_prerequisites("SENATE-REF-101", today, today + timedelta(days=365))

    # Prohibited: Missing policy ref
    with pytest.raises(AwardPolicyError, match="Policy approval reference is mandatory"):
        rules.validate_catalogue_publication_prerequisites("", today)


def test_br_016_document_authenticity_recording():
    """TEST-BR-016-PASS: Document Authenticity Verification Recording."""
    rules.validate_document_verification_recording(True, "Document verified with registrar seal")

    with pytest.raises(CompletenessError):
        rules.validate_document_verification_recording(True, "")


def test_br_017_renewal_rules():
    """TEST-BR-017-PASS, FAIL: Renewal Conditions."""
    now = datetime(2026, 11, 4, 12, 0)
    # Permitted
    rules.validate_renewal_conditions(
        parent_state="approved",
        renewal_allowed=True,
        renewal_window_start=now - timedelta(days=5),
        renewal_window_end=now + timedelta(days=10),
        current_time=now,
    )

    # Prohibited: Parent was rejected
    with pytest.raises(RenewalEligibilityError, match="Only previously approved"):
        rules.validate_renewal_conditions(
            parent_state="rejected",
            renewal_allowed=True,
            renewal_window_start=None,
            renewal_window_end=None,
            current_time=now,
        )


def test_br_018_scholarship_decision_authority():
    """TEST-BR-018-PASS, FAIL: Scholarship Decision Authority."""
    rules.assert_decision_authority(["spacs_convener"])

    with pytest.raises(UnauthorizedActionError):
        rules.assert_decision_authority(["spacs_assistant"])


def test_br_019_and_020_award_evaluation_and_criteria():
    """TEST-BR-019, TEST-BR-020: Award Publication and Criteria Versioning."""
    # Permitted publication
    rules.validate_award_publication_allowed(READY_FOR_PUBLICATION, "SENATE-APPROVED")

    # Prohibited: Approval evidence missing
    with pytest.raises(AwardPolicyError, match="approval evidence"):
        rules.validate_award_publication_allowed(READY_FOR_PUBLICATION, "")

    # BR-020: Criteria version consistency
    rules.validate_award_criteria_version(1, 1)

    with pytest.raises(AwardPolicyError, match="version mismatch"):
        rules.validate_award_criteria_version(1, 2)


@pytest.mark.django_db
def test_br_021_audit_records_protected():
    """TEST-BR-021-FAIL: Audit Records Protected and Restricted."""
    log = SpacsAuditLog.objects.create(event_type="test", entity_type="app", entity_id="1", actor_user_id=1)
    with pytest.raises(AuditProtectionError):
        log.delete()

    with pytest.raises(AuditProtectionError):
        log.actor_user_id = 99
        log.save()


def test_br_022_role_reassignment():
    """TEST-BR-022-PASS: Role Reassignment Preserves History."""
    tasks = [
        {"id": 1, "status": "pending"},
        {"id": 2, "status": "completed"},
    ]
    reassignable = rules.filter_reassignable_tasks(tasks)
    assert len(reassignable) == 1
    assert reassignable[0]["id"] == 1


def test_br_023_candidate_source_method():
    """TEST-BR-023-PASS: Award Candidate Source Method Filtering."""
    candidates = [
        {"student_user_id": 1, "cpi": 8.5},
        {"student_user_id": 2, "cpi": 7.5},
    ]
    pool = rules.filter_eligible_candidates(candidates, source_method="system_pool", min_cpi=8.0)
    assert len(pool) == 1
    assert pool[0]["student_user_id"] == 1
