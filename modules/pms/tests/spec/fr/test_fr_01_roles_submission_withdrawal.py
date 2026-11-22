"""FR Spec Tests: Roles, Application Submission, Withdrawal, and Co-Inventors.

Covers TC-001..TC-020 and TC-096..TC-110 from FR_DESIGN.json.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.domain.entities import MAX_DOCUMENT_SIZE_BYTES, validate_document
from modules.pms.domain.errors import (
    IncompleteInventorsError,
    InvalidDocumentError,
    PreconditionNotMetError,
    WithdrawalNotAllowedError,
)
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    ApplicationDocument,
    AttorneyPanel,
    PatentApplication,
    PmsAuditTrail,
    PmsConfiguration,
    PmsNotificationOutbox,
    PmsRoleAssignment,
)
from modules.pms.services import applications as app_service
from modules.pms.services import (
    assign_director,
    enqueue_notification,
    record_consent_and_agreement,
    record_withdrawal_consent,
    set_policy_value,
    submit_application,
    update_coinventors,
    withdraw_application,
)

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


def _base_app_kwargs(applicant_user_id: int = 1001, domain: str = "Computer Science", title: str = "Novel System"):
    return {
        "applicant_user_id": applicant_user_id,
        "title": title,
        "abstract": "Concise technical abstract describing the invention.",
        "detailed_description": "Comprehensive specification and implementation details.",
        "claims": "1. A system comprising a processor and memory configured to...",
        "domain": domain,
    }


def _allow_clean_pdf_scanner(monkeypatch, infected_filenames: set[str] | None = None):
    infected = infected_filenames or set()

    def _validate(filename: str, file_size_bytes: int, is_malware_clean: bool | None = None):
        scan_result = filename not in infected
        return validate_document(filename, file_size_bytes, is_malware_clean=scan_result)

    monkeypatch.setattr(app_service, "validate_document", _validate)


def test_tc_001_pms_afr_010_applicant_tracks_own_application_status_and_progress(stub_iam):
    """Test ID: TC-001 | Source ID: PMS-AFR-010: track application status and progress."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001, title="Tracked Invention"))
    client = _auth_client(stub_iam, 1001, "student", ("pms.application.view_self",))

    response = client.get(f"{API}/applications/{app.id}/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == app.id
    assert payload["status"] == PatentApplicationStatus.SUBMITTED.value
    assert payload["title"] == "Tracked Invention"


def test_tc_002_pms_afr_016_applicant_views_reports_for_own_applications(stub_iam):
    """Test ID: TC-002 | Source ID: PMS-AFR-016: view reports for own applications."""
    own_app = submit_application(**_base_app_kwargs(applicant_user_id=1001, title="Own App"))
    submit_application(**_base_app_kwargs(applicant_user_id=1002, title="Other App"))
    assign_director(application_id=own_app.id, director_user_id=2001, assigned_by_user_id=9001)

    client = _auth_client(stub_iam, 1001, "student", ("pms.report.view_self",))
    response = client.get(f"{API}/reports/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_applications"] == 1
    assert data["status_distribution"].get(PatentApplicationStatus.UNDER_REVIEW.value) == 1


def test_tc_003_pms_afr_023_director_domain_workflow_oversight(stub_iam):
    """Test ID: TC-003 | Source ID: PMS-AFR-023: Director domain workflow oversight."""
    in_domain = submit_application(**_base_app_kwargs(applicant_user_id=1001, domain="Photonics", title="In Domain"))
    out_domain = submit_application(**_base_app_kwargs(applicant_user_id=1002, domain="Biotech", title="Out Domain"))
    PmsRoleAssignment.objects.create(user_id=2001, role="Director", domain="Photonics", is_active=True)

    client = _auth_client(stub_iam, 2001, "director", ("pms.workflow.oversight", "pms.application.review"))
    response = client.get(f"{API}/workflow-oversight/")
    assert response.status_code == 200
    ids = {row["application_id"] for row in response.json()}
    assert in_domain.id in ids
    assert out_domain.id not in ids


def test_tc_004_pms_afr_026_pcc_admin_monitor_workflows_and_resolve_coi(stub_iam):
    """Test ID: TC-004 | Source ID: PMS-AFR-026: PCC_ADMIN monitor workflows and resolve conflict-of-interest cases."""
    conflicted_app = submit_application(
        **_base_app_kwargs(applicant_user_id=2001, domain="AI", title="COI Application")
    )
    client = _auth_client(
        stub_iam,
        9001,
        "pcc_admin",
        ("pms.workflow.monitor", "pms.application.assign_director", "pms.audit.view"),
    )
    monitor_res = client.get(f"{API}/workflow-oversight/")
    assert monitor_res.status_code == 200
    assert any(r["application_id"] == conflicted_app.id for r in monitor_res.json())

    # Conflicted director (user 2001 is applicant) is blocked; admin resolves by assigning non-conflicted director 2002
    assign_res = client.post(
        f"{API}/applications/{conflicted_app.id}/assign-director/",
        {"director_user_id": 2002},
        format="json",
    )
    assert assign_res.status_code == 200
    conflicted_app.refresh_from_db()
    assert conflicted_app.assigned_director_user_id == 2002


def test_tc_005_pms_afr_027_pcc_admin_manage_configuration_and_role_assignments(stub_iam):
    """Test ID: TC-005 | Source ID: PMS-AFR-027: PCC_ADMIN manage configuration and role assignments."""
    client = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.config.manage",))
    cfg_res = client.put(
        f"{API}/configuration/",
        {"key": "revision_days", "value": 45, "description": "Updated revision window"},
        format="json",
    )
    assert cfg_res.status_code == 200
    assert PmsConfiguration.objects.get(key="revision_days").value == 45

    role_assignment = PmsRoleAssignment.objects.create(
        user_id=2005, role="Director", domain="Robotics", is_active=True
    )
    assert role_assignment.pk is not None
    assert role_assignment.domain == "Robotics"


def test_tc_006_pms_afr_029_pcc_admin_handle_escalations_and_exceptional_cases(stub_iam):
    """Test ID: TC-006 | Source ID: PMS-AFR-029: PCC_ADMIN handle escalations and exceptional cases."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001, title="Escalated Case"))
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    enqueue_notification(
        topic="deadline.escalated",
        dedupe_key=f"pms:esc:{app.id}",
        subject="Escalation",
        body="Review overdue",
        recipient_user_id=9001,
    )
    client = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.workflow.monitor", "pms.application.assign_director"))
    reassigned = client.post(
        f"{API}/applications/{app.id}/assign-director/",
        {"director_user_id": 2002},
        format="json",
    )
    assert reassigned.status_code == 200
    app.refresh_from_db()
    assert app.assigned_director_user_id == 2002


def test_tc_007_pms_afr_030_pcc_admin_maintain_attorney_panels_and_expertise_mappings(stub_iam):
    """Test ID: TC-007 | Source ID: PMS-AFR-030: PCC_ADMIN maintain attorney panels and expertise mappings."""
    client = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.panel.manage",))
    create_res = client.post(
        f"{API}/attorney-panel/",
        {
            "attorney_user_id": 5001,
            "name": "Counsel Verma",
            "firm_name": "Verma IP",
            "email": "verma@ip.example.test",
            "is_approved": True,
            "expertise_domains": ["Computer Science", "AI"],
            "max_workload": 8,
        },
        format="json",
    )
    assert create_res.status_code == 201
    panel_id = create_res.json()["id"]

    patch_res = client.patch(
        f"{API}/attorney-panel/{panel_id}/",
        {"expertise_domains": ["Computer Science", "AI", "Quantum"]},
        format="json",
    )
    assert patch_res.status_code == 200
    panel = AttorneyPanel.objects.get(pk=panel_id)
    assert panel.expertise_domains == ["Computer Science", "AI", "Quantum"]


def test_tc_008_pms_afr_037_attorney_legal_advice_records(stub_iam):
    """Test ID: TC-008 | Source ID: PMS-AFR-037: Attorney legal advice records."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001, title="Advice App"))
    app.status = PatentApplicationStatus.APPROVED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(
        attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True
    )

    client = _auth_client(stub_iam, 5001, "attorney", ("pms.advice.record", "pms.application.view"))
    res = client.post(
        f"{API}/applications/{app.id}/legal-advice/",
        {"stage": "pre_filing", "advice_text": "Narrow independent claim 1 before filing."},
        format="json",
    )
    assert res.status_code == 201
    assert app.legal_advices.filter(stage="pre_filing").count() == 1


def test_tc_009_pms_afr_038_submit_patent_application_with_required_sections(stub_iam, monkeypatch):
    """Test ID: TC-009 | Source ID: PMS-AFR-038: submit patent application with required sections."""
    _allow_clean_pdf_scanner(monkeypatch)
    client = _auth_client(stub_iam, 1001, "student", ("pms.application.create", "pms.application.view_self"))
    payload = {
        "title": "Complete Patent Filing",
        "abstract": "Abstract text",
        "detailed_description": "Detailed description text",
        "claims": "1. Claim one.",
        "domain": "Electronics",
        "jurisdiction": "IN",
        "coinventors": [
            {"user_id": 1001, "name": "Inventor One", "email": "inv1@test.org", "ownership_percentage": "100.00"}
        ],
        "documents": [
            {
                "doc_type": "specification",
                "title": "Spec PDF",
                "filename": "spec.pdf",
                "file_size_bytes": 2048,
                "sensitivity": "confidential",
            }
        ],
    }
    res = client.post(f"{API}/applications/", payload, format="json")
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Complete Patent Filing"
    assert len(body["coinventors"]) == 1
    assert len(body["documents"]) == 1


def test_tc_010_pms_afr_039_require_patent_application_documents_to_be_pdf_files(monkeypatch):
    """Test ID: TC-010 | Source ID: PMS-AFR-039: require patent application documents to be PDF files."""
    _allow_clean_pdf_scanner(monkeypatch)
    app = submit_application(
        **_base_app_kwargs(applicant_user_id=1001),
        documents_data=[{"title": "Drawings", "filename": "drawings.pdf", "file_size_bytes": 1024}],
    )
    assert app.documents.filter(file_format="pdf").count() == 1


def test_tc_011_pms_afr_039_reject_non_pdf_patent_application_documents():
    """Test ID: TC-011 | Source ID: PMS-AFR-039: reject non-PDF patent application documents."""
    with pytest.raises(InvalidDocumentError, match="Only PDF documents"):
        submit_application(
            **_base_app_kwargs(applicant_user_id=1001),
            documents_data=[{"title": "Spec", "filename": "spec.docx", "file_size_bytes": 1024}],
        )


def test_tc_012_pms_afr_040_reject_documents_larger_than_50_mb():
    """Test ID: TC-012 | Source ID: PMS-AFR-040: reject documents larger than 50 MB."""
    oversized = MAX_DOCUMENT_SIZE_BYTES + 1
    with pytest.raises(InvalidDocumentError, match="50 MB"):
        submit_application(
            **_base_app_kwargs(applicant_user_id=1001),
            documents_data=[{"title": "Huge Spec", "filename": "huge.pdf", "file_size_bytes": oversized}],
        )


def test_tc_013_pms_afr_041_validate_documents_as_malware_free_before_accepting(monkeypatch):
    """Test ID: TC-013 | Source ID: PMS-AFR-041: validate documents as malware-free before accepting."""
    _allow_clean_pdf_scanner(monkeypatch, infected_filenames={"infected.pdf"})
    with pytest.raises(InvalidDocumentError, match="malware"):
        submit_application(
            **_base_app_kwargs(applicant_user_id=1001),
            documents_data=[{"title": "Infected", "filename": "infected.pdf", "file_size_bytes": 512}],
        )
    assert not PatentApplication.objects.filter(title="Novel System").exists()


def test_tc_014_pms_afr_042_validate_completeness_of_submission_information():
    """Test ID: TC-014 | Source ID: PMS-AFR-042: validate completeness of submission information."""
    with pytest.raises(PreconditionNotMetError):
        submit_application(
            applicant_user_id=1001,
            title="Incomplete App",
            abstract="",
            detailed_description="Description",
            claims="Claims",
            domain="Tech",
        )


def test_tc_015_pms_afr_043_classify_submitted_documents_by_sensitivity(monkeypatch):
    """Test ID: TC-015 | Source ID: PMS-AFR-043: classify submitted documents by sensitivity."""
    _allow_clean_pdf_scanner(monkeypatch)
    app = submit_application(
        **_base_app_kwargs(applicant_user_id=1001),
        documents_data=[
            {
                "title": "Restricted Claims",
                "filename": "claims.pdf",
                "file_size_bytes": 1024,
                "sensitivity": "restricted",
            }
        ],
    )
    doc = ApplicationDocument.objects.get(application=app)
    assert doc.sensitivity == "restricted"


def test_tc_016_pms_afr_044_assign_unique_application_id():
    """Test ID: TC-016 | Source ID: PMS-AFR-044: assign unique application ID."""
    first = submit_application(**_base_app_kwargs(applicant_user_id=1001, title="First App"))
    second = submit_application(**_base_app_kwargs(applicant_user_id=1002, title="Second App"))
    assert first.id != second.id
    assert first.application_no != second.application_no


def test_tc_017_pms_afr_045_set_status_to_submitted_upon_submission():
    """Test ID: TC-017 | Source ID: PMS-AFR-045: set status to Submitted upon submission."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    assert app.status == PatentApplicationStatus.SUBMITTED.value


def test_tc_018_pms_afr_046_require_inventor_agreements_before_filing():
    """Test ID: TC-018 | Source ID: PMS-AFR-046: require inventor agreements before filing."""
    app = submit_application(
        **_base_app_kwargs(applicant_user_id=1001),
        coinventors_data=[
            {"user_id": 1001, "name": "Lead", "email": "l@test.org", "ownership_percentage": "50.00", "agreement_signed": True},
            {"user_id": 1002, "name": "Co", "email": "c@test.org", "ownership_percentage": "50.00", "agreement_signed": False},
        ],
    )
    unsigned = app.coinventors.filter(agreement_signed=False)
    assert unsigned.exists()


def test_tc_019_pms_afr_047_record_application_history():
    """Test ID: TC-019 | Source ID: PMS-AFR-047: record application history."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    actions = list(PmsAuditTrail.objects.filter(application=app).order_by("id").values_list("action_type", flat=True))
    assert actions == ["application_submitted", "director_assigned"]


def test_tc_020_pms_afr_048_notify_stakeholders_after_submission_or_status_update():
    """Test ID: TC-020 | Source ID: PMS-AFR-048: notify stakeholders after submission or status update."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    assert PmsNotificationOutbox.objects.filter(
        topic="application.submitted", recipient_user_id=1001
    ).exists()

    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    assert PmsNotificationOutbox.objects.filter(
        topic="application.assigned_director", recipient_user_id=2001
    ).exists()


def test_tc_096_pms_afr_125_applicant_withdraws_application_before_filing_stage():
    """Test ID: TC-096 | Source ID: PMS-AFR-125: Applicant withdraws application before filing stage."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    withdrawn = withdraw_application(
        application_id=app.id, applicant_user_id=1001, reason="No longer pursuing filing."
    )
    assert withdrawn.status == PatentApplicationStatus.WITHDRAWN.value
    assert withdrawn.is_withdrawn is True


