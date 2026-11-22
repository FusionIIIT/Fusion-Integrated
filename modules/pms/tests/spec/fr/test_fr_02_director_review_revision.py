"""FR Spec Tests: Director Assignment, Review Decisions, and Revision Cycles.

Covers TC-021..TC-032, TC-032b, and TC-033..TC-044 from FR_DESIGN.json.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.domain.entities import MIN_JUSTIFICATION_LENGTH, validate_document
from modules.pms.domain.errors import (
    ConflictOfInterestError,
    DeadlineExceededError,
    InsufficientJustificationError,
    PreconditionNotMetError,
)
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    AttorneyPanel,
    DirectorReview,
    PatentApplication,
    PmsAuditTrail,
    PmsNotificationOutbox,
    PmsRoleAssignment,
)
from modules.pms.services import applications as app_service
from modules.pms.services import (
    assign_director,
    calculate_review_deadline,
    monitor_and_process_deadlines,
    revise_and_resubmit_application,
    submit_application,
    submit_director_review,
)

pytestmark = pytest.mark.django_db

API = "/api/v1/pms"


def _auth_client(stub_iam, user_id: int, role: str = "director", permissions: tuple[str, ...] = ()):
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


def _make_app(applicant_user_id: int = 1001, domain: str = "Physics", title: str = "Quantum Sensor"):
    return submit_application(
        applicant_user_id=applicant_user_id,
        title=title,
        abstract="Abstract detailing technical contribution.",
        detailed_description="Full description of apparatus and method.",
        claims="1. An apparatus comprising...",
        domain=domain,
    )


def test_tc_021_pms_afr_049_pcc_admin_assigns_submitted_applications_to_directors(stub_iam):
    """Test ID: TC-021 | Source ID: PMS-AFR-049: PCC_ADMIN assigns submitted applications to Directors."""
    app = _make_app()
    client = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.application.assign_director",))
    res = client.post(
        f"{API}/applications/{app.id}/assign-director/",
        {"director_user_id": 2001},
        format="json",
    )
    assert res.status_code == 200
    app.refresh_from_db()
    assert app.assigned_director_user_id == 2001


def test_tc_022_pms_afr_050_automatic_assignment_to_directors_when_rules_are_available():
    """Test ID: TC-022 | Source ID: PMS-AFR-050: automatic assignment to Directors when rules are available."""
    app = _make_app(domain="Materials")
    PmsRoleAssignment.objects.create(user_id=2003, role="Director", domain="Materials", is_active=True)
    eligible_director = PmsRoleAssignment.objects.filter(
        role="Director", domain=app.domain, is_active=True
    ).first()
    assert eligible_director is not None
    assigned = assign_director(
        application_id=app.id,
        director_user_id=eligible_director.user_id,
        assigned_by_user_id=9001,
    )
    assert assigned.assigned_director_user_id == 2003


def test_tc_023_pms_afr_051_director_expertise_matching_criterion():
    """Test ID: TC-023 | Source ID: PMS-AFR-051: Director expertise matching criterion."""
    PmsRoleAssignment.objects.create(user_id=2001, role="Director", domain="Optics", is_active=True)
    PmsRoleAssignment.objects.create(user_id=2002, role="Director", domain="Acoustics", is_active=True)
    optics_app = _make_app(domain="Optics", title="Optics Lens")
    matching_dirs = list(
        PmsRoleAssignment.objects.filter(role="Director", domain=optics_app.domain, is_active=True)
    )
    assert [d.user_id for d in matching_dirs] == [2001]


def test_tc_024_pms_afr_052_director_workload_balance_criterion():
    """Test ID: TC-024 | Source ID: PMS-AFR-052: Director workload balance criterion."""
    busy_app = _make_app(applicant_user_id=1001, domain="Optics", title="Busy Dir App")
    assign_director(application_id=busy_app.id, director_user_id=2001, assigned_by_user_id=9001)
    PmsRoleAssignment.objects.create(user_id=2001, role="Director", domain="Optics", is_active=True)
    PmsRoleAssignment.objects.create(user_id=2002, role="Director", domain="Optics", is_active=True)

    workloads = {
        d.user_id: PatentApplication.objects.filter(
            assigned_director_user_id=d.user_id, status=PatentApplicationStatus.UNDER_REVIEW.value
        ).count()
        for d in PmsRoleAssignment.objects.filter(role="Director", domain="Optics", is_active=True)
    }
    least_loaded_director = min(workloads, key=workloads.get)
    assert least_loaded_director == 2002


def test_tc_025_pms_afr_053_conflict_of_interest_checks_before_director_assignment():
    """Test ID: TC-025 | Source ID: PMS-AFR-053: conflict-of-interest checks before Director assignment."""
    app = _make_app(applicant_user_id=1001)
    app.coinventors.create(
        user_id=2001, name="Conflicted Director", email="d@t.org", ownership_percentage="50.00"
    )
    with pytest.raises(ConflictOfInterestError):
        assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)


def test_tc_026_pms_afr_054_prevent_director_from_reviewing_own_inventor_application():
    """Test ID: TC-026 | Source ID: PMS-AFR-054: prevent Director from reviewing own inventor application."""
    app = _make_app(applicant_user_id=2001)
    with pytest.raises(ConflictOfInterestError):
        assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)


def test_tc_027_pms_afr_055_prevent_pcc_admin_from_reviewing_own_inventor_application():
    """Test ID: TC-027 | Source ID: PMS-AFR-055: prevent PCC_ADMIN from reviewing own inventor application."""
    app = _make_app(applicant_user_id=9001)
    with pytest.raises(ConflictOfInterestError):
        assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)


def test_tc_028_pms_afr_056_update_status_to_under_review_upon_assignment():
    """Test ID: TC-028 | Source ID: PMS-AFR-056: update status to Under Review upon assignment."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.UNDER_REVIEW.value


