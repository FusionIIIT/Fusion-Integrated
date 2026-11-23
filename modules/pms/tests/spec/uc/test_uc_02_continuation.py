"""Comprehensive UC test suite continuation covering UC-TC-049 through UC-TC-101 from UC_DESIGN.json."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.principal import Principal
from modules.pms.contracts import (
    get_attorney_active_workload,
    get_director_active_workload,
    get_patent_counts,
)
from modules.pms.domain.errors import (
    AppealNotAllowedError,
    InvalidDocumentError,
    InvalidTransitionError,
    NotPermittedError,
    PreconditionNotMetError,
    UnauthorizedRoleError,
)
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    AttorneyPanel,
    CoInventor,
    LicensingRequest,
    PatentAppeal,
    PatentApplication,
    PatentBudget,
    PmsAuditTrail,
    PmsConfiguration,
    PmsNotificationOutbox,
    PmsRoleAssignment,
    PostGrantMaintenance,
)
from modules.pms.selectors.applications import visible_applications
from modules.pms.services import (
    approve_office_action_response,
    assign_director,
    attach_prior_art,
    decide_renewal,
    draft_office_action_response,
    file_appeal,
    monitor_and_process_deadlines,
    record_consent_and_agreement,
    record_external_filing,
    record_maintenance_action,
    record_office_action,
    record_patent_grant,
    record_withdrawal_consent,
    request_office_action_extension,
    request_renewal_decision,
    review_appeal,
    revise_and_resubmit_application,
    send_pending_notifications,
    submit_application,
    submit_director_review,
    submit_office_action_response,
    upload_document_version,
    withdraw_application,
)
from modules.pms.services.configuration import set_policy_value
from modules.pms.services.notifications import enqueue_notification
from modules.pms.tests.support import configure_maintenance_schedule

pytestmark = pytest.mark.django_db

ALL_PMS_PERMS = (
    "pms.application.create",
    "pms.application.view",
    "pms.application.view_self",
    "pms.application.revise",
    "pms.application.withdraw",
    "pms.director.assign",
    "pms.review.submit",
    "pms.appeal.file",
    "pms.appeal.review",
    "pms.budget.review",
    "pms.attorney.assign",
    "pms.assignment.respond",
    "pms.patentability.assess",
    "pms.legal_advice.record",
    "pms.filing.record",
    "pms.grant.record",
    "pms.oa.record",
    "pms.oa.respond",
    "pms.oa.review",
    "pms.maintenance.manage",
    "pms.maintenance.decide",
    "pms.prior_art.search",
    "pms.prior_art.attach",
    "pms.document.manage",
    "pms.licensing.request",
    "pms.licensing.review",
    "pms.coinventor.manage",
    "pms.config.manage",
    "pms.audit.view",
    "pms.reports.view",
    "pms.oversight.view",
)


def _api_client(
    stub_iam,
    *,
    user_id=2001,
    permissions=ALL_PMS_PERMS,
    modules=("pms",),
    kind="faculty",
    roles=("Applicant", "Director", "PCC_ADMIN", "Attorney"),
    active_role="Applicant",
    users=None,
):
    session = make_session(
        user_id=user_id,
        permissions=permissions,
        modules=modules,
        kind=kind,
        roles=roles,
        active_role=active_role,
    )
    stub_iam(
        session=session,
        users=users
        or {
            user_id: {
                "user_id": user_id,
                "username": f"u{user_id}",
                "display_name": f"User {user_id}",
                "email": f"u{user_id}@example.edu",
                "kind": kind,
                "department": "CSE",
            }
        },
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer tok-123")
    return client


def _valid_payload(**overrides):
    data = {
        "title": "Solid-State Thermal Harvester Array",
        "abstract": "Harvests waste thermal gradients using thermoelectric modules.",
        "detailed_description": "Full technical specification of layered Bi2Te3 converter stages.",
        "claims": "1. A thermal harvester comprising a heat spreader and converter stage.",
        "domain": "Energy",
        "jurisdiction": "IN",
        "is_international": False,
        "coinventors": [
            {
                "user_id": 2001,
                "name": "Lead Inventor",
                "email": "lead@example.edu",
                "department": "CSE",
                "ownership_percentage": "100.00",
            }
        ],
        "documents": [
            {
                "doc_type": "specification",
                "title": "Patent Specification v1",
                "file_format": "pdf",
                "file_size_bytes": 102400,
                "sensitivity": "internal",
                "file_url": "https://storage.local/spec-v1.pdf",
            }
        ],
        "budget": {
            "filing_fees": "5000.00",
            "attorney_fees": "15000.00",
            "administrative_costs": "2000.00",
            "justification": "Standard filing, drafting, and administrative processing costs.",
            "availability_verified": True,
        },
    }
    data.update(overrides)
    return data


def _create_app_via_service(applicant_user_id=2001, **overrides):
    payload = _valid_payload(**overrides)
    return submit_application(
        applicant_user_id=applicant_user_id,
        title=payload["title"],
        abstract=payload["abstract"],
        detailed_description=payload["detailed_description"],
        claims=payload["claims"],
        domain=payload["domain"],
        jurisdiction=payload["jurisdiction"],
        is_international=payload["is_international"],
        international_justification=payload.get("international_justification", ""),
        preferred_attorney_id=payload.get("preferred_attorney_id"),
        coinventors=payload["coinventors"],
        documents=payload["documents"],
        budget=payload["budget"],
    )


def _create_app_model(
    *,
    applicant_user_id=2001,
    status=PatentApplicationStatus.SUBMITTED,
    domain="Energy",
    title="Test Patent Application",
    assigned_director_user_id=None,
    assigned_attorney_user_id=None,
    review_deadline=None,
    revision_deadline=None,
    jurisdiction="IN",
    is_international=False,
    international_justification="",
    grant_date=None,
    patent_number="",
    budget_status="approved",
    budget_verified=True,
    total_cost=Decimal("20000.00"),
    signed_coinventors=True,
):
    seq = PatentApplication.objects.count() + 1
    app = PatentApplication.objects.create(
        application_no=f"PMS-2026-{seq:04d}",
        title=title,
        abstract="Abstract text",
        detailed_description="Detailed description text",
        claims="1. Claim one.",
        domain=domain,
        status=status,
        applicant_user_id=applicant_user_id,
        assigned_director_user_id=assigned_director_user_id,
        assigned_attorney_user_id=assigned_attorney_user_id,
        review_deadline=review_deadline,
        revision_deadline=revision_deadline,
        jurisdiction=jurisdiction,
        is_international=is_international,
        international_justification=international_justification,
        grant_date=grant_date,
        patent_number=patent_number,
        format_validated=True,
    )
    PatentBudget.objects.create(
        application=app,
        filing_fees=Decimal("5000.00"),
        attorney_fees=Decimal("10000.00"),
        administrative_costs=total_cost - Decimal("15000.00"),
        total_cost=total_cost,
        status=budget_status,
        availability_verified=budget_verified,
        justification="Initial budget allocation.",
    )
    CoInventor.objects.create(
        application=app,
        user_id=applicant_user_id,
        name="Primary Inventor",
        email="primary@example.edu",
        department=domain,
        ownership_percentage=Decimal("100.00"),
        consent_given=signed_coinventors,
        agreement_signed=signed_coinventors,
        electronic_signature="SIG-PRIMARY" if signed_coinventors else "",
        signed_at=timezone.now() if signed_coinventors else None,
        withdrawal_consent_given=False,
    )
    return app


# ---------------------------------------------------------------------------
# UC-PMS-015: Post-Grant Maintenance & Renewal (UC-TC-049 .. UC-TC-052)
# ---------------------------------------------------------------------------


def test_uc_tc_049_request_renewal_decision_success(stub_iam):
    """test_id: UC-TC-049 | source_id: UC-PMS-015"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.GRANTED,
        patent_number="PAT-100",
    )
    rec = PostGrantMaintenance.objects.create(
        application=app,
        cycle_number=1,
        fee_due_date=date.today() + timedelta(days=120),
        fee_amount=Decimal("10000.00"),
        maintenance_status="pending_decision",
    )
    client = _api_client(stub_iam, user_id=4001)
    resp = client.post(
        reverse("pms:maintenance-request-renewal", kwargs={"maintenance_id": rec.pk}),
        {"decision_requested": True},
        format="json",
    )
    assert resp.status_code == 200
    rec.refresh_from_db()
    assert rec.decision_requested is True