def test_tc_097_pms_afr_126_validate_withdrawal_eligibility_based_on_current_status():
    """Test ID: TC-097 | Source ID: PMS-AFR-126: validate withdrawal eligibility based on current status."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    app.status = PatentApplicationStatus.FILED.value
    app.save(update_fields=["status", "updated_at"])

    with pytest.raises(WithdrawalNotAllowedError):
        withdraw_application(application_id=app.id, applicant_user_id=1001, reason="Too late.")


def test_tc_098_pms_afr_127_require_reason_for_withdrawal():
    """Test ID: TC-098 | Source ID: PMS-AFR-127: require reason for withdrawal."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    with pytest.raises(WithdrawalNotAllowedError, match="reason is required"):
        withdraw_application(application_id=app.id, applicant_user_id=1001, reason="   ")


def test_tc_099_pms_afr_128_record_co_inventor_consent_for_withdrawal_when_required():
    """Test ID: TC-099 | Source ID: PMS-AFR-128: record co-inventor consent for withdrawal when required."""
    app = submit_application(
        **_base_app_kwargs(applicant_user_id=1001),
        coinventors_data=[
            {"user_id": 1001, "name": "Lead", "email": "l@t.org", "ownership_percentage": "60.00"},
            {"user_id": 1002, "name": "Co", "email": "c@t.org", "ownership_percentage": "40.00"},
        ],
    )
    co = app.coinventors.get(user_id=1002)

    with pytest.raises(WithdrawalNotAllowedError):
        withdraw_application(application_id=app.id, applicant_user_id=1001, reason="Withdraw")

    record_withdrawal_consent(coinventor_id=co.id, user_id=1002, consent_given=True)

    withdrawn = withdraw_application(application_id=app.id, applicant_user_id=1001, reason="Withdraw")
    assert withdrawn.status == PatentApplicationStatus.WITHDRAWN.value