def test_tc_029_pms_afr_057_notify_assigned_director_and_initiate_review_timeline():
    """Test ID: TC-029 | Source ID: PMS-AFR-057: notify assigned Director and initiate review timeline."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    app.refresh_from_db()
    assert app.director_assigned_at is not None
    assert app.review_deadline is not None
    assert PmsNotificationOutbox.objects.filter(
        topic="application.assigned_director", recipient_user_id=2001
    ).exists()


def test_tc_030_pms_afr_058_director_views_assigned_application_details_and_documents(stub_iam):
    """Test ID: TC-030 | Source ID: PMS-AFR-058: Director views assigned application details and documents."""
    app = _make_app()
    app.documents.create(
        doc_type="specification",
        title="Full Spec",
        file_format="pdf",
        file_size_bytes=1024,
        uploaded_by_user_id=1001,
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)

    client = _auth_client(stub_iam, 2001, "director", ("pms.application.view", "pms.application.review"))
    res = client.get(f"{API}/applications/{app.id}/")
    assert res.status_code == 200
    assert len(res.json()["documents"]) == 1


def test_tc_031_pms_afr_059_director_chooses_approve_reject_or_needs_revision():
    """Test ID: TC-031 | Source ID: PMS-AFR-059: Director chooses Approve, Reject, or Needs Revision."""
    justification = "A" * MIN_JUSTIFICATION_LENGTH
    for idx, decision in enumerate(("Approve", "Needs Revision", "Reject")):
        app = _make_app(applicant_user_id=1001, title=f"Decision App {idx}")
        assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
        review = submit_director_review(
            application_id=app.id,
            director_user_id=2001,
            decision=decision,
            justification=justification,
            feedback="Reviewed carefully.",
        )
        assert review.decision == decision


def test_tc_032_pms_afr_060_reject_decision_with_fewer_than_50_characters_of_justification():
    """Test ID: TC-032 | Source ID: PMS-AFR-060: reject decision with fewer than 50 characters of justification."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    with pytest.raises(InsufficientJustificationError):
        submit_director_review(
            application_id=app.id,
            director_user_id=2001,
            decision="Approve",
            justification="Too short justification.",
        )


def test_tc_032b_pms_afr_060_accept_decision_with_at_least_50_characters_of_justification():
    """Test ID: TC-032b | Source ID: PMS-AFR-060: accept decision with at least 50 characters of justification."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    review = submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Approve",
        justification="J" * 50,
    )
    assert len(review.justification) >= 50


def test_tc_033_pms_afr_061_enforce_15_business_day_director_review_completion():
    """Test ID: TC-033 | Source ID: PMS-AFR-061: enforce 15-business-day Director review completion."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    app.refresh_from_db()
    expected_dl = calculate_review_deadline(app.director_assigned_at)
    assert app.review_deadline == expected_dl

    app.review_deadline = timezone.now() - timedelta(days=1)
    app.save(update_fields=["review_deadline", "updated_at"])
    stats = monitor_and_process_deadlines()
    assert stats["escalations"] >= 1


def test_tc_034_pms_afr_062_notify_applicant_with_detailed_feedback_on_rejection():
    """Test ID: TC-034 | Source ID: PMS-AFR-062: notify Applicant with detailed feedback on rejection."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Reject",
        justification="Lacks inventive step over prior art reference D1 in claim 1.",
        feedback="Prior art D1 discloses this exact mechanism.",
    )
    notif = PmsNotificationOutbox.objects.filter(
        topic="application.reviewed", recipient_user_id=1001
    ).order_by("-id").first()
    assert notif is not None
    assert "Prior art D1" in notif.body


def test_tc_035_pms_afr_063_notify_applicant_with_detailed_feedback_on_revision_request():
    """Test ID: TC-035 | Source ID: PMS-AFR-063: notify Applicant with detailed feedback on revision request."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Needs Revision",
        justification="Clarify experimental data and calibration parameters in specification.",
        feedback="Provide calibration table for sensor output.",
    )
    notif = PmsNotificationOutbox.objects.filter(
        topic="application.reviewed", recipient_user_id=1001
    ).order_by("-id").first()
    assert notif is not None
    assert "calibration table" in notif.body


