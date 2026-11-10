"""Automated Backend Tests for Functional Requirements Strategy (FR: CFR + AFR).
Frozen Design: a8_design/FR_DESIGN.json
"""

from datetime import date, timedelta
import pytest
from django.utils import timezone

from modules.spacs.models import (
    SpacsApplication,
    SpacsAuditLog,
    SpacsAwardCandidate,
    SpacsAwardCycle,
    SpacsCatalogueEntry,
    SpacsCatalogueVersion,
    SpacsDocument,
    SpacsNotification,
    SpacsTask,
)
from modules.spacs.services import (
    applications as app_svc,
    audit as audit_svc,
    awards as award_svc,
    catalogue as cat_svc,
    decisions as dec_svc,
    renewals as rnw_svc,
    tasks as task_svc,
    verification as ver_svc,
)
from modules.spacs.selectors import (
    get_application_by_id,
    get_audit_trail_for_auditor,
    visible_applications_for_student,
    visible_catalogue,
)
from modules.spacs.domain.errors import (
    AuditProtectionError,
    AwardPolicyError,
    CompletenessError,
    DuplicateApplicationError,
    EligibilityError,
    RenewalEligibilityError,
    UnauthorizedActionError,
)


@pytest.fixture
def base_scheme(db):
    now = timezone.now()
    entry = cat_svc.create_catalogue_entry(
        scheme_code="FR-SCH-01",
        name="Merit Scholarship Scheme",
        scheme_type="scholarship",
        description="Merit scholarship for high-performing students",
        min_cpi=7.5,
        max_family_income=500000.0,
        required_documents=["income_cert", "grade_sheet"],
        application_window_start=now - timedelta(days=10),
        application_window_end=now + timedelta(days=20),
        renewal_allowed=True,
        renewal_window_start=now - timedelta(days=5),
        renewal_window_end=now + timedelta(days=25),
        candidate_source_method="application",
        academic_cycle="2026-27",
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version(
        scheme_code=entry.scheme_code,
        policy_approval_ref="POLICY-2026-M01",
        effective_from=date.today(),
        actor_user_id=1,
    )
    return entry


@pytest.mark.django_db
def test_fr_001(base_scheme):
    """TEST-FR-001 | AFR-SPACS-001: Browse published catalogue entries."""
    cat_svc.create_catalogue_entry(
        scheme_code="DRAFT-SCH", name="Draft Scheme", scheme_type="scholarship", created_by_user_id=1
    )
    published = visible_catalogue()
    codes = [e.scheme_code for e in published]
    assert "FR-SCH-01" in codes
    assert "DRAFT-SCH" not in codes


@pytest.mark.django_db
def test_fr_002(base_scheme):
    """TEST-FR-002 | AFR-SPACS-002: Display full details and eligibility criteria."""
    entry = SpacsCatalogueEntry.objects.get(scheme_code=base_scheme.scheme_code)
    assert entry.description == "Merit scholarship for high-performing students"
    assert float(entry.min_cpi) == 7.5
    assert float(entry.max_family_income) == 500000.0
    assert "income_cert" in entry.required_documents
    assert entry.renewal_allowed is True


@pytest.mark.django_db
def test_fr_003():
    """TEST-FR-003 | AFR-SPACS-003: Convener creates new draft catalogue entry."""
    entry = cat_svc.create_catalogue_entry(
        scheme_code="NEW-DRAFT-01",
        name="New Scheme",
        scheme_type="scholarship",
        created_by_user_id=1,
    )
    assert entry.status == "draft"
    assert entry.version == 1


@pytest.mark.django_db
def test_fr_004(base_scheme):
    """TEST-FR-004 | AFR-SPACS-004: Modifying published entry increments version."""
    updated = cat_svc.update_draft_catalogue_entry(
        scheme_code=base_scheme.scheme_code,
        actor_user_id=1,
        min_cpi=8.0,
    )
    assert updated.version == 2
    assert updated.status == "draft"
    assert SpacsCatalogueVersion.objects.filter(catalogue_entry=base_scheme, version=1).exists()


@pytest.mark.django_db
def test_fr_005():
    """TEST-FR-005 | AFR-SPACS-005: Publish catalogue version with policy provenance."""
    draft = cat_svc.create_catalogue_entry(
        scheme_code="PUB-TEST", name="Publish Test", scheme_type="scholarship", created_by_user_id=1
    )
    pub = cat_svc.publish_catalogue_version(
        scheme_code=draft.scheme_code,
        policy_approval_ref="SENATE-2026-R1",
        effective_from=date.today(),
        actor_user_id=1,
    )
    assert pub.status == "published"
    assert SpacsCatalogueVersion.objects.filter(catalogue_entry=draft, version=1).exists()


@pytest.mark.django_db
def test_fr_005_neg():
    """TEST-FR-005-NEG | AFR-SPACS-005: Missing policy approval reference raises error."""
    draft = cat_svc.create_catalogue_entry(
        scheme_code="PUB-NEG", name="Publish Neg", scheme_type="scholarship", created_by_user_id=1
    )
    with pytest.raises(AwardPolicyError):
        cat_svc.publish_catalogue_version(
            scheme_code=draft.scheme_code,
            policy_approval_ref="",
            effective_from=date.today(),
            actor_user_id=1,
        )


@pytest.mark.django_db
def test_fr_006(base_scheme):
    """TEST-FR-006 | AFR-SPACS-006: Convener retires catalogue entry prospectively."""
    retired = cat_svc.retire_catalogue_entry(base_scheme.scheme_code, actor_user_id=1)
    assert retired.status == "retired"


@pytest.mark.django_db
def test_fr_007(base_scheme):
    """TEST-FR-007 | AFR-SPACS-007: Preserve auditable version history."""
    v1 = SpacsCatalogueVersion.objects.get(catalogue_entry=base_scheme, version=1)
    assert v1.policy_approval_ref == "POLICY-2026-M01"
    assert "min_cpi" in v1.criteria_snapshot


@pytest.mark.django_db
def test_fr_008(base_scheme):
    """TEST-FR-008 | AFR-SPACS-008: Student initiates draft for open scheme."""
    app = app_svc.create_draft_application(
        scheme_code=base_scheme.scheme_code,
        applicant_user_id=101,
    )
    assert app.state == "draft"
    assert app.catalogue_entry == base_scheme


@pytest.mark.django_db
def test_fr_008_neg(db):
    """TEST-FR-008-NEG | AFR-SPACS-008: Application rejected if window is closed."""
    past = timezone.now() - timedelta(days=30)
    closed_scheme = cat_svc.create_catalogue_entry(
        scheme_code="CLOSED-SCH",
        name="Closed Scheme",
        scheme_type="scholarship",
        application_window_start=past - timedelta(days=10),
        application_window_end=past,
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version(
        scheme_code="CLOSED-SCH",
        policy_approval_ref="REF-01",
        effective_from=date.today() - timedelta(days=40),
        actor_user_id=1,
    )
    with pytest.raises(EligibilityError, match="window is closed"):
        app_svc.create_draft_application("CLOSED-SCH", applicant_user_id=101)


@pytest.mark.django_db
def test_fr_009(base_scheme):
    """TEST-FR-009 | AFR-SPACS-009: Machine-checkable eligibility rejection at submission."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=102)
    app_svc.upload_document(app.application_id, 102, "income_cert", "/docs/inc.pdf")
    app_svc.upload_document(app.application_id, 102, "grade_sheet", "/docs/grd.pdf")

    with pytest.raises(EligibilityError, match="below the required minimum"):
        app_svc.submit_application(
            application_id=app.application_id,
            acting_user_id=102,
            student_cpi=7.0,  # Required 7.5
            student_family_income=300000.0,
        )


@pytest.mark.django_db
def test_fr_010(base_scheme):
    """TEST-FR-010 | AFR-SPACS-010: Prevent duplicate active applications."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=103)
    app_svc.upload_document(app.application_id, 103, "income_cert", "/docs/inc.pdf")
    app_svc.upload_document(app.application_id, 103, "grade_sheet", "/docs/grd.pdf")
    app_svc.submit_application(app.application_id, 103, student_cpi=8.0, student_family_income=300000.0)

    with pytest.raises(DuplicateApplicationError):
        app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=103)


@pytest.mark.django_db
def test_fr_011(base_scheme):
    """TEST-FR-011 | AFR-SPACS-011: Capture required application data."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=104)
    updated = app_svc.update_draft(app.application_id, 104, {"bank_account": "11223344", "phone": "9876543210"})
    assert updated.application_data["bank_account"] == "11223344"


@pytest.mark.django_db
def test_fr_012(base_scheme):
    """TEST-FR-012 | AFR-SPACS-012: Upload supporting documents."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=105)
    doc = app_svc.upload_document(app.application_id, 105, "income_cert", "/uploads/income_105.pdf")
    assert doc.application == app
    assert doc.document_type == "income_cert"


@pytest.mark.django_db
def test_fr_013(base_scheme):
    """TEST-FR-013 | AFR-SPACS-013: Reuse valid prior uploaded documents."""
    prior_doc = SpacsDocument.objects.create(
        user_id=106,
        document_type="income_cert",
        file_path="/uploads/prior.pdf",
        valid_until=date.today() + timedelta(days=100),
    )
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=106)
    reused = app_svc.reuse_prior_document(app.application_id, 106, prior_doc.id, "income_cert")
    assert reused.file_path == prior_doc.file_path