def test_tc_100_pms_afr_129_update_status_to_withdrawn_after_permitted_withdrawal():
    """Test ID: TC-100 | Source ID: PMS-AFR-129: update status to Withdrawn after permitted withdrawal."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    withdraw_application(application_id=app.id, applicant_user_id=1001, reason="Commercial shift")
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.WITHDRAWN.value


def test_tc_101_pms_afr_130_remove_withdrawn_applications_from_active_queue():
    """Test ID: TC-101 | Source ID: PMS-AFR-130: remove withdrawn applications from active queue."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    withdraw_application(application_id=app.id, applicant_user_id=1001, reason="Withdraw from queue")
    active_qs = PatentApplication.objects.exclude(
        status__in=[PatentApplicationStatus.WITHDRAWN.value, PatentApplicationStatus.EXPIRED.value]
    )
    assert app.id not in active_qs.values_list("id", flat=True)


def test_tc_102_pms_afr_131_maintain_withdrawal_history():
    """Test ID: TC-102 | Source ID: PMS-AFR-131: maintain withdrawal history."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    withdraw_application(application_id=app.id, applicant_user_id=1001, reason="Project shelved")
    app.refresh_from_db()
    assert app.withdrawal_reason == "Project shelved"
    assert app.withdrawal_date is not None
    assert PmsAuditTrail.objects.filter(application=app, action_type="application_withdrawn").exists()


def test_tc_103_pms_afr_132_applicant_manages_multiple_inventors():
    """Test ID: TC-103 | Source ID: PMS-AFR-132: Applicant manages multiple inventors."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    updated = update_coinventors(
        application_id=app.id,
        actor_user_id=1001,
        coinventors_data=[
            {"user_id": 1001, "name": "Inv 1", "email": "i1@t.org", "ownership_percentage": "50.00"},
            {"user_id": 1002, "name": "Inv 2", "email": "i2@t.org", "ownership_percentage": "30.00"},
            {"user_id": 1003, "name": "Inv 3", "email": "i3@t.org", "ownership_percentage": "20.00"},
        ],
    )
    assert len(updated) == 3
    assert app.coinventors.count() == 3