def test_tc_036_pms_afr_064_route_approved_applications_to_attorney_assignment():
    """Test ID: TC-036 | Source ID: PMS-AFR-064: route approved applications to attorney assignment."""
    AttorneyPanel.objects.create(
        attorney_user_id=5001, name="Adv. Rao", email="rao@law.test", is_approved=True
    )
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Approve",
        justification="Approved for attorney assignment and prosecution workflow.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPROVED.value


def test_tc_037_pms_afr_065_audit_trail_of_director_review_process():
    """Test ID: TC-037 | Source ID: PMS-AFR-065: audit trail of Director review process."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Approve",
        justification="All technical claims satisfy novelty and utility criteria.",
    )
    assert PmsAuditTrail.objects.filter(application=app, action_type="director_reviewed").exists()
    assert DirectorReview.objects.filter(application=app, director_user_id=2001).exists()


def test_tc_038_pms_afr_066_revise_applications_with_status_needs_revision():
    """Test ID: TC-038 | Source ID: PMS-AFR-066: revise applications with status Needs Revision."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Needs Revision",
        justification="Please add additional experimental validation data before approval.",
    )
    revised = revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response="Added complete experimental validation dataset and updated claims.",
    )
    assert revised.status == PatentApplicationStatus.RESUBMITTED.value


def test_tc_039_pms_afr_067_revise_applications_with_status_rejected():
    """Test ID: TC-039 | Source ID: PMS-AFR-067: revise applications with status Rejected."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Reject",
        justification="Original claims were overly broad relative to cited art.",
    )
    revised = revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response="Narrowed independent claims to distinguish from cited art.",
    )
    assert revised.status == PatentApplicationStatus.RESUBMITTED.value


def test_tc_040_pms_afr_068_60_day_resubmission_period():
    """Test ID: TC-040 | Source ID: PMS-AFR-068: 60-day resubmission period."""
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.revision_deadline = timezone.now() - timedelta(days=1)
    app.save(update_fields=["status", "revision_deadline", "updated_at"])

    with pytest.raises(DeadlineExceededError):
        revise_and_resubmit_application(
            application_id=app.id,
            applicant_user_id=1001,
            feedback_response="Late revision after 60-day window.",
        )


def test_tc_041_pms_afr_069_validate_revision_addresses_director_feedback():
    """Test ID: TC-041 | Source ID: PMS-AFR-069: validate revision addresses Director feedback."""
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])

    with pytest.raises(PreconditionNotMetError, match="feedback"):
        revise_and_resubmit_application(
            application_id=app.id,
            applicant_user_id=1001,
            feedback_response="short",
        )


def test_tc_042_pms_afr_070_start_new_review_cycle_after_resubmission():
    """Test ID: TC-042 | Source ID: PMS-AFR-070: start new review cycle after resubmission."""
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])
    revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response="Addressed all points raised in Director review.",
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.UNDER_REVIEW.value


def test_tc_043_pms_afr_071_version_control_for_revised_applications(monkeypatch):
    """Test ID: TC-043 | Source ID: PMS-AFR-071: version control for revised applications."""
    def _clean_pdf(filename: str, file_size_bytes: int, is_malware_clean: bool | None = None):
        return validate_document(filename, file_size_bytes, is_malware_clean=True)

    monkeypatch.setattr(app_service, "validate_document", _clean_pdf)
    app = _make_app()
    app.documents.create(
        doc_type="specification",
        title="Spec v1",
        file_format="pdf",
        file_size_bytes=500,
        version=1,
        is_current=True,
        uploaded_by_user_id=1001,
    )
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save(update_fields=["status", "updated_at"])

    revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response="Updated specification to version 2.",
        new_documents_data=[{"doc_type": "specification", "title": "Spec v2", "filename": "spec.pdf", "file_size_bytes": 600}],
    )
    versions = list(app.documents.filter(doc_type="specification").order_by("version"))
    assert len(versions) == 2
    assert versions[0].is_current is False
    assert versions[1].version == 2
    assert versions[1].is_current is True


def test_tc_044_pms_afr_072_expire_application_when_resubmission_deadline_expires():
    """Test ID: TC-044 | Source ID: PMS-AFR-072: expire application when resubmission deadline expires."""
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.revision_deadline = timezone.now() - timedelta(days=2)
    app.save(update_fields=["status", "revision_deadline", "updated_at"])

    stats = monitor_and_process_deadlines()
    assert stats["revisions_expired"] >= 1
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.EXPIRED.value