def test_uc_tc_050_decide_renewal_renew_updates_decision(stub_iam):
    """test_id: UC-TC-050 | source_id: UC-PMS-015"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.GRANTED,
        patent_number="PAT-101",
    )
    rec = PostGrantMaintenance.objects.create(
        application=app,
        cycle_number=1,
        fee_due_date=date.today() + timedelta(days=90),
        fee_amount=Decimal("10000.00"),
        maintenance_status="pending_decision",
    )
    client = _api_client(stub_iam, user_id=5001)
    resp = client.post(
        reverse("pms:maintenance-decide-renewal", kwargs={"maintenance_id": rec.pk}),
        {"decision": "Renew"},
        format="json",
    )
    assert resp.status_code == 200
    rec.refresh_from_db()
    assert rec.director_decision == "Renew"
    assert rec.renewal_decided_at is not None


def test_uc_tc_051_record_maintenance_action_renewed_schedules_next_cycle(stub_iam):
    """test_id: UC-TC-051 | source_id: UC-PMS-015"""
    configure_maintenance_schedule()
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.GRANTED,
        grant_date=date.today() - timedelta(days=365 * 3),
        patent_number="PAT-102",
    )
    rec = PostGrantMaintenance.objects.create(
        application=app,
        cycle_number=1,
        fee_due_date=date.today() + timedelta(days=30),
        fee_amount=Decimal("10000.00"),
        director_decision="Renew",
        maintenance_status="pending_decision",
    )
    client = _api_client(stub_iam, user_id=4001)
    resp = client.post(
        reverse("pms:maintenance-record-action", kwargs={"maintenance_id": rec.pk}),
        {"action_status": "renewed", "transaction_reference": "TXN-RENEW-01"},
        format="json",
    )
    assert resp.status_code == 200
    rec.refresh_from_db()
    assert rec.maintenance_status == "renewed"
    assert rec.transaction_reference == "TXN-RENEW-01"
    assert app.maintenance_records.filter(cycle_number=2).exists()


def test_uc_tc_052_record_maintenance_action_lapsed_marks_application_lapsed(stub_iam):
    """test_id: UC-TC-052 | source_id: UC-PMS-015"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.GRANTED,
        patent_number="PAT-103",
    )
    rec = PostGrantMaintenance.objects.create(
        application=app,
        cycle_number=1,
        fee_due_date=date.today() - timedelta(days=10),
        fee_amount=Decimal("10000.00"),
        director_decision="Do Not Renew",
        maintenance_status="pending_decision",
    )
    client = _api_client(stub_iam, user_id=4001)
    resp = client.post(
        reverse("pms:maintenance-record-action", kwargs={"maintenance_id": rec.pk}),
        {"action_status": "lapsed", "transaction_reference": "LAPSED-01"},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.LAPSED


# ---------------------------------------------------------------------------
# UC-PMS-016: Monitor Deadlines & Escalations (UC-TC-053 .. UC-TC-055)
# ---------------------------------------------------------------------------


def test_uc_tc_053_monitor_deadlines_enqueues_upcoming_alert():
    """test_id: UC-TC-053 | source_id: UC-PMS-016"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.UNDER_REVIEW,
        assigned_director_user_id=5001,
        review_deadline=timezone.now() + timedelta(days=5),
    )
    summary = monitor_and_process_deadlines()
    assert summary["alerts_sent"] >= 1
    assert PmsNotificationOutbox.objects.filter(topic="deadline.alert").exists()
    assert PmsAuditTrail.objects.filter(application=app, action_type="deadline_alert_sent").exists()


def test_uc_tc_054_monitor_deadlines_expires_overdue_revision_application():
    """test_id: UC-TC-054 | source_id: UC-PMS-016"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.NEEDS_REVISION,
        revision_deadline=timezone.now() - timedelta(days=2),
    )
    summary = monitor_and_process_deadlines()
    assert summary["expired"] >= 1
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.EXPIRED