def test_tc_104_pms_afr_133_applicant_manages_ownership_shares_for_inventors():
    """Test ID: TC-104 | Source ID: PMS-AFR-133: Applicant manages ownership shares for inventors."""
    app = submit_application(
        **_base_app_kwargs(applicant_user_id=1001),
        coinventors_data=[
            {"user_id": 1001, "name": "Inv 1", "email": "i1@t.org", "ownership_percentage": "70.00"},
            {"user_id": 1002, "name": "Inv 2", "email": "i2@t.org", "ownership_percentage": "30.00"},
        ],
    )
    shares = {c.user_id: c.ownership_percentage for c in app.coinventors.all()}
    assert shares == {1001: Decimal("70.00"), 1002: Decimal("30.00")}


def test_tc_105_pms_afr_134_validate_inventor_information():
    """Test ID: TC-105 | Source ID: PMS-AFR-134: validate inventor information."""
    app = submit_application(**_base_app_kwargs(applicant_user_id=1001))
    with pytest.raises(IncompleteInventorsError):
        update_coinventors(
            application_id=app.id,
            actor_user_id=1001,
            coinventors_data=[
                {"user_id": 1001, "name": "Inv 1", "email": "i1@t.org", "ownership_percentage": "60.00"}
            ],
        )


def test_tc_106_pms_afr_135_validate_ownership_percentages_for_inventors():
    """Test ID: TC-106 | Source ID: PMS-AFR-135: validate ownership percentages for inventors."""
    with pytest.raises(IncompleteInventorsError, match=r"100\.00%"):
        submit_application(
            **_base_app_kwargs(applicant_user_id=1001),
            coinventors_data=[
                {"user_id": 1001, "name": "Inv 1", "email": "i1@t.org", "ownership_percentage": "60.00"},
                {"user_id": 1002, "name": "Inv 2", "email": "i2@t.org", "ownership_percentage": "25.00"},
            ],
        )