@pytest.mark.django_db
def test_fr_014(base_scheme):
    """TEST-FR-014 | AFR-SPACS-014: Explicit draft preservation on partial inputs."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=107)
    saved = app_svc.update_draft(app.application_id, 107, {"partial_note": "work in progress"})
    assert saved.application_data["partial_note"] == "work in progress"
    assert saved.state == "draft"


@pytest.mark.django_db
def test_fr_015(base_scheme):
    """TEST-FR-015 | AFR-SPACS-015: Completeness validation at submission."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=108)
    # Upload only one of two required documents
    app_svc.upload_document(app.application_id, 108, "income_cert", "/uploads/inc.pdf")
    with pytest.raises(CompletenessError, match="grade_sheet"):
        app_svc.submit_application(app.application_id, 108, student_cpi=8.0, student_family_income=300000.0)


@pytest.mark.django_db
def test_fr_016(base_scheme):
    """TEST-FR-016 | AFR-SPACS-016: Unique ID, submission timestamp, bound version."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=109)
    app_svc.upload_document(app.application_id, 109, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 109, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 109, student_cpi=8.5, student_family_income=200000.0)

    assert sub.application_id.startswith("SPACS-APP-")
    assert sub.submitted_at is not None
    assert sub.catalogue_version == base_scheme.version


@pytest.mark.django_db
def test_fr_017(base_scheme):
    """TEST-FR-017 | AFR-SPACS-017: Transition to Submitted and create verification task."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=110)
    app_svc.upload_document(app.application_id, 110, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 110, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 110, student_cpi=8.0, student_family_income=250000.0)

    assert sub.state == "submitted"
    assert SpacsTask.objects.filter(entity_id=sub.application_id, assigned_role="spacs_assistant").exists()