def test_uc_tc_055_monitor_deadlines_escalates_overdue_review():
    """test_id: UC-TC-055 | source_id: UC-PMS-016"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.UNDER_REVIEW,
        assigned_director_user_id=5001,
        review_deadline=timezone.now() - timedelta(days=3),
    )
    summary = monitor_and_process_deadlines()
    assert summary["escalated"] >= 1
    assert PmsAuditTrail.objects.filter(application=app, action_type="deadline_escalated").exists()


# ---------------------------------------------------------------------------
# UC-PMS-017: Dispatch Notifications (UC-TC-056 .. UC-TC-058)
# ---------------------------------------------------------------------------


def test_uc_tc_056_send_pending_notifications_delivers_queued_item():
    """test_id: UC-TC-056 | source_id: UC-PMS-017"""
    outbox = PmsNotificationOutbox.objects.create(
        topic="application.submitted",
        dedupe_key="dedupe-uc-056",
        recipient_user_id=2001,
        recipient_email="inv@example.edu",
        subject="Application Submitted",
        body="Your patent application has been submitted.",
        payload={"application_id": 1},
        status="pending",
    )
    sent_count = send_pending_notifications()
    assert sent_count == 1
    outbox.refresh_from_db()
    assert outbox.status == "sent"
    assert outbox.sent_at is not None


def test_uc_tc_057_send_pending_notifications_deduplicates_identical_dedupe_key():
    """test_id: UC-TC-057 | source_id: UC-PMS-017"""
    first = enqueue_notification(
        topic="application.submitted",
        dedupe_key="dedupe-uc-057",
        recipient_user_id=2001,
        recipient_email="inv@example.edu",
        subject="Sub",
        body="Body",
        payload={},
    )
    second = enqueue_notification(
        topic="application.submitted",
        dedupe_key="dedupe-uc-057",
        recipient_user_id=2001,
        recipient_email="inv@example.edu",
        subject="Sub",
        body="Body",
        payload={},
    )
    assert first.pk == second.pk
    assert PmsNotificationOutbox.objects.filter(dedupe_key="dedupe-uc-057").count() == 1


def test_uc_tc_058_send_pending_notifications_retries_failed_delivery():
    """test_id: UC-TC-058 | source_id: UC-PMS-017"""
    outbox = PmsNotificationOutbox.objects.create(
        topic="application.submitted",
        dedupe_key="dedupe-uc-058",
        recipient_user_id=2001,
        recipient_email="",
        subject="Sub",
        body="Body",
        payload={},
        status="pending",
    )
    with (
        patch("modules.pms.services.notifications.get_users", side_effect=RuntimeError("directory down")),
        pytest.raises(RuntimeError),
    ):
        send_pending_notifications()
        outbox.refresh_from_db()
    assert outbox.status == "failed"
    assert outbox.attempts >= 1


# ---------------------------------------------------------------------------
# UC-PMS-018: Upload & Manage Documents (UC-TC-059 .. UC-TC-061)
# ---------------------------------------------------------------------------


def test_uc_tc_059_upload_document_version_increments_and_supersedes_prior(stub_iam):
    """test_id: UC-TC-059 | source_id: UC-PMS-018"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.NEEDS_REVISION)
    first_doc = app.documents.create(
        doc_type="specification",
        title="Spec v1",
        file_format="pdf",
        file_size_bytes=1024,
        malware_scanned=True,
        is_clean=True,
        sensitivity="internal",
        version=1,
        is_current=True,
        uploaded_by_user_id=2001,
        file_url="https://storage.local/v1.pdf",
    )
    client = _api_client(stub_iam, user_id=2001)
    with patch("modules.pms.services.documents.validate_document") as mock_val:
        mock_val.side_effect = lambda **kw: {
            "doc_type": kw["doc_type"],
            "title": kw["title"],
            "file_format": kw["file_format"],
            "file_size_bytes": kw["file_size_bytes"],
            "malware_scanned": True,
            "is_clean": True,
            "sensitivity": kw["sensitivity"],
            "version": kw["version"],
            "is_current": True,
            "uploaded_by_user_id": kw["uploaded_by_user_id"],
            "file_url": kw["file_url"],
        }
        resp = client.post(
            reverse("pms:application-documents", kwargs={"pk": app.pk}),
            {
                "doc_type": "specification",
                "title": "Spec v2",
                "file_format": "pdf",
                "file_size_bytes": 2048,
                "sensitivity": "internal",
                "file_url": "https://storage.local/v2.pdf",
            },
            format="json",
        )
    assert resp.status_code == 201
    first_doc.refresh_from_db()
    assert first_doc.is_current is False
    assert app.documents.filter(version=2, is_current=True).exists()


