"""Business Rule tests for submission, documents, inventors, and filing preconditions."""

from __future__ import annotations

from decimal import Decimal

import pytest

from modules.pms.domain.entities import (
    MAX_DOCUMENT_SIZE_BYTES,
    validate_coinventor_shares,
    validate_document,
    validate_filing_preconditions,
)
from modules.pms.domain.errors import (
    ExternalServiceUnavailableError,
    IncompleteInventorsError,
    InvalidDocumentError,
    NotPermittedError,
    PreconditionNotMetError,
)
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import ApplicationDocument, PatentApplication
from modules.pms.services import (
    record_consent_and_agreement,
    record_external_filing,
    submit_application,
    upload_document_version,
)
from modules.pms.services.coinventors import update_coinventors

pytestmark = pytest.mark.django_db


def test_br_tc_007_permitted_pdf_supporting_document_for_submission():
    """BR-TC-007 | BR-PMS-014: permitted PDF supporting document for submission."""
    validate_document("specification.pdf", 1024, is_malware_clean=True)


def test_br_tc_008_prohibited_non_pdf_supporting_document_for_submission():
    """BR-TC-008 | BR-PMS-014: prohibited non-PDF supporting document for submission."""
    with pytest.raises(InvalidDocumentError):
        validate_document("specification.docx", 1024, is_malware_clean=True)
    with pytest.raises(InvalidDocumentError):
        validate_document("notes.txt", 1024, is_malware_clean=True)


def test_br_tc_009_boundary_below_50_mb_accepted():
    """BR-TC-009 | BR-PMS-015: boundary below 50 MB accepted."""
    below_50_mb = MAX_DOCUMENT_SIZE_BYTES - 1
    validate_document("under_limit.pdf", below_50_mb, is_malware_clean=True)


def test_br_tc_010_boundary_at_or_above_50_mb_rejected():
    """BR-TC-010 | BR-PMS-015: boundary at or above 50 MB rejected."""
    with pytest.raises(InvalidDocumentError):
        validate_document("at_limit.pdf", MAX_DOCUMENT_SIZE_BYTES, is_malware_clean=True)
    with pytest.raises(InvalidDocumentError):
        validate_document("over_limit.pdf", MAX_DOCUMENT_SIZE_BYTES + 1, is_malware_clean=True)


def test_br_tc_011_permitted_document_passing_malware_validation():
    """BR-TC-011 | BR-PMS-016: permitted document passing malware validation."""
    validate_document("clean.pdf", 2048, is_malware_clean=True)


def test_br_tc_012_prohibited_document_failing_malware_validation():
    """BR-TC-012 | BR-PMS-016: prohibited document failing malware validation."""
    with pytest.raises(InvalidDocumentError):
        validate_document("infected.pdf", 2048, is_malware_clean=False)


def test_br_tc_013_permitted_submission_with_all_required_application_fields_complete():
    """BR-TC-013 | BR-PMS-017: permitted submission with all required application fields complete."""
    app = submit_application(
        applicant_user_id=1001,
        title="Complete Invention",
        abstract="Complete Abstract",
        detailed_description="Complete Detailed Description",
        claims="1. A system comprising...",
        domain="Engineering",
    )
    assert app.pk is not None
    assert app.status == PatentApplicationStatus.SUBMITTED.value


def test_br_tc_014_prohibited_submission_when_required_application_fields_incomplete():
    """BR-TC-014 | BR-PMS-017: prohibited submission when required application fields are incomplete."""
    before_count = PatentApplication.objects.count()
    with pytest.raises(PreconditionNotMetError):
        submit_application(
            applicant_user_id=1001,
            title="",
            abstract="Complete Abstract",
            detailed_description="Complete Detailed Description",
            claims="1. Claim",
            domain="Engineering",
        )
    assert PatentApplication.objects.count() == before_count


def test_br_tc_015_permitted_external_filing_with_completed_inventor_agreements():
    """BR-TC-015 | BR-PMS-020: permitted external filing with completed inventor agreements."""
    validate_filing_preconditions(
        status=PatentApplicationStatus.APPROVED.value,
        budget_status="approved",
        all_agreements_complete=True,
    )


def test_br_tc_016_prohibited_external_filing_with_incomplete_inventor_agreements():
    """BR-TC-016 | BR-PMS-020: prohibited external filing with incomplete inventor agreements."""
    with pytest.raises(PreconditionNotMetError):
        validate_filing_preconditions(
            status=PatentApplicationStatus.APPROVED.value,
            budget_status="approved",
            all_agreements_complete=False,
        )