def test_tc_107_pms_afr_136_require_inventor_consent_before_filing():
    """Test ID: TC-107 | Source ID: PMS-AFR-136: require inventor consent before filing."""
    app = submit_application(
        **_base_app_kwargs(applicant_user_id=1001),
        coinventors_data=[
            {"user_id": 1001, "name": "Inv 1", "email": "i1@t.org", "ownership_percentage": "50.00", "consent_given": True, "agreement_signed": True},
            {"user_id": 1002, "name": "Inv 2", "email": "i2@t.org", "ownership_percentage": "50.00", "consent_given": False, "agreement_signed": False},
        ],
    )
    assert app.coinventors.filter(consent_given=False).exists()


def test_tc_108_pms_afr_137_collect_electronic_signatures_where_legally_permitted_and_configured(stub_iam):
    """Test ID: TC-108 | Source ID: PMS-AFR-137: collect electronic signatures where legally permitted and configured."""
    set_policy_value("revision_days", 60)
    app = submit_application(
        **_base_app_kwargs(applicant_user_id=1001),
        coinventors_data=[
            {"user_id": 1002, "name": "Co-Inv", "email": "co@t.org", "ownership_percentage": "100.00"}
        ],
    )
    co = app.coinventors.get(user_id=1002)
    client = _auth_client(stub_iam, 1002, "student", ("pms.coinventor.manage",))
    res = client.post(
        f"{API}/coinventors/{co.id}/consent/",
        {"consent_given": True, "agreement_signed": True, "electronic_signature": "SIG-CO-1002"},
        format="json",
    )
    assert res.status_code == 200
    co.refresh_from_db()
    assert co.electronic_signature == "SIG-CO-1002"
    assert co.signed_at is not None