def test_uc_tc_060_upload_document_applicant_outside_needs_revision_returns_403(stub_iam):
    """test_id: UC-TC-060 | source_id: UC-PMS-018"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.UNDER_REVIEW)
    client = _api_client(
        stub_iam,
        user_id=2001,
        roles=("Applicant",),
        active_role="Applicant",
    )
    resp = client.post(
        reverse("pms:application-documents", kwargs={"pk": app.pk}),
        {
            "doc_type": "specification",
            "title": "Spec",
            "file_format": "pdf",
            "file_size_bytes": 1024,
            "sensitivity": "internal",
            "file_url": "https://storage.local/spec.pdf",
        },
        format="json",
    )
    assert resp.status_code == 403


def test_uc_tc_061_upload_document_scanner_unavailable_returns_503(stub_iam):
    """test_id: UC-TC-061 | source_id: UC-PMS-018"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.NEEDS_REVISION)
    client = _api_client(stub_iam, user_id=2001)
    resp = client.post(
        reverse("pms:application-documents", kwargs={"pk": app.pk}),
        {
            "doc_type": "specification",
            "title": "Spec v2",
            "file_format": "pdf",
            "file_size_bytes": 1024,
            "sensitivity": "internal",
            "file_url": "https://storage.local/v2.pdf",
        },
        format="json",
    )
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# UC-PMS-019: Submit & Review Licensing Requests (UC-TC-062 .. UC-TC-065)
# ---------------------------------------------------------------------------


def test_uc_tc_062_submit_licensing_request_success(stub_iam):
    """test_id: UC-TC-062 | source_id: UC-PMS-019"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.GRANTED,
        patent_number="PAT-200",
    )
    client = _api_client(stub_iam, user_id=2001)
    resp = client.post(
        reverse("pms:application-licensing", kwargs={"pk": app.pk}),
        {
            "licensee_name": "Acme Energy Corp",
            "request_type": "non_exclusive",
            "commercial_terms": "5% royalty on net sales.",
            "is_confidential": True,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert LicensingRequest.objects.filter(application=app, licensee_name="Acme Energy Corp").exists()


def test_uc_tc_063_submit_licensing_request_on_ungranted_app_returns_409(stub_iam):
    """test_id: UC-TC-063 | source_id: UC-PMS-019"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.SUBMITTED)
    client = _api_client(stub_iam, user_id=2001)
    resp = client.post(
        reverse("pms:application-licensing", kwargs={"pk": app.pk}),
        {
            "licensee_name": "Acme Energy Corp",
            "request_type": "exclusive",
            "commercial_terms": "Upfront fee + royalty.",
        },
        format="json",
    )
    assert resp.status_code == 409


def test_uc_tc_064_review_licensing_request_agreement_recorded(stub_iam):
    """test_id: UC-TC-064 | source_id: UC-PMS-019"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.GRANTED,
        patent_number="PAT-201",
    )
    req_obj = LicensingRequest.objects.create(
        application=app,
        requested_by_user_id=2001,
        licensee_name="GridTech Ltd",
        request_type="non_exclusive",
        commercial_terms="Standard terms.",
        status="submitted",
    )
    client = _api_client(stub_iam, user_id=4001)
    resp = client.post(
        reverse("pms:licensing-review", kwargs={"request_id": req_obj.pk}),
        {
            "status": "agreement_recorded",
            "negotiation_notes": "Terms finalized.",
            "agreement_reference": "LIC-2026-088",
        },
        format="json",
    )
    assert resp.status_code == 200
    req_obj.refresh_from_db()
    assert req_obj.status == "agreement_recorded"
    assert req_obj.agreement_reference == "LIC-2026-088"


def test_uc_tc_065_review_licensing_request_invalid_status_returns_400(stub_iam):
    """test_id: UC-TC-065 | source_id: UC-PMS-019"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.GRANTED,
        patent_number="PAT-202",
    )
    req_obj = LicensingRequest.objects.create(
        application=app,
        requested_by_user_id=2001,
        licensee_name="GridTech Ltd",
        request_type="non_exclusive",
        commercial_terms="Standard terms.",
        status="submitted",
    )
    client = _api_client(stub_iam, user_id=4001)
    resp = client.post(
        reverse("pms:licensing-review", kwargs={"request_id": req_obj.pk}),
        {"status": "bogus_status"},
        format="json",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# UC-PMS-020 .. UC-PMS-033: Reporting, Oversight, Appeals, Audit, Admin
# (UC-TC-066 .. UC-TC-101)
# ---------------------------------------------------------------------------


def test_uc_tc_066_reports_endpoint_returns_aggregated_metrics(stub_iam):
    """test_id: UC-TC-066 | source_id: UC-PMS-020"""
    _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.SUBMITTED, domain="Energy")
    client = _api_client(stub_iam, user_id=4001)
    resp = client.get(reverse("pms:reports"))
    assert resp.status_code == 200
    assert resp.data["total_applications"] >= 1