@pytest.mark.django_db
def test_fr_018(base_scheme):
    """TEST-FR-018 | AFR-SPACS-018: Lifecycle notification on submission."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=111)
    app_svc.upload_document(app.application_id, 111, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 111, "grade_sheet", "/uploads/grd.pdf")
    app_svc.submit_application(app.application_id, 111, student_cpi=8.0, student_family_income=250000.0)

    assert SpacsNotification.objects.filter(recipient_user_id=111, event_type="submitted").exists()


@pytest.mark.django_db
def test_fr_019(base_scheme):
    """TEST-FR-019 | AFR-SPACS-019: Authorized assistant opens verification."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=112)
    app_svc.upload_document(app.application_id, 112, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 112, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 112, student_cpi=8.0, student_family_income=250000.0)

    ver = ver_svc.open_verification_task(sub.application_id, assistant_user_id=20, user_roles=["spacs_assistant"])
    assert ver.state == "under_verification"
    assert ver.verification_assigned_to_user_id == 20


@pytest.mark.django_db
def test_fr_020(base_scheme):
    """TEST-FR-020 | AFR-SPACS-020: Assistant records findings without sanction authority."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=113)
    app_svc.upload_document(app.application_id, 113, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 113, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 113, student_cpi=8.0, student_family_income=250000.0)

    ver_svc.open_verification_task(sub.application_id, assistant_user_id=20, user_roles=["spacs_assistant"])
    rec = ver_svc.record_verification_findings(
        sub.application_id, 20, ["spacs_assistant"], findings="Documents authentic", is_authenticity_confirmed=True
    )
    assert rec.verification_authenticity_confirmed is True

    # Assistant cannot approve
    with pytest.raises(UnauthorizedActionError):
        dec_svc.approve_application(sub.application_id, 20, user_roles=["spacs_assistant"])


@pytest.mark.django_db
def test_fr_021(base_scheme):
    """TEST-FR-021 | AFR-SPACS-021: Assistant returns application for correction."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=114)
    app_svc.upload_document(app.application_id, 114, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 114, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 114, student_cpi=8.0, student_family_income=250000.0)

    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    corr = ver_svc.request_correction(sub.application_id, 20, ["spacs_assistant"], reason="Income cert blurry")
    assert corr.state == "correction_required"
    assert corr.correction_reason == "Income cert blurry"


