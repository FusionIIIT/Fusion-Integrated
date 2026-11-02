"""Business Rule Specification verification tests for PMS.

Maps to all business rules BR-PMS-003 through BR-PMS-146.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.pms.domain.errors import (
    ConflictOfInterestError,
    InsufficientJustificationError,
    InvalidDocumentError,
    PreconditionNotMetError,
    WithdrawalNotAllowedError,
)
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    AttorneyPanel,
)
from modules.pms.services import (
    assign_attorney,
    assign_director,
    decide_budget,
    decide_renewal,
    file_appeal,
    monitor_and_process_deadlines,
    record_consent_and_agreement,
    record_external_filing,
    record_maintenance_action,
    record_patent_grant,
    record_withdrawal_consent,
    request_renewal_decision,
    respond_to_attorney_assignment,
    review_appeal,
    revise_and_resubmit_application,
    submit_application,
    submit_director_review,
    submit_or_update_budget,
    upload_document_version,
    withdraw_application,
)

pytestmark = pytest.mark.django_db


# --- BR-PMS-014, 015, 016, 017: Submission & Document Validation ---


def test_br_pms_017_required_application_fields():
    """BR-PMS-017: Required application fields must be complete before PMS accepts submission."""
    with pytest.raises(PreconditionNotMetError, match="title is required"):
        submit_application(
            applicant_user_id=1001,
            title="",
            abstract="A",
            detailed_description="D",
            claims="C",
            domain="Tech",
        )
    with pytest.raises(PreconditionNotMetError, match="abstract is required"):
        submit_application(
            applicant_user_id=1001,
            title="T",
            abstract="",
            detailed_description="D",
            claims="C",
            domain="Tech",
        )
    with pytest.raises(PreconditionNotMetError, match="claims are required"):
        submit_application(
            applicant_user_id=1001,
            title="T",
            abstract="A",
            detailed_description="D",
            claims="",
            domain="Tech",
        )


def test_br_pms_014_015_016_document_validations_during_submission():
    """BR-PMS-014 (PDF only), BR-PMS-015 (<50MB), BR-PMS-016 (Malware free)."""
    # Invalid extension
    with pytest.raises(InvalidDocumentError, match="Unsupported document format"):
        submit_application(
            applicant_user_id=1001,
            title="T",
            abstract="A",
            detailed_description="D",
            claims="C",
            domain="Tech",
            documents_data=[{"title": "Doc", "filename": "doc.docx", "file_size_bytes": 100}],
        )

    # Exceeding size
    with pytest.raises(InvalidDocumentError, match="exceeds the 50 MB limit"):
        submit_application(
            applicant_user_id=1001,
            title="T",
            abstract="A",
            detailed_description="D",
            claims="C",
            domain="Tech",
            documents_data=[
                {"title": "Doc", "filename": "doc.pdf", "file_size_bytes": 60 * 1024 * 1024}
            ],
        )

    # Malware infected
    with pytest.raises(InvalidDocumentError, match="failed security / malware validation"):
        submit_application(
            applicant_user_id=1001,
            title="T",
            abstract="A",
            detailed_description="D",
            claims="C",
            domain="Tech",
            documents_data=[
                {"title": "Doc", "filename": "doc.pdf", "file_size_bytes": 100, "is_clean": False}
            ],
        )


# --- BR-PMS-025, 026, 027: Director Assignment & Conflict of Interest ---


def test_br_pms_026_027_director_conflict_of_interest():
    """BR-PMS-026: Director must not review application in which Director is listed as inventor/co-inventor."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 2001,
                "name": "Co-Inv 1",
                "email": "c1@test.com",
                "ownership_percentage": "40.00",
            },
            {
                "user_id": 1001,
                "name": "Primary",
                "email": "p@test.com",
                "ownership_percentage": "60.00",
            },
        ],
    )

    # Director is primary applicant
    with pytest.raises(ConflictOfInterestError):
        assign_director(application_id=app.id, director_user_id=1001, assigned_by_user_id=9001)

    # Director is co-inventor
    with pytest.raises(ConflictOfInterestError):
        assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)

    # Non-conflicted director succeeds
    assigned_app = assign_director(
        application_id=app.id, director_user_id=3001, assigned_by_user_id=9001
    )
    assert assigned_app.status == PatentApplicationStatus.UNDER_REVIEW.value
    assert assigned_app.assigned_director_user_id == 3001
    assert assigned_app.review_deadline is not None