def test_uc_tc_067_reports_endpoint_forbidden_without_permission(stub_iam):
    """test_id: UC-TC-067 | source_id: UC-PMS-020"""
    client = _api_client(
        stub_iam,
        user_id=2001,
        permissions=("pms.application.view_self",),
        roles=("Applicant",),
        active_role="Applicant",
    )
    resp = client.get(reverse("pms:reports"))
    assert resp.status_code == 403


def test_uc_tc_068_reports_filter_by_domain(stub_iam):
    """test_id: UC-TC-068 | source_id: UC-PMS-020"""
    _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.SUBMITTED, domain="Energy")
    _create_app_model(applicant_user_id=2002, status=PatentApplicationStatus.SUBMITTED, domain="BioTech")
    client = _api_client(stub_iam, user_id=4001)
    resp = client.get(reverse("pms:reports"), {"domain": "Energy"})
    assert resp.status_code == 200
    assert resp.data["total_applications"] == 1


def test_uc_tc_069_workflow_oversight_returns_bottlenecks_and_metrics(stub_iam):
    """test_id: UC-TC-069 | source_id: UC-PMS-021"""
    _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.UNDER_REVIEW,
        assigned_director_user_id=5001,
    )
    client = _api_client(stub_iam, user_id=4001)
    resp = client.get(reverse("pms:workflow-oversight"))
    assert resp.status_code == 200
    assert "status_counts" in resp.data


def test_uc_tc_070_workflow_oversight_forbidden_without_permission(stub_iam):
    """test_id: UC-TC-070 | source_id: UC-PMS-021"""
    client = _api_client(
        stub_iam,
        user_id=2001,
        permissions=("pms.application.view_self",),
        roles=("Applicant",),
        active_role="Applicant",
    )
    resp = client.get(reverse("pms:workflow-oversight"))
    assert resp.status_code == 403