@pytest.mark.django_db
def test_fr_022(base_scheme):
    """TEST-FR-022 | AFR-SPACS-022: Student modifies application in Correction Required state."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=115)
    app_svc.upload_document(app.application_id, 115, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 115, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 115, student_cpi=8.0, student_family_income=250000.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    corr = ver_svc.request_correction(sub.application_id, 20, ["spacs_assistant"], reason="Need bank details")

    modified = app_svc.modify_application_in_correction(corr.application_id, 115, {"bank_account": "987654"})
    assert modified.application_data["bank_account"] == "987654"


@pytest.mark.django_db
def test_fr_023(base_scheme):
    """TEST-FR-023 | AFR-SPACS-023: Resubmission revalidates and invalidates prior verification."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=116)
    app_svc.upload_document(app.application_id, 116, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 116, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 116, student_cpi=8.0, student_family_income=250000.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    ver_svc.record_verification_findings(sub.application_id, 20, ["spacs_assistant"], findings="Old findings")
    ver_svc.request_correction(sub.application_id, 20, ["spacs_assistant"], reason="Update grade")

    resub = app_svc.resubmit_application(sub.application_id, 116)
    assert resub.state == "resubmitted"
    assert resub.verification_findings == ""
    assert resub.verification_authenticity_confirmed is False


@pytest.mark.django_db
def test_fr_024(base_scheme):
    """TEST-FR-024 | AFR-SPACS-024: Assistant marks verified and routes to Convener."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=117)
    app_svc.upload_document(app.application_id, 117, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 117, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 117, student_cpi=8.0, student_family_income=250000.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    verified = ver_svc.mark_verified(sub.application_id, 20, ["spacs_assistant"])

    assert verified.state == "verified"
    assert SpacsTask.objects.filter(entity_id=sub.application_id, assigned_role="spacs_convener").exists()


@pytest.mark.django_db
def test_fr_025(base_scheme):
    """TEST-FR-025 | AFR-SPACS-025: Assistant records unresolved verification concern."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=118)
    app_svc.upload_document(app.application_id, 118, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 118, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 118, student_cpi=8.0, student_family_income=250000.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    concern = ver_svc.record_verification_concern(sub.application_id, 20, ["spacs_assistant"], "Discrepancy in seal")

    assert concern.state == "verification_concern"
    assert SpacsTask.objects.filter(entity_id=sub.application_id, assigned_role="spacs_convener").exists()


@pytest.mark.django_db
def test_fr_026(db):
    """TEST-FR-026 | AFR-SPACS-026: SLA reminders and escalations for pending tasks."""
    past_time = timezone.now() - timedelta(hours=60)
    task = SpacsTask.objects.create(
        task_type="verification",
        entity_type="application",
        entity_id="SPACS-SLA-TEST",
        assigned_role="spacs_assistant",
        assigned_user_id=25,
        status="pending",
    )
    # simulate aged creation
    SpacsTask.objects.filter(id=task.id).update(created_at=past_time)

    escalated = task_svc.check_and_escalate_sla_tasks(sla_hours=48)
    assert any(t.id == task.id for t in escalated)
    assert SpacsNotification.objects.filter(recipient_user_id=25, event_type="sla_reminder").exists()


@pytest.mark.django_db
def test_fr_027(base_scheme):
    """TEST-FR-027 | AFR-SPACS-027: Convener reviews verified applications."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=119)
    app_svc.upload_document(app.application_id, 119, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 119, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 119, student_cpi=8.0, student_family_income=250000.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    verified = ver_svc.mark_verified(sub.application_id, 20, ["spacs_assistant"])

    review = dec_svc.open_convener_decision(verified.application_id, convener_user_id=1, user_roles=["spacs_convener"])
    assert review.state == "under_convener_review"


@pytest.mark.django_db
def test_fr_028_and_029(base_scheme):
    """TEST-FR-028 & TEST-FR-029 | AFR-SPACS-028, 029: Convener approves and records decision."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=120)
    app_svc.upload_document(app.application_id, 120, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 120, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 120, student_cpi=8.0, student_family_income=250000.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    ver_svc.mark_verified(sub.application_id, 20, ["spacs_assistant"])
    dec_svc.open_convener_decision(sub.application_id, 1, ["spacs_convener"])

    approved = dec_svc.approve_application(sub.application_id, 1, ["spacs_convener"], reason="Outstanding merit")
    assert approved.state == "approved"
    assert approved.decision_actor_user_id == 1
    assert approved.decision_reason == "Outstanding merit"
    assert approved.decision_at is not None


@pytest.mark.django_db
def test_fr_030(base_scheme):
    """TEST-FR-030 | AFR-SPACS-030: Student notified of decision outcome."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=121)
    app_svc.upload_document(app.application_id, 121, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 121, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 121, student_cpi=8.0, student_family_income=250000.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    ver_svc.mark_verified(sub.application_id, 20, ["spacs_assistant"])
    dec_svc.open_convener_decision(sub.application_id, 1, ["spacs_convener"])
    dec_svc.approve_application(sub.application_id, 1, ["spacs_convener"], reason="Merit approved")

    assert SpacsNotification.objects.filter(recipient_user_id=121, event_type="approved").exists()


@pytest.mark.django_db
def test_fr_031(base_scheme):
    """TEST-FR-031 | AFR-SPACS-031: Modification blocked in non-editable states."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=122)
    app_svc.upload_document(app.application_id, 122, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 122, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 122, student_cpi=8.0, student_family_income=250000.0)

    with pytest.raises(UnauthorizedActionError, match="not editable"):
        app_svc.modify_application_in_correction(sub.application_id, 122, {"note": "try edit"})


@pytest.mark.django_db
def test_fr_032(base_scheme):
    """TEST-FR-032 | AFR-SPACS-032: Substantive modification revalidates completeness & eligibility."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=123)
    app_svc.upload_document(app.application_id, 123, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 123, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 123, student_cpi=8.0, student_family_income=250000.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    ver_svc.request_correction(sub.application_id, 20, ["spacs_assistant"], reason="Update info")

    # Modify with ineligible CPI
    app_svc.modify_application_in_correction(sub.application_id, 123, {"cpi": 6.0})
    with pytest.raises(EligibilityError):
        app_svc.resubmit_application(sub.application_id, 123)


@pytest.mark.django_db
def test_fr_033(base_scheme):
    """TEST-FR-033 | AFR-SPACS-033: Withdrawal blocked after final decision."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=124)
    app_svc.upload_document(app.application_id, 124, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 124, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 124, student_cpi=8.0, student_family_income=250000.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    ver_svc.mark_verified(sub.application_id, 20, ["spacs_assistant"])
    dec_svc.open_convener_decision(sub.application_id, 1, ["spacs_convener"])
    dec_svc.approve_application(sub.application_id, 1, ["spacs_convener"])

    with pytest.raises(UnauthorizedActionError, match="terminal state"):
        app_svc.withdraw_application(sub.application_id, 124)


@pytest.mark.django_db
def test_fr_034(base_scheme):
    """TEST-FR-034 | AFR-SPACS-034: Withdrawal closes tasks and updates state."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=125)
    app_svc.upload_document(app.application_id, 125, "income_cert", "/uploads/inc.pdf")
    app_svc.upload_document(app.application_id, 125, "grade_sheet", "/uploads/grd.pdf")
    sub = app_svc.submit_application(app.application_id, 125, student_cpi=8.0, student_family_income=250000.0)

    withdrawn = app_svc.withdraw_application(sub.application_id, 125)
    assert withdrawn.state == "withdrawn"
    assert not SpacsTask.objects.filter(entity_id=sub.application_id, status="pending").exists()
    assert SpacsNotification.objects.filter(recipient_user_id=125, event_type="withdrawn").exists()


@pytest.mark.django_db
def test_fr_035(base_scheme):
    """TEST-FR-035 | AFR-SPACS-035: Student views own application status history."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=126)
    history = visible_applications_for_student(126)
    assert any(a.application_id == app.application_id for a in history)


@pytest.mark.django_db
def test_fr_036(base_scheme):
    """TEST-FR-036 | AFR-SPACS-036: Export restriction enforcement."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=127)
    # Student exports own
    data = app_svc.export_application(app.application_id, acting_user_id=127, acting_user_roles=["student"])
    assert data["application_id"] == app.application_id

    # Another student blocked
    with pytest.raises(UnauthorizedActionError):
        app_svc.export_application(app.application_id, acting_user_id=999, acting_user_roles=["student"])


@pytest.mark.django_db
def test_fr_037(db):
    """TEST-FR-037 | AFR-SPACS-037: Renewal eligibility gate."""
    non_renew_scheme = cat_svc.create_catalogue_entry(
        scheme_code="NON-RNW", name="No Renewal", scheme_type="scholarship", renewal_allowed=False, created_by_user_id=1
    )
    cat_svc.publish_catalogue_version("NON-RNW", "REF-02", date.today(), 1)
    app = SpacsApplication.objects.create(
        application_id="SPACS-NO-RNW",
        catalogue_entry=non_renew_scheme,
        applicant_user_id=128,
        state="approved",
        academic_cycle="2026-27",
    )
    with pytest.raises(RenewalEligibilityError, match="does not permit renewals"):
        rnw_svc.initiate_renewal(app.application_id, 128)


@pytest.mark.django_db
def test_fr_038_and_040(base_scheme):
    """TEST-FR-038 & TEST-FR-040 | AFR-SPACS-038, 040: Renewal prefill and verification routing."""
    parent = SpacsApplication.objects.create(
        application_id="SPACS-PAR-01",
        catalogue_entry=base_scheme,
        applicant_user_id=129,
        state="approved",
        academic_cycle="2026-27",
        application_data={"name": "Charlie", "prev_account": "1234"},
        cpi=8.5,
    )
    rnw = rnw_svc.initiate_renewal(parent.application_id, 129, renewal_cycle="2027-28")
    assert rnw.is_renewal is True
    assert rnw.parent_application == parent
    assert rnw.application_data["prev_account"] == "1234"

    # Upload refreshed doc and submit
    app_svc.upload_document(rnw.application_id, 129, "income_cert", "/docs/refreshed.pdf")
    app_svc.upload_document(rnw.application_id, 129, "grade_sheet", "/docs/refreshed_g.pdf")
    sub_rnw = rnw_svc.submit_renewal(rnw.application_id, 129, current_cpi=8.7, current_family_income=300000.0)

    assert sub_rnw.state == "renewal_submitted"
    assert SpacsTask.objects.filter(entity_id=rnw.application_id, assigned_role="spacs_assistant").exists()


@pytest.mark.django_db
def test_fr_039(base_scheme):
    """TEST-FR-039 | AFR-SPACS-039: Renewal validates updated criteria."""
    parent = SpacsApplication.objects.create(
        application_id="SPACS-PAR-02",
        catalogue_entry=base_scheme,
        applicant_user_id=130,
        state="approved",
        academic_cycle="2026-27",
    )
    rnw = rnw_svc.initiate_renewal(parent.application_id, 130)
    app_svc.upload_document(rnw.application_id, 130, "income_cert", "/docs/ref.pdf")
    app_svc.upload_document(rnw.application_id, 130, "grade_sheet", "/docs/ref_g.pdf")

    # Ineligible CPI
    with pytest.raises(EligibilityError):
        rnw_svc.submit_renewal(rnw.application_id, 130, current_cpi=6.8, current_family_income=300000.0)


@pytest.mark.django_db
def test_fr_041(base_scheme):
    """TEST-FR-041 | AFR-SPACS-041: Renewal reminders."""
    SpacsApplication.objects.create(
        application_id="SPACS-RNW-REM",
        catalogue_entry=base_scheme,
        applicant_user_id=131,
        state="approved",
        academic_cycle="2026-27",
    )
    reminded = rnw_svc.send_renewal_reminders(base_scheme.scheme_code)
    assert 131 in reminded
    assert SpacsNotification.objects.filter(recipient_user_id=131, event_type="renewal_reminder").exists()


@pytest.mark.django_db
def test_fr_042_and_043(db):
    """TEST-FR-042 & TEST-FR-043 | AFR-SPACS-042, 043: Award cycle candidate pool preparation."""
    award_scheme = cat_svc.create_catalogue_entry(
        scheme_code="AWD-GOLD",
        name="Director Gold Medal",
        scheme_type="award",
        min_cpi=8.5,
        candidate_source_method="system_pool",
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version("AWD-GOLD", "SENATE-MEDAL-2026", date.today(), 1)

    cycle = award_svc.open_award_cycle("AWD-GOLD", "2026-27", convener_user_id=1)
    assert cycle.state == "open"

    candidates = [
        {"student_user_id": 201, "cpi": 9.2, "academic_standing": "good"},
        {"student_user_id": 202, "cpi": 8.0, "academic_standing": "good"},  # Below 8.5
    ]
    prepared = award_svc.prepare_candidate_pool(cycle.id, 1, candidates)
    assert prepared.state == "pool_prepared"
    # Only eligible student added
    assert SpacsAwardCandidate.objects.filter(award_cycle=cycle).count() == 1
    assert SpacsAwardCandidate.objects.filter(award_cycle=cycle, student_user_id=201).exists()


@pytest.mark.django_db
def test_fr_044_to_047(db):
    """TEST-FR-044 to 047 | AFR-SPACS-044, 045, 046, 047: Evaluation, approval and publication."""
    award_scheme = cat_svc.create_catalogue_entry(
        scheme_code="AWD-SILVER",
        name="Silver Medal",
        scheme_type="award",
        min_cpi=8.0,
        candidate_source_method="system_pool",
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version("AWD-SILVER", "SENATE-MEDAL-2026", date.today(), 1)
    cycle = award_svc.open_award_cycle("AWD-SILVER", "2026-27", 1)
    award_svc.prepare_candidate_pool(cycle.id, 1, [{"student_user_id": 301, "cpi": 8.8}])

    # Committee evaluation
    award_svc.begin_committee_evaluation(cycle.id, evaluator_user_id=5)
    rec = award_svc.record_committee_results(
        cycle.id, 5, {301: {"score": 95.0, "recommendation": "winner", "remarks": "Top performer"}}
    )
    assert rec.state == "committee_result_recorded"

    # AFR-SPACS-046: Publication without approval blocked
    with pytest.raises(AwardPolicyError):
        award_svc.publish_award_results(cycle.id, 1)

    # AFR-SPACS-045: Record institutional approval
    award_svc.record_final_award_outcome(cycle.id, 1, approval_evidence="SENATE-MINUTES-ITEM-12")
    cycle.refresh_from_db()
    assert cycle.state == "ready_for_publication"

    # AFR-SPACS-047: Publish results
    pub = award_svc.publish_award_results(cycle.id, 1)
    assert pub.state == "published"
    assert pub.published_at is not None
    assert SpacsNotification.objects.filter(recipient_user_id=301, event_type="award_published").exists()


@pytest.mark.django_db
def test_fr_048(db):
    """TEST-FR-048 | AFR-SPACS-048: Notifications for significant events."""
    notif = audit_svc.notify_user(401, "approved", "Approved", "Your application is approved.")
    assert notif is not None
    assert notif.recipient_user_id == 401


@pytest.mark.django_db
def test_fr_049_and_050(db):
    """TEST-FR-049 & TEST-FR-050 | AFR-SPACS-049, 050: Immutable audit logging."""
    log = audit_svc.log_action("custom_event", "application", "APP-AUDIT", 1, {"note": "test"})
    assert log.timestamp is not None

    with pytest.raises(AuditProtectionError):
        log.delete()

    with pytest.raises(AuditProtectionError):
        log.actor_user_id = 99
        log.save()


@pytest.mark.django_db
def test_fr_051(base_scheme):
    """TEST-FR-051 | AFR-SPACS-051: Role-based access control enforcement."""
    app = app_svc.create_draft_application(base_scheme.scheme_code, applicant_user_id=140)
    # Student role cannot approve
    with pytest.raises(UnauthorizedActionError):
        dec_svc.approve_application(app.application_id, 140, user_roles=["student"])


@pytest.mark.django_db
def test_fr_052(db):
    """TEST-FR-052 | AFR-SPACS-052: Role reassignment routes pending tasks and preserves audit."""
    task = SpacsTask.objects.create(
        task_type="verification",
        entity_type="application",
        entity_id="SPACS-REASSIGN",
        assigned_role="spacs_assistant",
        assigned_user_id=50,
        status="pending",
    )
    count = task_svc.reassign_role_tasks("spacs_assistant", old_user_id=50, new_user_id=60, acting_user_id=1)
    assert count == 1
    task.refresh_from_db()
    assert task.assigned_user_id == 60
    assert SpacsAuditLog.objects.filter(event_type="role_tasks_reassigned").exists()