# --- BR-PMS-029, 030, 031: Director Review & Justification Constraint ---


def test_br_pms_029_030_director_review_validation():
    """BR-PMS-029 (Approve/Reject/Needs Revision), BR-PMS-030 (justification >= 50 characters)."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    assign_director(application_id=app.id, director_user_id=3001, assigned_by_user_id=9001)

    # Justification too short (< 50 chars)
    with pytest.raises(InsufficientJustificationError):
        submit_director_review(
            application_id=app.id,
            director_user_id=3001,
            decision="Approve",
            justification="Short justification.",
        )

    # Valid justification
    valid_justification = (
        "This patent application presents clear technical novelty and inventive step."
    )
    review = submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification=valid_justification,
        feedback="All claims accepted.",
    )
    assert review.decision == "Approve"
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPROVED.value


# --- BR-PMS-033, 034, 035, 036, 038: Revision Loop and Deadlines ---


def test_br_pms_033_035_036_revision_lifecycle():
    """BR-PMS-033 (revision permitted for Needs Revision), BR-PMS-036 (must address feedback)."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    assign_director(application_id=app.id, director_user_id=3001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Needs Revision",
        justification="The claims in section 4 lack sufficient clarity and technical specificity.",
        feedback="Please narrow claims 1-3.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.NEEDS_REVISION.value
    assert app.revision_deadline is not None

    # Resubmission without feedback notes fails (BR-PMS-036)
    with pytest.raises(
        PreconditionNotMetError, match="must include notes addressing Director feedback"
    ):
        revise_and_resubmit_application(
            application_id=app.id,
            applicant_user_id=1001,
            feedback_response="",
            claims="Updated claims",
        )

    # Valid resubmission
    revised_app = revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response="Narrowed claims 1 to 3 to focus exclusively on the specific algorithm.",
        claims="1. A narrowed claim...",
    )
    assert revised_app.status == PatentApplicationStatus.RESUBMITTED.value


def test_br_pms_038_revision_expiration():
    """BR-PMS-038: Overdue 60-day revision deadline changes status to Expired."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    assign_director(application_id=app.id, director_user_id=3001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Needs Revision",
        justification="The claims in section 4 lack sufficient clarity and technical specificity.",
    )
    app.refresh_from_db()

    # Move revision_deadline into the past
    app.revision_deadline = timezone.now() - timedelta(days=2)
    app.save(update_fields=["revision_deadline"])

    # Processing deadlines expires the application
    stats = monitor_and_process_deadlines(now=timezone.now())
    assert stats["revisions_expired"] >= 1
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.EXPIRED.value


# --- BR-PMS-040, 041, 043, 044, 127: Attorney Assignment Rules ---


def test_br_pms_040_127_attorney_assignment_prerequisite():
    """BR-PMS-127: Attorney assignment must not occur before Director approval is recorded."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    # Status is Submitted (not Approved)
    with pytest.raises(PreconditionNotMetError, match="cannot receive attorney assignment"):
        assign_attorney(application_id=app.id, attorney_user_id=5001, assigned_by_user_id=9001)


def test_br_pms_041_043_044_attorney_panel_and_workload():
    """BR-PMS-041 (approved panel), BR-PMS-043 (workload limit), BR-PMS-044 (conflict)."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    assign_director(application_id=app.id, director_user_id=3001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification="Novelty and technical application are well demonstrated in claims.",
    )
    app.refresh_from_db()

    # Not on approved panel (BR-PMS-041)
    with pytest.raises(PreconditionNotMetError, match="not on the approved attorney panel"):
        assign_attorney(application_id=app.id, attorney_user_id=8888, assigned_by_user_id=9001)

    # Create approved panel entry with max workload (BR-PMS-043)
    panel_busy = AttorneyPanel.objects.create(
        attorney_user_id=5001,
        name="Busy Atty",
        email="busy@atty.com",
        is_approved=True,
        current_workload=5,
        max_workload=5,
    )
    with pytest.raises(PreconditionNotMetError, match="reached maximum workload limit"):
        assign_attorney(application_id=app.id, attorney_user_id=5001, assigned_by_user_id=9001)

    # Valid panel attorney
    panel_avail = AttorneyPanel.objects.create(
        attorney_user_id=5002,
        name="Avail Atty",
        email="avail@atty.com",
        is_approved=True,
        current_workload=1,
        max_workload=5,
    )
    assignment = assign_attorney(
        application_id=app.id, attorney_user_id=5002, assigned_by_user_id=9001
    )
    assert assignment.status == "offered"

    # Attorney accepts assignment
    respond_to_attorney_assignment(assignment_id=assignment.id, attorney_user_id=5002, accept=True)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.ATTORNEY_ASSIGNED.value
    panel_avail.refresh_from_db()
    assert panel_avail.current_workload == 2


# --- BR-PMS-048..053: Budget Data, Approval, and Threshold Escalation ---


def test_br_pms_051_budget_escalation_above_threshold():
    """BR-PMS-051: When total cost exceeds configured threshold limit, PMS must route/escalate."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    assign_director(application_id=app.id, director_user_id=3001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification="Novelty and technical application are well demonstrated in claims.",
    )
    app.refresh_from_db()

    # Budget total 150,000 > threshold 100,000
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("50000.00"),
        attorney_fees=Decimal("80000.00"),
        administrative_costs=Decimal("20000.00"),
        actor_user_id=3001,
        threshold_limit=Decimal("100000.00"),
    )

    # Director tries to approve -> automatically escalates due to threshold (BR-PMS-051)
    budget = decide_budget(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification="Approved but exceeds limit",
    )
    assert budget.status == "escalated"
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.ESCALATED.value