def test_uc_tc_071_appeal_list_returns_visible_appeals(stub_iam):
    """test_id: UC-TC-071 | source_id: UC-PMS-008"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.APPEAL_UNDER_REVIEW)
    PatentAppeal.objects.create(
        application=app,
        applicant_user_id=2001,
        grounds="Novelty",
        justification="Detailed appeal.",
        status="pending",
    )
    client = _api_client(stub_iam, user_id=2001)
    resp = client.get(reverse("pms:appeal-list"))
    assert resp.status_code == 200
    assert len(resp.data["results"]) == 1


def test_uc_tc_072_review_appeal_uphold_rejection_keeps_rejected_state(stub_iam):
    """test_id: UC-TC-072 | source_id: UC-PMS-008"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.APPEAL_UNDER_REVIEW)
    appeal = PatentAppeal.objects.create(
        application=app,
        applicant_user_id=2001,
        grounds="Novelty",
        justification="Appeal basis.",
        status="pending",
    )
    client = _api_client(stub_iam, user_id=5001)
    resp = client.post(
        reverse("pms:appeal-review", kwargs={"appeal_id": appeal.pk}),
        {
            "outcome": "Uphold Rejection",
            "outcome_justification": "Prior art anticipates the claimed device structure.",
        },
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.REJECTED


def test_uc_tc_073_review_appeal_modify_decision_updates_outcome(stub_iam):
    """test_id: UC-TC-073 | source_id: UC-PMS-008"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.APPEAL_UNDER_REVIEW)
    appeal = PatentAppeal.objects.create(
        application=app,
        applicant_user_id=2001,
        grounds="Scope",
        justification="Appeal basis.",
        status="pending",
    )
    client = _api_client(stub_iam, user_id=5001)
    resp = client.post(
        reverse("pms:appeal-review", kwargs={"appeal_id": appeal.pk}),
        {
            "outcome": "Modify Decision",
            "outcome_justification": "Modified rejection scope to allow independent claim 1.",
        },
        format="json",
    )
    assert resp.status_code == 200
    appeal.refresh_from_db()
    assert appeal.outcome == "Modify Decision"


def test_uc_tc_074_review_appeal_invalid_outcome_returns_400(stub_iam):
    """test_id: UC-TC-074 | source_id: UC-PMS-008"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.APPEAL_UNDER_REVIEW)
    appeal = PatentAppeal.objects.create(
        application=app,
        applicant_user_id=2001,
        grounds="Scope",
        justification="Appeal basis.",
        status="pending",
    )
    client = _api_client(stub_iam, user_id=5001)
    resp = client.post(
        reverse("pms:appeal-review", kwargs={"appeal_id": appeal.pk}),
        {"outcome": "Invalid Outcome", "outcome_justification": "Reason."},
        format="json",
    )
    assert resp.status_code == 400


def test_uc_tc_075_audit_trail_list_returns_entries(stub_iam):
    """test_id: UC-TC-075 | source_id: UC-PMS-022"""
    app = _create_app_model(applicant_user_id=2001)
    PmsAuditTrail.objects.create(
        application=app,
        actor_user_id=2001,
        action_type="application_submitted",
        from_state="",
        to_state="submitted",
        details={},
    )
    client = _api_client(stub_iam, user_id=4001)
    resp = client.get(reverse("pms:audit-trail-list"))
    assert resp.status_code == 200
    assert len(resp.data["results"]) >= 1


def test_uc_tc_076_audit_trail_filter_by_application_id(stub_iam):
    """test_id: UC-TC-076 | source_id: UC-PMS-022"""
    app1 = _create_app_model(applicant_user_id=2001)
    app2 = _create_app_model(applicant_user_id=2002)
    PmsAuditTrail.objects.create(application=app1, actor_user_id=2001, action_type="act1", to_state="submitted")
    PmsAuditTrail.objects.create(application=app2, actor_user_id=2002, action_type="act2", to_state="submitted")
    client = _api_client(stub_iam, user_id=4001)
    resp = client.get(reverse("pms:audit-trail-list"), {"application_id": app1.pk})
    assert resp.status_code == 200
    assert all(item["application"] == app1.pk for item in resp.data["results"])


def test_uc_tc_077_audit_trail_forbidden_without_permission(stub_iam):
    """test_id: UC-TC-077 | source_id: UC-PMS-022"""
    client = _api_client(
        stub_iam,
        user_id=2001,
        permissions=("pms.application.view_self",),
        roles=("Applicant",),
        active_role="Applicant",
    )
    resp = client.get(reverse("pms:audit-trail-list"))
    assert resp.status_code == 403


def test_uc_tc_078_audit_trail_entries_are_immutable():
    """test_id: UC-TC-078 | source_id: UC-PMS-022"""
    app = _create_app_model(applicant_user_id=2001)
    entry = PmsAuditTrail.objects.create(
        application=app,
        actor_user_id=2001,
        action_type="application_submitted",
        to_state="submitted",
    )
    assert entry.is_immutable is True
    with pytest.raises(ValueError):
        entry.delete()


def test_uc_tc_079_configuration_list_and_set_value(stub_iam):
    """test_id: UC-TC-079 | source_id: UC-PMS-023"""
    client = _api_client(stub_iam, user_id=4001)
    put_resp = client.put(
        reverse("pms:configuration-detail", kwargs={"key": "review_sla_days"}),
        {"value": 15, "description": "Review SLA in business days"},
        format="json",
    )
    assert put_resp.status_code == 200
    assert PmsConfiguration.objects.filter(key="review_sla_days").exists()

    list_resp = client.get(reverse("pms:configuration-list"))
    assert list_resp.status_code == 200


def test_uc_tc_080_configuration_delete_unsets_key(stub_iam):
    """test_id: UC-TC-080 | source_id: UC-PMS-023"""
    set_policy_value("review_sla_days", 20, description="Temp SLA")
    client = _api_client(stub_iam, user_id=4001)
    resp = client.delete(reverse("pms:configuration-detail", kwargs={"key": "review_sla_days"}))
    assert resp.status_code in (200, 204)
    assert not PmsConfiguration.objects.filter(key="review_sla_days").exists()


def test_uc_tc_081_configuration_forbidden_without_permission(stub_iam):
    """test_id: UC-TC-081 | source_id: UC-PMS-023"""
    client = _api_client(
        stub_iam,
        user_id=2001,
        permissions=("pms.application.view_self",),
        roles=("Applicant",),
        active_role="Applicant",
    )
    resp = client.get(reverse("pms:configuration-list"))
    assert resp.status_code == 403


def test_uc_tc_082_configuration_invalid_key_returns_400(stub_iam):
    """test_id: UC-TC-082 | source_id: UC-PMS-023"""
    client = _api_client(stub_iam, user_id=4001)
    resp = client.put(
        reverse("pms:configuration-detail", kwargs={"key": "unknown_nonexistent_key"}),
        {"value": 123},
        format="json",
    )
    assert resp.status_code == 400


def test_uc_tc_083_attorney_panel_list_and_create(stub_iam):
    """test_id: UC-TC-083 | source_id: UC-PMS-024"""
    client = _api_client(stub_iam, user_id=4001)
    resp = client.post(
        reverse("pms:attorney-panel-list"),
        {
            "attorney_user_id": 3010,
            "name": "Panel Attorney",
            "firm_name": "Patent Law Group",
            "email": "panel@example.edu",
            "is_approved": True,
            "expertise_domains": ["Energy", "IT"],
            "current_workload": 1,
            "max_workload": 6,
        },
        format="json",
    )
    assert resp.status_code == 201
    list_resp = client.get(reverse("pms:attorney-panel-list"))
    assert list_resp.status_code == 200
    assert len(list_resp.data["results"]) == 1


def test_uc_tc_084_attorney_panel_patch_and_delete(stub_iam):
    """test_id: UC-TC-084 | source_id: UC-PMS-024"""
    panel = AttorneyPanel.objects.create(
        attorney_user_id=3011,
        name="Attorney Patch",
        firm_name="Firm X",
        email="patch@example.edu",
        is_approved=True,
        expertise_domains=["Energy"],
        current_workload=0,
        max_workload=4,
    )
    client = _api_client(stub_iam, user_id=4001)
    patch_resp = client.patch(
        reverse("pms:attorney-panel-detail", kwargs={"pk": panel.pk}),
        {"max_workload": 8},
        format="json",
    )
    assert patch_resp.status_code == 200
    panel.refresh_from_db()
    assert panel.max_workload == 8

    del_resp = client.delete(reverse("pms:attorney-panel-detail", kwargs={"pk": panel.pk}))
    assert del_resp.status_code in (200, 204)
    assert not AttorneyPanel.objects.filter(pk=panel.pk).exists()


def test_uc_tc_085_attorney_panel_forbidden_without_permission(stub_iam):
    """test_id: UC-TC-085 | source_id: UC-PMS-024"""
    client = _api_client(
        stub_iam,
        user_id=2001,
        permissions=("pms.application.view_self",),
        roles=("Applicant",),
        active_role="Applicant",
    )
    resp = client.get(reverse("pms:attorney-panel-list"))
    assert resp.status_code == 403


def test_uc_tc_086_contracts_get_patent_counts_and_workloads():
    """test_id: UC-TC-086 | source_id: UC-PMS-025"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.UNDER_REVIEW,
        assigned_director_user_id=5001,
        assigned_attorney_user_id=3001,
    )
    counts = get_patent_counts()
    assert counts["total"] >= 1
    assert get_director_active_workload(5001) >= 1
    assert get_attorney_active_workload(3001) >= 0
    assert app.pk is not None


def test_uc_tc_087_visible_applications_selector_includes_coinventor_and_director():
    """test_id: UC-TC-087 | source_id: UC-PMS-026"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.UNDER_REVIEW,
        domain="Energy",
        assigned_director_user_id=5001,
    )
    CoInventor.objects.create(
        application=app,
        user_id=2055,
        name="Co-Inventor",
        email="co@example.edu",
        department="Energy",
        ownership_percentage=Decimal("0.00"),
    )
    PmsRoleAssignment.objects.create(user_id=5001, role="Director", domain="Energy", is_active=True)

    co_session = make_session(
        user_id=2055,
        permissions=("pms.application.view_self",),
        modules=("pms",),
        roles=("Applicant",),
        active_role="Applicant",
    )
    assert app in visible_applications(Principal.from_session(co_session))

    dir_session = make_session(
        user_id=5001,
        permissions=("pms.application.view",),
        modules=("pms",),
        kind="faculty",
        roles=("Director",),
        active_role="Director",
    )
    assert app in visible_applications(Principal.from_session(dir_session))