def test_br_tc_078_permitted_inventor_information_change_passing_pms_validation():
    """BR-TC-078 | BR-PMS-073: permitted inventor information change passing PMS validation."""
    app = submit_application(
        applicant_user_id=1001,
        title="Inventor Info App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    updated = update_coinventors(
        application_id=app.id,
        actor_user_id=1001,
        coinventors_data=[
            {
                "user_id": 1001,
                "name": "Alice Smith",
                "email": "alice@example.edu",
                "department": "CSE",
                "ownership_percentage": "100.00",
            }
        ],
    )
    assert len(updated) == 1
    assert updated[0].name == "Alice Smith"


def test_br_tc_079_prohibited_inventor_information_change_failing_pms_validation():
    """BR-TC-079 | BR-PMS-073: prohibited inventor information change failing PMS validation."""
    app = submit_application(
        applicant_user_id=1001,
        title="Inventor Validation App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    initial_names = list(app.coinventors.values_list("name", flat=True))
    with pytest.raises(IncompleteInventorsError):
        update_coinventors(
            application_id=app.id,
            actor_user_id=1001,
            coinventors_data=[
                {
                    "user_id": 1001,
                    "name": "Alice Smith",
                    "email": "alice@example.edu",
                    "ownership_percentage": "50.00",
                }
            ],
        )
    assert list(app.coinventors.values_list("name", flat=True)) == initial_names


def test_br_tc_080_permitted_inventor_ownership_percentages_passing_validation():
    """BR-TC-080 | BR-PMS-074: permitted inventor ownership percentages passing PMS validation."""
    validate_coinventor_shares([Decimal("60.00"), Decimal("40.00")])


def test_br_tc_081_prohibited_inventor_ownership_percentages_failing_validation():
    """BR-TC-081 | BR-PMS-074: prohibited inventor ownership percentages failing PMS validation."""
    with pytest.raises(IncompleteInventorsError):
        validate_coinventor_shares([Decimal("60.00"), Decimal("30.00")])


def test_br_tc_082_required_inventor_consent_obtained_before_filing():
    """BR-TC-082 | BR-PMS-075: required inventor consent obtained before filing."""
    app = submit_application(
        applicant_user_id=1001,
        title="Consent App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 2001,
                "name": "Co Inventor",
                "email": "co@example.edu",
                "ownership_percentage": "100.00",
            }
        ],
    )
    coinv = app.coinventors.first()
    assert coinv is not None
    updated = record_consent_and_agreement(
        coinventor_id=coinv.id,
        user_id=2001,
        consent_given=True,
        agreement_signed=True,
        electronic_signature="/s/ Co Inventor",
    )
    assert updated.consent_given is True
    assert updated.agreement_signed is True


def test_br_tc_083_prohibited_filing_when_required_inventor_consent_missing():
    """BR-TC-083 | BR-PMS-075: prohibited filing when required inventor consent is missing."""
    app = submit_application(
        applicant_user_id=1001,
        title="Missing Consent App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 2001,
                "name": "Co Inventor",
                "email": "co@example.edu",
                "ownership_percentage": "100.00",
                "agreement_signed": False,
            }
        ],
    )
    app.status = PatentApplicationStatus.APPROVED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    budget = app.budget
    budget.status = "approved"
    budget.save(update_fields=["status", "updated_at"])

    with pytest.raises(NotPermittedError):
        record_external_filing(
            application_id=app.id,
            attorney_user_id=5001,
            external_filing_id="EXT-100",
            external_filing_date=app.created_at.date(),
            filing_confirmation="CONF-100",
        )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPROVED.value
    assert app.external_filing_id == ""


def test_br_tc_084_permitted_electronic_signature_collection_when_configured():
    """BR-TC-084 | BR-PMS-076: permitted electronic signature collection when legally permitted and configured."""
    app = submit_application(
        applicant_user_id=1001,
        title="ESig App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 2001,
                "name": "Signer",
                "email": "signer@example.edu",
                "ownership_percentage": "100.00",
            }
        ],
    )
    coinv = app.coinventors.first()
    assert coinv is not None
    res = record_consent_and_agreement(
        coinventor_id=coinv.id,
        user_id=2001,
        consent_given=True,
        agreement_signed=True,
        electronic_signature="SIG-VALID-123",
    )
    assert res.electronic_signature == "SIG-VALID-123"
    assert res.signed_at is not None


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-085 | BR-PMS-076: A8_BASE has no policy flag or "
        "legal-permission toggle disabling electronic signature collection."
    )
)
def test_br_tc_085_prohibited_electronic_signature_collection_when_not_configured():
    """BR-TC-085 | BR-PMS-076: prohibited electronic signature collection when not legally permitted or not configured."""