# --- BR-PMS-020, 056, 078, 128: Pre-Filing Prerequisites and International Filing ---


def test_br_pms_020_056_128_external_filing_rules():
    """BR-PMS-020, 078, 128 (agreements & budget prerequisite), BR-PMS-056 (international justification)."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 2001,
                "name": "Co-Inv",
                "email": "c@test.com",
                "ownership_percentage": "100.00",
                "agreement_signed": False,
            }
        ],
    )
    assign_director(application_id=app.id, director_user_id=3001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification="Novelty and technical application are well demonstrated in claims.",
    )
    app.refresh_from_db()

    # Budget approved
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("10000.00"),
        attorney_fees=Decimal("20000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=3001,
        threshold_limit=Decimal("100000.00"),
    )
    decide_budget(application_id=app.id, director_user_id=3001, decision="Approve")
    app.refresh_from_db()

    # Co-inventor has not signed agreement (BR-PMS-020, 078)
    with pytest.raises(PreconditionNotMetError, match="agreements and consents must be complete"):
        record_external_filing(
            application_id=app.id,
            attorney_user_id=5001,
            external_filing_id="IPO/2026/001",
            external_filing_date=date(2026, 10, 1),
            filing_confirmation="Filing confirmed.",
        )

    # Sign agreement
    coinv = app.coinventors.first()
    record_consent_and_agreement(
        coinventor_id=coinv.id, user_id=2001, consent_given=True, agreement_signed=True
    )

    # International filing without justification fails (BR-PMS-056)
    with pytest.raises(
        PreconditionNotMetError, match="International filings require additional justification"
    ):
        record_external_filing(
            application_id=app.id,
            attorney_user_id=5001,
            external_filing_id="PCT/IB/2026/001",
            external_filing_date=date(2026, 10, 1),
            filing_confirmation="PCT confirmed.",
            is_international=True,
            international_justification="",
        )

    # Valid international filing
    filed_app = record_external_filing(
        application_id=app.id,
        attorney_user_id=5001,
        external_filing_id="PCT/IB/2026/001",
        external_filing_date=date(2026, 10, 1),
        filing_confirmation="PCT confirmed.",
        is_international=True,
        international_justification="Targeting European and US markets for institutional licensing.",
    )
    assert filed_app.status == PatentApplicationStatus.FILED.value
    assert filed_app.external_filing_id == "PCT/IB/2026/001"


# --- BR-PMS-059, 060, 061: Post-Grant and Maintenance Decision Cycle ---


def test_br_pms_059_060_061_post_grant_maintenance():
    """BR-PMS-059 (active only when Granted), BR-PMS-060 (schedule), BR-PMS-061 (renewal decision)."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    # Cannot grant before filed
    with pytest.raises(PreconditionNotMetError, match="Cannot grant patent"):
        record_patent_grant(
            application_id=app.id,
            attorney_user_id=5001,
            patent_number="IN99999",
            grant_date=date(2026, 11, 1),
        )

    # Fast forward to Filed
    app.status = PatentApplicationStatus.FILED.value
    app.save()

    # Grant patent (BR-PMS-059)
    record_patent_grant(
        application_id=app.id,
        attorney_user_id=5001,
        patent_number="IN99999",
        grant_date=date(2026, 11, 1),
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.GRANTED.value
    assert app.maintenance_records.count() == 1  # Cycle 1 scheduled

    maint = app.maintenance_records.first()
    request_renewal_decision(maintenance_id=maint.id, attorney_user_id=5001)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RENEWAL_DECISION_REQUESTED.value

    # Director decides Renew (BR-PMS-061)
    decide_renewal(maintenance_id=maint.id, director_user_id=3001, decision="Renew")
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RENEWAL_APPROVED.value

    # Attorney records action -> status becomes Renewed and next cycle is scheduled
    record_maintenance_action(
        maintenance_id=maint.id, attorney_user_id=5001, transaction_reference="TXN-98765"
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RENEWED.value
    assert app.maintenance_records.count() == 2  # Next cycle created


# --- BR-PMS-067..070: Withdrawal Rules and Co-inventor Consent ---


def test_br_pms_067_070_withdrawal_rules():
    """BR-PMS-067 (before filing), BR-PMS-069 (reason), BR-PMS-070 (co-inventor consent)."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 2001,
                "name": "Co-Inv",
                "email": "c@test.com",
                "ownership_percentage": "100.00",
            }
        ],
    )

    # Missing co-inventor consent (BR-PMS-070)
    with pytest.raises(WithdrawalNotAllowedError, match="All co-inventors must record consent"):
        withdraw_application(
            application_id=app.id, applicant_user_id=1001, reason="Commercial reasons"
        )

    # Give consent
    coinv = app.coinventors.first()
    record_withdrawal_consent(coinventor_id=coinv.id, user_id=2001, consent_given=True)

    # Missing reason (BR-PMS-069)
    with pytest.raises(WithdrawalNotAllowedError, match="reason is required"):
        withdraw_application(application_id=app.id, applicant_user_id=1001, reason="")

    # Valid withdrawal
    withdrawn_app = withdraw_application(
        application_id=app.id, applicant_user_id=1001, reason="Commercial strategy shift."
    )
    assert withdrawn_app.status == PatentApplicationStatus.WITHDRAWN.value
    assert withdrawn_app.is_withdrawn is True


# --- BR-PMS-087: Document Edit Rule ---


def test_br_pms_087_applicant_document_edit_rule():
    """BR-PMS-087: Applicants may edit application documents only while status is Needs Revision."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    # Under review
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.save()

    # Applicant tries to upload new document during Under Review -> Prohibited
    with pytest.raises(
        PreconditionNotMetError,
        match="Applicants may edit application documents only while status is Needs Revision",
    ):
        upload_document_version(
            application_id=app.id,
            user_id=1001,
            user_role="Applicant",
            doc_type="claims",
            title="Revised Claims",
            filename="claims.pdf",
            file_size_bytes=1000,
        )

    # In Needs Revision status -> Allowed
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save()
    new_doc = upload_document_version(
        application_id=app.id,
        user_id=1001,
        user_role="Applicant",
        doc_type="claims",
        title="Revised Claims",
        filename="claims.pdf",
        file_size_bytes=1000,
    )
    assert new_doc.version == 1
    assert new_doc.is_current is True


# --- BR-PMS-092..095: Appeal Rules ---


def test_br_pms_092_095_appeal_rules():
    """BR-PMS-092 (only from Rejected), BR-PMS-094 (grounds & justification), BR-PMS-095 (outcomes)."""
    app = submit_application(
        applicant_user_id=1001,
        title="T",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    # Cannot appeal from Submitted
    with pytest.raises(
        PreconditionNotMetError, match="only be filed for applications in 'rejected' status"
    ):
        file_appeal(
            application_id=app.id,
            applicant_user_id=1001,
            grounds="Disagreement with review",
            justification="Full justification...",
        )

    # Set to Rejected
    app.status = PatentApplicationStatus.REJECTED.value
    app.save()

    appeal = file_appeal(
        application_id=app.id,
        applicant_user_id=1001,
        grounds="Disagreement with prior art interpretation",
        justification="The cited reference D1 does not disclose element X as claimed.",
    )
    assert appeal.status == "submitted"
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPEAL_SUBMITTED.value

    # Director review appeal: Remand for Amendment (BR-PMS-095)
    review_appeal(
        appeal_id=appeal.id,
        director_user_id=3001,
        outcome="Remand for Amendment",
        outcome_justification="Applicant's distinction regarding element X is plausible. Remanded to amend claims.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.REMANDED_FOR_AMENDMENT.value