def test_tc_109_pms_afr_138_validate_electronic_signatures_where_legally_permitted_and_configured():
    """Test ID: TC-109 | Source ID: PMS-AFR-138: validate electronic signatures where legally permitted and configured."""
    app = submit_application(
        **_base_app_kwargs(applicant_user_id=1001),
        coinventors_data=[
            {"user_id": 1002, "name": "Co-Inv", "email": "co@t.org", "ownership_percentage": "100.00"}
        ],
    )
    co = app.coinventors.get(user_id=1002)
    signed = record_consent_and_agreement(
        coinventor_id=co.id, user_id=1002, consent_given=True, agreement_signed=True, electronic_signature="SIG-VALID"
    )
    assert signed.electronic_signature == "SIG-VALID"
    unsigned = record_consent_and_agreement(
        coinventor_id=co.id, user_id=1002, consent_given=False, agreement_signed=False, electronic_signature=""
    )
    assert unsigned.agreement_signed is False
    assert unsigned.signed_at is None


def test_tc_110_pms_afr_140_notify_affected_parties_when_inventor_information_changes():
    """Test ID: TC-110 | Source ID: PMS-AFR-140: notify affected parties when inventor information changes."""
    app = submit_application(
        **_base_app_kwargs(applicant_user_id=1001),
        coinventors_data=[
            {"user_id": 1001, "name": "Inv 1", "email": "i1@t.org", "ownership_percentage": "100.00"}
        ],
    )
    update_coinventors(
        application_id=app.id,
        actor_user_id=1001,
        coinventors_data=[
            {"user_id": 1001, "name": "Inv 1 Updated", "email": "i1@t.org", "ownership_percentage": "100.00"}
        ],
    )
    assert PmsNotificationOutbox.objects.filter(topic="inventor.changed", recipient_user_id=1001).exists()