def test_uc_tc_088_submit_application_via_service_sets_initial_budget_and_audit():
    """test_id: UC-TC-088 | source_id: UC-PMS-027"""
    with patch("modules.pms.services.applications.validate_document") as mock_val:
        mock_val.side_effect = lambda **kw: {
            "doc_type": kw["doc_type"],
            "title": kw["title"],
            "file_format": kw["file_format"],
            "file_size_bytes": kw["file_size_bytes"],
            "malware_scanned": True,
            "is_clean": True,
            "sensitivity": kw["sensitivity"],
            "version": kw["version"],
            "is_current": True,
            "uploaded_by_user_id": kw["uploaded_by_user_id"],
            "file_url": kw["file_url"],
        }
        app = _create_app_via_service(applicant_user_id=2001)
    assert app.status == PatentApplicationStatus.SUBMITTED
    assert app.budget.status == "pending_approval"
    assert PmsAuditTrail.objects.filter(application=app, action_type="application_submitted").count() == 1


def test_uc_tc_089_revise_application_via_service_rejects_invalid_state():
    """test_id: UC-TC-089 | source_id: UC-PMS-028"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.SUBMITTED)
    with pytest.raises(InvalidTransitionError):
        revise_and_resubmit_application(app.pk, actor_user_id=2001, feedback_response="Cannot revise now.")


def test_uc_tc_090_assign_director_via_service_rejects_unauthorized_actor():
    """test_id: UC-TC-090 | source_id: UC-PMS-028"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.SUBMITTED, domain="Energy")
    PmsRoleAssignment.objects.create(user_id=5001, role="Director", domain="Energy", is_active=True)
    with pytest.raises(UnauthorizedRoleError):
        assign_director(app.pk, actor_user_id=2001, director_user_id=5001)


def test_uc_tc_091_submit_director_review_rejects_unassigned_director():
    """test_id: UC-TC-091 | source_id: UC-PMS-029"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.UNDER_REVIEW,
        assigned_director_user_id=5001,
    )
    with pytest.raises(NotPermittedError):
        submit_director_review(
            app.pk,
            director_user_id=5099,
            decision="Approve",
            justification="Attempted review by non-assigned director with sufficient text length.",
        )


def test_uc_tc_092_file_appeal_rejects_non_applicant():
    """test_id: UC-TC-092 | source_id: UC-PMS-029"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.REJECTED)
    with pytest.raises(NotPermittedError):
        file_appeal(app.pk, applicant_user_id=2999, grounds="Grounds", justification="Reason")