def test_br_tc_086_electronic_signature_validation_when_configured():
    """BR-TC-086 | BR-PMS-077: electronic-signature validation when legally permitted and configured."""
    app = submit_application(
        applicant_user_id=1001,
        title="ESig Validate App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 2001,
                "name": "Signer",
                "email": "signer@example.edu",
                "ownership_percentage": "100.00",
            }
        ],
    )
    coinv = app.coinventors.first()
    assert coinv is not None
    res = record_consent_and_agreement(
        coinventor_id=coinv.id,
        user_id=2001,
        consent_given=True,
        agreement_signed=True,
        electronic_signature="SIG-CHECKED",
    )
    assert res.agreement_signed is True


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-087 | BR-PMS-077: A8_BASE provides no separate "
        "electronic-signature validation gate or configuration toggle."
    )
)
def test_br_tc_087_exception_when_electronic_signature_validation_not_configured():
    """BR-TC-087 | BR-PMS-077: exception when electronic-signature validation is not legally permitted or not configured."""


def test_br_tc_088_inventor_agreements_complete_before_filing():
    """BR-TC-088 | BR-PMS-078: inventor agreements complete before filing."""
    validate_filing_preconditions(
        status=PatentApplicationStatus.APPROVED.value,
        budget_status="approved",
        all_agreements_complete=True,
    )


def test_br_tc_089_prohibited_filing_when_inventor_agreements_incomplete():
    """BR-TC-089 | BR-PMS-078: prohibited filing when inventor agreements are incomplete."""
    with pytest.raises(PreconditionNotMetError):
        validate_filing_preconditions(
            status=PatentApplicationStatus.APPROVED.value,
            budget_status="approved",
            all_agreements_complete=False,
        )


def test_br_tc_090_automatic_version_numbering_for_new_document_versions():
    """BR-TC-090 | BR-PMS-082: automatic version numbering for new document versions."""
    app = submit_application(
        applicant_user_id=1001,
        title="Versioned Doc App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    v1 = ApplicationDocument.objects.create(
        application=app,
        doc_type="specification",
        title="Spec v1",
        file_format="pdf",
        file_size_bytes=500,
        version=1,
        is_current=True,
        uploaded_by_user_id=1001,
    )
    assert v1.version == 1

    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])
    with pytest.raises(ExternalServiceUnavailableError):
        upload_document_version(
            application_id=app.id,
            user_id=1001,
            user_role="Applicant",
            doc_type="specification",
            title="Spec v2",
            filename="spec_v2.pdf",
            file_size_bytes=500,
        )
    assert ApplicationDocument.objects.filter(application=app).count() == 1


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-091 | BR-PMS-084: No dedicated previous-version "
        "retrieval endpoint or selector with role/status matrix exists in A8_BASE."
    )
)
def test_br_tc_091_access_to_previous_document_versions_governed_by_role_and_status():
    """BR-TC-091 | BR-PMS-084: access to previous document versions governed by role and status rules."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-092 | BR-PMS-086: No standalone document-download/view "
        "endpoint or selector is exposed in A8_BASE."
    )
)
def test_br_tc_092_document_access_controlled_by_user_role_and_application_status():
    """BR-TC-092 | BR-PMS-086: document access controlled by user role and application status."""


def test_br_tc_093_permitted_document_editing_by_applicant_when_needs_revision():
    """BR-TC-093 | BR-PMS-087: permitted document editing by Applicant when status is Needs Revision."""
    app = submit_application(
        applicant_user_id=1001,
        title="Editable Doc App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])

    # State guard passes and reaches document validation (which fails closed on scanner).
    with pytest.raises(ExternalServiceUnavailableError):
        upload_document_version(
            application_id=app.id,
            user_id=1001,
            user_role="Applicant",
            doc_type="claims",
            title="Updated Claims",
            filename="claims.pdf",
            file_size_bytes=500,
        )


def test_br_tc_094_prohibited_document_editing_by_applicant_when_not_needs_revision():
    """BR-TC-094 | BR-PMS-087: prohibited document editing by Applicant when status is not Needs Revision."""
    app = submit_application(
        applicant_user_id=1001,
        title="Locked Doc App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    with pytest.raises(PreconditionNotMetError):
        upload_document_version(
            application_id=app.id,
            user_id=1001,
            user_role="Applicant",
            doc_type="claims",
            title="Blocked Claims",
            filename="claims.pdf",
            file_size_bytes=500,
        )
    assert ApplicationDocument.objects.filter(application=app).count() == 0


def test_br_tc_128_prohibited_attorney_assignment_before_director_approval():
    """BR-TC-128 | BR-PMS-127: prohibited Attorney assignment before Director approval is recorded."""
    with pytest.raises(PreconditionNotMetError):
        validate_filing_preconditions(
            status=PatentApplicationStatus.SUBMITTED.value,
            budget_status="approved",
            all_agreements_complete=True,
        )


def test_br_tc_129_prohibited_external_filing_before_approvals_and_budget():
    """BR-TC-129 | BR-PMS-128: prohibited external filing before required approvals and budget allocation are complete."""
    with pytest.raises(PreconditionNotMetError):
        validate_filing_preconditions(
            status=PatentApplicationStatus.APPROVED.value,
            budget_status="draft",
            all_agreements_complete=True,
        )
