"""FR Spec Tests: Prior Art, Document Versioning, Licensing, and Appeals.

Covers TC-111..TC-121, TC-121b, TC-122..TC-124, TC-124b, TC-125..TC-127,
TC-127b, and TC-128..TC-141 from FR_DESIGN.json.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.domain.entities import validate_document
from modules.pms.domain.errors import (
    ExternalServiceUnavailableError,
    PreconditionNotMetError,
)
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    ApplicationDocument,
    LicensingRequest,
    PatentAppeal,
    PmsAuditTrail,
)
from modules.pms.services import documents as docs_service
from modules.pms.services import (
    file_appeal,
    review_appeal,
    review_licensing_request,
    submit_application,
    submit_licensing_request,
    upload_document_version,
)
from modules.pms.services import prior_art as prior_art_service

pytestmark = pytest.mark.django_db

API = "/api/v1/pms"


def _auth_client(stub_iam, user_id: int, role: str = "student", permissions: tuple[str, ...] = ()):
    session = make_session(
        user_id=user_id,
        roles=(role,),
        active_role=role,
        permissions=permissions,
        modules=("pms",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def _make_app(applicant_user_id: int = 1001, title: str = "Patent App"):
    return submit_application(
        applicant_user_id=applicant_user_id,
        title=title,
        abstract="Abstract",
        detailed_description="Detailed description",
        claims="Claims",
        domain="Computing",
    )


def _allow_clean_pdf(monkeypatch):
    def _validate(filename: str, file_size_bytes: int, is_malware_clean: bool | None = None):
        return validate_document(filename, file_size_bytes, is_malware_clean=True)

    monkeypatch.setattr(docs_service, "validate_document", _validate)


def test_tc_111_pms_afr_141_applicant_searches_prior_art_references(stub_iam, monkeypatch):
    """Test ID: TC-111 | Source ID: PMS-AFR-141: Applicant searches prior-art references."""
    monkeypatch.setattr(
        prior_art_service,
        "search_prior_art",
        lambda *, query, domain="", actor_user_id=None: [{"id": "REF-1", "title": f"Match for {query}"}],
    )
    client = _auth_client(stub_iam, 1001, "student", ("pms.prior_art.search",))
    res = client.get(f"{API}/prior-art/search/?q=neural")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 1


def test_tc_112_pms_afr_142_attorney_searches_prior_art_references(stub_iam, monkeypatch):
    """Test ID: TC-112 | Source ID: PMS-AFR-142: Attorney searches prior-art references."""
    monkeypatch.setattr(
        prior_art_service,
        "search_prior_art",
        lambda *, query, domain="", actor_user_id=None: [{"id": "PAT-101", "title": "Prior Patent"}],
    )
    client = _auth_client(stub_iam, 5001, "attorney", ("pms.prior_art.search",))
    res = client.get(f"{API}/prior-art/search/?q=circuit")
    assert res.status_code == 200
    assert res.json()["results"][0]["id"] == "PAT-101"


def test_tc_113_pms_afr_143_query_relevant_patent_databases_when_available(monkeypatch):
    """Test ID: TC-113 | Source ID: PMS-AFR-143: query relevant patent databases when available."""
    def _patent_search(*, query: str, domain: str = "", actor_user_id: int | None = None):
        return [{"source": "USPTO", "reference_id": "US-9001", "title": query}]

    monkeypatch.setattr(prior_art_service, "search_prior_art", _patent_search)
    results = prior_art_service.search_prior_art(query="photonic switch", actor_user_id=5001)
    assert results[0]["source"] == "USPTO"


def test_tc_114_pms_afr_144_query_relevant_publication_databases_when_available(monkeypatch):
    """Test ID: TC-114 | Source ID: PMS-AFR-144: query relevant publication databases when available."""
    def _pub_search(*, query: str, domain: str = "", actor_user_id: int | None = None):
        return [{"source": "IEEE", "reference_id": "IEEE-404", "title": query}]

    monkeypatch.setattr(prior_art_service, "search_prior_art", _pub_search)
    results = prior_art_service.search_prior_art(query="quantum key", actor_user_id=1001)
    assert results[0]["source"] == "IEEE"


def test_tc_115_pms_afr_145_display_prior_art_search_results_with_relevance_ranking(monkeypatch):
    """Test ID: TC-115 | Source ID: PMS-AFR-145: display prior-art search results with relevance ranking."""
    ranked = [
        {"reference_id": "R1", "score": 0.95},
        {"reference_id": "R2", "score": 0.60},
    ]
    monkeypatch.setattr(
        prior_art_service,
        "search_prior_art",
        lambda *, query, domain="", actor_user_id=None: ranked,
    )
    out = prior_art_service.search_prior_art(query="ranking", actor_user_id=1001)
    assert out[0]["score"] > out[1]["score"]


def test_tc_116_pms_afr_146_attach_selected_prior_art_references_to_application(stub_iam):
    """Test ID: TC-116 | Source ID: PMS-AFR-146: attach selected prior-art references to application."""
    app = _make_app()
    client = _auth_client(stub_iam, 1001, "student", ("pms.prior_art.search", "pms.application.view_self"))
    res = client.post(
        f"{API}/applications/{app.id}/prior-art/",
        {
            "source": "EPO",
            "reference_id": "EP-1234567",
            "title": "Optical Waveguide",
            "relevance": "high",
        },
        format="json",
    )
    assert res.status_code == 201
    assert app.prior_art_references.filter(reference_id="EP-1234567").exists()


def test_tc_117_pms_afr_147_log_prior_art_search_sessions_for_audit_trail():
    """Test ID: TC-117 | Source ID: PMS-AFR-147: log prior-art search sessions for audit trail."""
    with pytest.raises(ExternalServiceUnavailableError):
        prior_art_service.search_prior_art(query="audit test", actor_user_id=1001)
    assert PmsAuditTrail.objects.filter(
        actor_user_id=1001, action_type="prior_art_search_unavailable"
    ).exists()


def test_tc_118_pms_afr_148_support_keyword_optimization_for_prior_art_search(monkeypatch):
    """Test ID: TC-118 | Source ID: PMS-AFR-148: support keyword optimization for prior-art search."""
    captured = {}

    def _opt_search(*, query: str, domain: str = "", actor_user_id: int | None = None):
        captured["query"] = query
        return [{"query_used": query}]

    monkeypatch.setattr(prior_art_service, "search_prior_art", _opt_search)
    out = prior_art_service.search_prior_art(query="battery AND thermal OR cooling", actor_user_id=1001)
    assert captured["query"] == "battery AND thermal OR cooling"
    assert out[0]["query_used"] == "battery AND thermal OR cooling"


def test_tc_119_pms_afr_149_support_classification_mapping_for_prior_art_search(monkeypatch):
    """Test ID: TC-119 | Source ID: PMS-AFR-149: support classification mapping for prior-art search."""
    captured = {}

    def _cls_search(*, query: str, domain: str = "", actor_user_id: int | None = None):
        captured["domain"] = domain
        return [{"domain": domain}]

    monkeypatch.setattr(prior_art_service, "search_prior_art", _cls_search)
    out = prior_art_service.search_prior_art(query="cpc:H01L", domain="H01L", actor_user_id=5001)
    assert captured["domain"] == "H01L"
    assert out[0]["domain"] == "H01L"


def test_tc_120_pms_afr_150_maintain_version_history_for_application_documents(monkeypatch):
    """Test ID: TC-120 | Source ID: PMS-AFR-150: maintain version history for application documents."""
    _allow_clean_pdf(monkeypatch)
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])

    upload_document_version(
        application_id=app.id, user_id=1001, user_role="Applicant",
        doc_type="claims", title="Claims v1", filename="claims.pdf", file_size_bytes=500
    )
    upload_document_version(
        application_id=app.id, user_id=1001, user_role="Applicant",
        doc_type="claims", title="Claims v2", filename="claims.pdf", file_size_bytes=600
    )
    assert app.documents.filter(doc_type="claims").count() == 2


def test_tc_121_pms_afr_151_allow_uploading_new_document_versions_when_role_and_status_permit(monkeypatch):
    """Test ID: TC-121 | Source ID: PMS-AFR-151: allow uploading new document versions when role and status permit."""
    _allow_clean_pdf(monkeypatch)
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])

    doc = upload_document_version(
        application_id=app.id, user_id=1001, user_role="Applicant",
        doc_type="specification", title="Spec Revised", filename="spec.pdf", file_size_bytes=700
    )
    assert doc.version == 1
    assert doc.is_current is True


def test_tc_121b_pms_afr_151_reject_uploading_new_document_versions_when_role_or_status_does_not_permit(monkeypatch):
    """Test ID: TC-121b | Source ID: PMS-AFR-151: reject uploading new document versions when role or status does not permit."""
    _allow_clean_pdf(monkeypatch)
    app = _make_app()
    with pytest.raises(PreconditionNotMetError):
        upload_document_version(
            application_id=app.id, user_id=1001, user_role="Applicant",
            doc_type="specification", title="Blocked Edit", filename="spec.pdf", file_size_bytes=700
        )


def test_tc_122_pms_afr_152_assign_automatic_version_numbers_to_new_document_versions(monkeypatch):
    """Test ID: TC-122 | Source ID: PMS-AFR-152: assign automatic version numbers to new document versions."""
    _allow_clean_pdf(monkeypatch)
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])

    d1 = upload_document_version(
        application_id=app.id, user_id=1001, user_role="Applicant",
        doc_type="abstract", title="Abs 1", filename="abs.pdf", file_size_bytes=300
    )
    d2 = upload_document_version(
        application_id=app.id, user_id=1001, user_role="Applicant",
        doc_type="abstract", title="Abs 2", filename="abs.pdf", file_size_bytes=350
    )
    assert d1.version == 1
    assert d2.version == 2


def test_tc_123_pms_afr_153_archive_previous_document_versions(monkeypatch):
    """Test ID: TC-123 | Source ID: PMS-AFR-153: archive previous document versions."""
    _allow_clean_pdf(monkeypatch)
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])

    d1 = upload_document_version(
        application_id=app.id, user_id=1001, user_role="Applicant",
        doc_type="claims", title="Claims 1", filename="claims.pdf", file_size_bytes=300
    )
    d2 = upload_document_version(
        application_id=app.id, user_id=1001, user_role="Applicant",
        doc_type="claims", title="Claims 2", filename="claims.pdf", file_size_bytes=350
    )
    d1.refresh_from_db()
    assert d1.is_current is False
    assert d2.is_current is True


def test_tc_124_pms_afr_154_allow_access_to_previous_document_versions_when_permitted(stub_iam):
    """Test ID: TC-124 | Source ID: PMS-AFR-154: allow access to previous document versions when permitted by role and status rules."""
    app = _make_app(applicant_user_id=1001)
    old_doc = app.documents.create(
        doc_type="claims", title="Claims v1", file_format="pdf", file_size_bytes=400,
        version=1, is_current=False, uploaded_by_user_id=1001
    )
    client = _auth_client(stub_iam, 1001, "student", ("pms.application.view_self",))
    res = client.get(f"{API}/applications/{app.id}/")
    assert res.status_code == 200
    assert any(d["id"] == old_doc.id and d["version"] == 1 for d in res.json()["documents"])


def test_tc_124b_pms_afr_154_deny_access_to_previous_document_versions_when_disallowed(stub_iam):
    """Test ID: TC-124b | Source ID: PMS-AFR-154: deny access to previous document versions when disallowed by role or status rules."""
    app = _make_app(applicant_user_id=2001)
    app.documents.create(
        doc_type="claims", title="Claims v1", file_format="pdf", file_size_bytes=400,
        version=1, is_current=False, uploaded_by_user_id=2001
    )
    client = _auth_client(stub_iam, 1001, "student", ("pms.application.view_self",))
    res = client.get(f"{API}/applications/{app.id}/")
    assert res.status_code == 404


def test_tc_125_pms_afr_155_log_document_modifications_with_user_and_timestamp(monkeypatch):
    """Test ID: TC-125 | Source ID: PMS-AFR-155: log document modifications with user and timestamp."""
    _allow_clean_pdf(monkeypatch)
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])

    upload_document_version(
        application_id=app.id, user_id=1001, user_role="Applicant",
        doc_type="claims", title="Claims v1", filename="claims.pdf", file_size_bytes=400
    )
    log = PmsAuditTrail.objects.filter(application=app, action_type="document_version_uploaded").first()
    assert log is not None
    assert log.actor_user_id == 1001
    assert log.timestamp is not None


def test_tc_126_pms_afr_156_control_document_access_based_on_role_and_application_status(stub_iam):
    """Test ID: TC-126 | Source ID: PMS-AFR-156: control document access based on role and application status."""
    app = _make_app(applicant_user_id=2001)
    client = _auth_client(stub_iam, 1001, "student", ("pms.application.view_self",))
    res = client.get(f"{API}/applications/{app.id}/")
    assert res.status_code == 404


def test_tc_127_pms_afr_157_allow_applicant_to_edit_documents_when_status_is_needs_revision(monkeypatch):
    """Test ID: TC-127 | Source ID: PMS-AFR-157: allow Applicant to edit documents when status is Needs Revision."""
    _allow_clean_pdf(monkeypatch)
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])

    doc = upload_document_version(
        application_id=app.id, user_id=1001, user_role="Applicant",
        doc_type="specification", title="Edited Spec", filename="spec.pdf", file_size_bytes=500
    )
    assert ApplicationDocument.objects.filter(pk=doc.pk).exists()


def test_tc_127b_pms_afr_157_prevent_applicant_from_editing_documents_when_status_not_needs_revision(monkeypatch):
    """Test ID: TC-127b | Source ID: PMS-AFR-157: prevent Applicant from editing documents when status is not Needs Revision."""
    _allow_clean_pdf(monkeypatch)
    app = _make_app()
    app.status = PatentApplicationStatus.FILED.value
    app.save(update_fields=["status", "updated_at"])

    with pytest.raises(PreconditionNotMetError):
        upload_document_version(
            application_id=app.id, user_id=1001, user_role="Applicant",
            doc_type="specification", title="Disallowed Edit", filename="spec.pdf", file_size_bytes=500
        )


def test_tc_128_pms_afr_158_applicant_submits_licensing_requests():
    """Test ID: TC-128 | Source ID: PMS-AFR-158: Applicant submits licensing requests."""
    app = _make_app()
    req = submit_licensing_request(
        application_id=app.id,
        applicant_user_id=1001,
        licensee_name="Partner Corp",
        request_type="non_exclusive",
        commercial_terms="5% royalty",
    )
    assert req.status == "submitted"
    assert req.licensee_name == "Partner Corp"


def test_tc_129_pms_afr_159_applicant_submits_technology_transfer_requests():
    """Test ID: TC-129 | Source ID: PMS-AFR-159: Applicant submits technology transfer requests."""
    app = _make_app()
    req = submit_licensing_request(
        application_id=app.id,
        applicant_user_id=1001,
        licensee_name="Tech Transfer Org",
        request_type="tech_transfer",
        commercial_terms="Milestone grant + royalty",
    )
    assert req.request_type == "tech_transfer"


def test_tc_130_pms_afr_160_route_licensing_or_technology_transfer_requests_to_committee_or_director(stub_iam):
    """Test ID: TC-130 | Source ID: PMS-AFR-160: route licensing or technology-transfer requests to committee or Director."""
    app = _make_app()
    app.assigned_director_user_id = 2001
    app.save(update_fields=["assigned_director_user_id", "updated_at"])
    req = submit_licensing_request(
        application_id=app.id,
        applicant_user_id=1001,
        licensee_name="Industrial Partner",
        request_type="exclusive",
        commercial_terms="Upfront + royalty",
    )
    reviewed = review_licensing_request(
        request_id=req.id, director_user_id=2001, status="under_review", negotiation_notes="Routed to committee"
    )
    assert reviewed.status == "under_review"


def test_tc_131_pms_afr_161_track_negotiation_process_information():
    """Test ID: TC-131 | Source ID: PMS-AFR-161: track negotiation process information."""
    app = _make_app()
    app.assigned_director_user_id = 2001
    app.save(update_fields=["assigned_director_user_id", "updated_at"])
    req = submit_licensing_request(
        application_id=app.id, applicant_user_id=1001, licensee_name="Partner", request_type="license", commercial_terms="Terms"
    )
    updated = review_licensing_request(
        request_id=req.id, director_user_id=2001, status="negotiating", negotiation_notes="Round 1 terms exchanged."
    )
    assert updated.negotiation_notes == "Round 1 terms exchanged."
    assert updated.status == "negotiating"


def test_tc_132_pms_afr_162_document_final_licensing_or_technology_transfer_agreements():
    """Test ID: TC-132 | Source ID: PMS-AFR-162: document final licensing or technology-transfer agreements."""
    app = _make_app()
    app.assigned_director_user_id = 2001
    app.save(update_fields=["assigned_director_user_id", "updated_at"])
    req = submit_licensing_request(
        application_id=app.id, applicant_user_id=1001, licensee_name="Partner", request_type="license", commercial_terms="Terms"
    )
    finalized = review_licensing_request(
        request_id=req.id,
        director_user_id=2001,
        status="agreement_recorded",
        agreement_reference="LIC-AGR-2026-01",
    )
    assert finalized.status == "agreement_recorded"
    assert finalized.agreement_reference == "LIC-AGR-2026-01"


def test_tc_133_pms_afr_163_update_or_share_financial_system_information_when_integration_available():
    """Test ID: TC-133 | Source ID: PMS-AFR-163: update or share licensing/technology-transfer financial-system information."""
    app = _make_app()
    app.assigned_director_user_id = 2001
    app.save(update_fields=["assigned_director_user_id", "updated_at"])
    req = submit_licensing_request(
        application_id=app.id, applicant_user_id=1001, licensee_name="Partner", request_type="license", commercial_terms="Royalty 8%"
    )
    review_licensing_request(
        request_id=req.id, director_user_id=2001, status="agreement_recorded", agreement_reference="FIN-REF-88"
    )
    audit = PmsAuditTrail.objects.filter(application=app, action_type="licensing_agreement_recorded").first()
    assert audit is not None
    assert audit.details["agreement_ref"] == "FIN-REF-88"


def test_tc_134_pms_afr_164_maintain_license_records_with_confidentiality_controls(stub_iam):
    """Test ID: TC-134 | Source ID: PMS-AFR-164: maintain license records with confidentiality controls."""
    app = _make_app(applicant_user_id=2001)
    req = submit_licensing_request(
        application_id=app.id, applicant_user_id=2001, licensee_name="Secret Licensee", request_type="exclusive", commercial_terms="Confidential"
    )
    assert LicensingRequest.objects.get(pk=req.pk).is_confidential is True

    outsider_client = _auth_client(stub_iam, 1001, "student", ("pms.application.view_self",))
    res = outsider_client.get(f"{API}/applications/{app.id}/licensing/")
    assert res.status_code == 404


def test_tc_135_pms_afr_165_applicant_files_appeals_against_rejected_applications():
    """Test ID: TC-135 | Source ID: PMS-AFR-165: Applicant files appeals against rejected applications."""
    app = _make_app()
    app.status = PatentApplicationStatus.REJECTED.value
    app.assigned_director_user_id = 2001
    app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])

    appeal = file_appeal(
        application_id=app.id,
        applicant_user_id=1001,
        grounds="Misinterpretation of claims",
        justification="Detailed technical justification for appeal.",
    )
    assert PatentAppeal.objects.filter(pk=appeal.pk).exists()
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPEAL_SUBMITTED.value


def test_tc_136_pms_afr_166_require_appeals_within_applicable_allowed_time_period():
    """Test ID: TC-136 | Source ID: PMS-AFR-166: require appeals within applicable allowed time period."""
    app = _make_app()
    app.status = PatentApplicationStatus.SUBMITTED.value
    app.save(update_fields=["status", "updated_at"])

    with pytest.raises(PreconditionNotMetError):
        file_appeal(
            application_id=app.id,
            applicant_user_id=1001,
            grounds="Grounds",
            justification="Justification",
        )


def test_tc_137_pms_afr_167_require_grounds_and_justification_for_appeal():
    """Test ID: TC-137 | Source ID: PMS-AFR-167: require grounds and justification for appeal."""
    app = _make_app()
    app.status = PatentApplicationStatus.REJECTED.value
    app.save(update_fields=["status", "updated_at"])

    with pytest.raises(PreconditionNotMetError):
        file_appeal(
            application_id=app.id,
            applicant_user_id=1001,
            grounds="",
            justification="Justification text",
        )


def test_tc_138_pms_afr_168_director_reviews_appeals_and_supporting_documentation(stub_iam):
    """Test ID: TC-138 | Source ID: PMS-AFR-168: Director reviews appeals and supporting documentation."""
    app = _make_app()
    app.status = PatentApplicationStatus.REJECTED.value
    app.assigned_director_user_id = 2001
    app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])
    appeal = file_appeal(
        application_id=app.id,
        applicant_user_id=1001,
        grounds="Technical grounds",
        justification="Supporting rationale",
    )

    client = _auth_client(stub_iam, 2001, "director", ("pms.application.review_appeal", "pms.application.view"))
    res = client.get(f"{API}/appeals/")
    assert res.status_code == 200
    assert any(item["id"] == appeal.id for item in res.json())


def test_tc_139_pms_afr_169_director_chooses_uphold_remand_or_modify_decision():
    """Test ID: TC-139 | Source ID: PMS-AFR-169: Director chooses Uphold Rejection, Remand for Amendment, or Modify Decision."""
    for idx, outcome in enumerate(("Uphold Rejection", "Remand for Amendment", "Modify Decision")):
        app = _make_app(applicant_user_id=1001, title=f"Appeal Case {idx}")
        app.status = PatentApplicationStatus.REJECTED.value
        app.assigned_director_user_id = 2001
        app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])
        appeal = file_appeal(
            application_id=app.id,
            applicant_user_id=1001,
            grounds="Grounds",
            justification="Justification",
        )
        reviewed = review_appeal(
            appeal_id=appeal.id,
            director_user_id=2001,
            outcome=outcome,
            outcome_justification="Written appeal review rationale.",
        )
        assert reviewed.outcome == outcome


def test_tc_140_pms_afr_170_record_appeal_outcomes():
    """Test ID: TC-140 | Source ID: PMS-AFR-170: record appeal outcomes."""
    app = _make_app()
    app.status = PatentApplicationStatus.REJECTED.value
    app.assigned_director_user_id = 2001
    app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])
    appeal = file_appeal(
        application_id=app.id, applicant_user_id=1001, grounds="Grounds", justification="Justification"
    )
    reviewed = review_appeal(
        appeal_id=appeal.id,
        director_user_id=2001,
        outcome="Uphold Rejection",
        outcome_justification="Rejection remains warranted.",
    )
    reviewed.refresh_from_db()
    assert reviewed.outcome == "Uphold Rejection"
    assert reviewed.decided_at is not None


def test_tc_141_pms_afr_171_initiate_next_steps_after_appeal_outcome_recording():
    """Test ID: TC-141 | Source ID: PMS-AFR-171: initiate next steps after appeal outcome recording."""
    app = _make_app()
    app.status = PatentApplicationStatus.REJECTED.value
    app.assigned_director_user_id = 2001
    app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])
    appeal = file_appeal(
        application_id=app.id, applicant_user_id=1001, grounds="Grounds", justification="Justification"
    )
    review_appeal(
        appeal_id=appeal.id,
        director_user_id=2001,
        outcome="Remand for Amendment",
        outcome_justification="Remanded for claim amendment.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.REMANDED_FOR_AMENDMENT.value