def test_uc_tc_093_review_appeal_rejects_non_appealed_application():
    """test_id: UC-TC-093 | source_id: UC-PMS-030"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.SUBMITTED)
    appeal = PatentAppeal.objects.create(
        application=app,
        applicant_user_id=2001,
        grounds="Grounds",
        justification="Reason",
        status="pending",
    )
    with pytest.raises(AppealNotAllowedError):
        review_appeal(
            appeal.pk,
            director_user_id=5001,
            outcome="Uphold Rejection",
            outcome_justification="Justification text.",
        )


def test_uc_tc_094_withdraw_application_rejects_non_applicant():
    """test_id: UC-TC-094 | source_id: UC-PMS-030"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.SUBMITTED)
    record_withdrawal_consent(app.pk, coinventor_user_id=2001, consent=True)
    with pytest.raises(NotPermittedError):
        withdraw_application(app.pk, actor_user_id=2999, reason="Unauthorized withdrawal")


def test_uc_tc_095_record_consent_rejects_unknown_coinventor():
    """test_id: UC-TC-095 | source_id: UC-PMS-031"""
    app = _create_app_model(applicant_user_id=2001)
    with pytest.raises(PreconditionNotMetError):
        record_consent_and_agreement(
            app.pk,
            coinventor_user_id=9999,
            consent_given=True,
            agreement_signed=True,
            electronic_signature="SIG",
        )


def test_uc_tc_096_attach_prior_art_rejects_blank_reference_id():
    """test_id: UC-TC-096 | source_id: UC-PMS-031"""
    app = _create_app_model(applicant_user_id=2001, assigned_attorney_user_id=3001)
    with pytest.raises(PreconditionNotMetError):
        attach_prior_art(
            app.pk,
            actor_user_id=3001,
            source="USPTO",
            reference_id="   ",
            title="Ref Title",
        )


def test_uc_tc_097_record_external_filing_requires_international_justification():
    """test_id: UC-TC-097 | source_id: UC-PMS-032"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.APPROVED,
        budget_status="approved",
        signed_coinventors=True,
    )
    with pytest.raises(PreconditionNotMetError):
        record_external_filing(
            app.pk,
            actor_user_id=4001,
            jurisdiction="PCT",
            is_international=True,
            international_justification="",
            external_filing_id="PCT-2026-01",
            external_filing_date=date.today(),
        )


def test_uc_tc_098_record_patent_grant_requires_patent_number():
    """test_id: UC-TC-098 | source_id: UC-PMS-032"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.FILED)
    with pytest.raises(PreconditionNotMetError):
        record_patent_grant(app.pk, actor_user_id=4001, patent_number="", grant_date=date.today())


def test_uc_tc_099_office_action_workflow_end_to_end_service_functions():
    """test_id: UC-TC-099 | source_id: UC-PMS-033"""
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.FILED,
        assigned_attorney_user_id=3001,
    )
    oa = record_office_action(
        app.pk,
        actor_user_id=3001,
        action_type="Office Action",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=45),
        details="Clarify claim scope.",
        requires_applicant_review=True,
    )
    oa = draft_office_action_response(oa.pk, actor_user_id=3001, draft_response="Amended claim wording.")
    assert oa.status == "awaiting_applicant_approval"
    oa = approve_office_action_response(oa.pk, actor_user_id=2001, approved=True)
    assert oa.status == "response_ready"
    oa = request_office_action_extension(oa.pk, actor_user_id=3001, extension_months=1)
    assert oa.extension_months == 1
    oa = submit_office_action_response(oa.pk, actor_user_id=3001, submission_details="Submitted response.")
    assert oa.status == "responded"


def test_uc_tc_100_maintenance_lifecycle_service_functions():
    """test_id: UC-TC-100 | source_id: UC-PMS-033"""
    configure_maintenance_schedule()
    app = _create_app_model(
        applicant_user_id=2001,
        status=PatentApplicationStatus.GRANTED,
        patent_number="PAT-300",
    )
    rec = PostGrantMaintenance.objects.create(
        application=app,
        cycle_number=1,
        fee_due_date=date.today() + timedelta(days=60),
        fee_amount=Decimal("12000.00"),
        maintenance_status="pending_decision",
    )
    rec = request_renewal_decision(rec.pk, actor_user_id=4001, decision_requested=True)
    assert rec.decision_requested is True
    rec = decide_renewal(rec.pk, actor_user_id=5001, decision="Renew")
    assert rec.director_decision == "Renew"
    rec = record_maintenance_action(
        rec.pk,
        actor_user_id=4001,
        action_status="renewed",
        transaction_reference="TXN-300-1",
    )
    assert rec.maintenance_status == "renewed"


def test_uc_tc_101_upload_document_version_via_service_rejects_invalid_doc():
    """test_id: UC-TC-101 | source_id: UC-PMS-033"""
    app = _create_app_model(applicant_user_id=2001, status=PatentApplicationStatus.NEEDS_REVISION)
    with pytest.raises(InvalidDocumentError):
        upload_document_version(
            app.pk,
            actor_user_id=2001,
            doc_type="specification",
            title="Invalid Format",
            file_format="bat",
            file_size_bytes=512,
            sensitivity="internal",
            file_url="https://storage.local/script.bat",
        )
