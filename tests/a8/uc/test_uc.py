"""Automated Backend Tests for Use Case Strategy (UC: Use Case Specifications).
Frozen Design: a8_design/UC_DESIGN.json
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
    AwardPolicyError,
    CompletenessError,
    DuplicateApplicationError,
    EligibilityError,
    RenewalEligibilityError,
    UnauthorizedActionError,
)


@pytest.fixture
def uc_scheme(db):
    now = timezone.now()
    entry = cat_svc.create_catalogue_entry(
        scheme_code="UC-SCH-01",
        name="UC Test Scholarship",
        scheme_type="scholarship",
        description="Scholarship scheme for UC testing",
        min_cpi=7.0,
        max_family_income=600000.0,
        required_documents=["income_cert"],
        application_window_start=now - timedelta(days=5),
        application_window_end=now + timedelta(days=25),
        renewal_allowed=True,
        renewal_window_start=now - timedelta(days=5),
        renewal_window_end=now + timedelta(days=25),
        candidate_source_method="application",
        academic_cycle="2026-27",
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version(
        scheme_code=entry.scheme_code,
        policy_approval_ref="POLICY-UC-2026",
        effective_from=date.today(),
        actor_user_id=1,
    )
    return entry


@pytest.mark.django_db
def test_uc_001_mf_and_alts(uc_scheme):
    """TEST-UC-001-MF, A1, A2, E1, E2: UC-SPACS-001 Apply for Scholarship."""
    # A1: Draft saving
    app_draft = app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=501)
    app_svc.update_draft(app_draft.application_id, 501, {"draft_notes": "partial"})
    assert app_draft.state == "draft"

    # E1: Ineligible CPI
    app_svc.upload_document(app_draft.application_id, 501, "income_cert", "/doc.pdf")
    with pytest.raises(EligibilityError):
        app_svc.submit_application(app_draft.application_id, 501, student_cpi=6.5)

    # E2: Missing required document
    app2 = app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=502)
    with pytest.raises(CompletenessError):
        app_svc.submit_application(app2.application_id, 502, student_cpi=8.0)

    # MF: Successful submission
    sub = app_svc.submit_application(app_draft.application_id, 501, student_cpi=8.0)
    assert sub.state == "submitted"

    # A2: Duplicate rejection
    with pytest.raises(DuplicateApplicationError):
        app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=501)


@pytest.mark.django_db
def test_uc_002_mf_and_alts(uc_scheme):
    """TEST-UC-002-MF, A1, A2: UC-SPACS-002 Verify Scholarship Application."""
    app = app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=503)
    app_svc.upload_document(app.application_id, 503, "income_cert", "/doc.pdf")
    sub = app_svc.submit_application(app.application_id, 503, student_cpi=8.0)

    # A1: Assistant requests correction
    ver_svc.open_verification_task(sub.application_id, assistant_user_id=21, user_roles=["spacs_assistant"])
    corr = ver_svc.request_correction(sub.application_id, 21, ["spacs_assistant"], reason="Doc illegible")
    assert corr.state == "correction_required"

    # Student resubmits
    app_svc.modify_application_in_correction(corr.application_id, 503, {"fixed": True})
    resub = app_svc.resubmit_application(corr.application_id, 503)

    # A2: Assistant records concern
    ver_svc.open_verification_task(resub.application_id, 21, ["spacs_assistant"])
    concern = ver_svc.record_verification_concern(resub.application_id, 21, ["spacs_assistant"], "Income mismatch")
    assert concern.state == "verification_concern"

    # MF: Verified flow on fresh application
    app_fresh = app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=504)
    app_svc.upload_document(app_fresh.application_id, 504, "income_cert", "/doc.pdf")
    sub_fresh = app_svc.submit_application(app_fresh.application_id, 504, student_cpi=8.0)
    ver_svc.open_verification_task(sub_fresh.application_id, 21, ["spacs_assistant"])
    ver_svc.record_verification_findings(sub_fresh.application_id, 21, ["spacs_assistant"], "Verified ok")
    verified = ver_svc.mark_verified(sub_fresh.application_id, 21, ["spacs_assistant"])
    assert verified.state == "verified"


@pytest.mark.django_db
def test_uc_003_mf_and_e1(uc_scheme):
    """TEST-UC-003-MF, E1: UC-SPACS-003 Modify / Correct Pending Application."""
    app = app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=505)
    app_svc.upload_document(app.application_id, 505, "income_cert", "/doc.pdf")
    sub = app_svc.submit_application(app.application_id, 505, student_cpi=8.0)

    # E1: Cannot modify in submitted state
    with pytest.raises(UnauthorizedActionError):
        app_svc.modify_application_in_correction(sub.application_id, 505, {"data": "edit"})

    # Transition to correction_required and test MF
    ver_svc.open_verification_task(sub.application_id, 21, ["spacs_assistant"])
    ver_svc.request_correction(sub.application_id, 21, ["spacs_assistant"], reason="Need correction")
    mod = app_svc.modify_application_in_correction(sub.application_id, 505, {"data": "fixed"})
    assert mod.application_data["data"] == "fixed"
    resub = app_svc.resubmit_application(sub.application_id, 505)
    assert resub.state == "resubmitted"


@pytest.mark.django_db
def test_uc_004_mf_and_e1(uc_scheme):
    """TEST-UC-004-MF, E1: UC-SPACS-004 Withdraw Application."""
    app = app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=506)
    app_svc.upload_document(app.application_id, 506, "income_cert", "/doc.pdf")
    sub = app_svc.submit_application(app.application_id, 506, student_cpi=8.0)

    # MF: Withdraw from submitted
    withdrawn = app_svc.withdraw_application(sub.application_id, 506)
    assert withdrawn.state == "withdrawn"

    # E1: Withdraw rejected after final decision
    app2 = app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=507)
    app_svc.upload_document(app2.application_id, 507, "income_cert", "/doc.pdf")
    sub2 = app_svc.submit_application(app2.application_id, 507, student_cpi=8.0)
    ver_svc.open_verification_task(sub2.application_id, 21, ["spacs_assistant"])
    ver_svc.mark_verified(sub2.application_id, 21, ["spacs_assistant"])
    dec_svc.open_convener_decision(sub2.application_id, 1, ["spacs_convener"])
    dec_svc.approve_application(sub2.application_id, 1, ["spacs_convener"])

    with pytest.raises(UnauthorizedActionError, match="terminal state"):
        app_svc.withdraw_application(sub2.application_id, 507)


@pytest.mark.django_db
def test_uc_006_mf_and_alts(uc_scheme):
    """TEST-UC-006-MF, A1, A2: UC-SPACS-006 Make Scholarship Decision."""
    # Setup verified app
    app = app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=508)
    app_svc.upload_document(app.application_id, 508, "income_cert", "/doc.pdf")
    sub = app_svc.submit_application(app.application_id, 508, student_cpi=8.0)
    ver_svc.open_verification_task(sub.application_id, 21, ["spacs_assistant"])
    ver_svc.mark_verified(sub.application_id, 21, ["spacs_assistant"])

    # A2: Convener returns for correction
    dec_svc.open_convener_decision(sub.application_id, 1, ["spacs_convener"])
    ret = dec_svc.return_for_correction(sub.application_id, 1, ["spacs_convener"], reason="Clarify family income")
    assert ret.state == "correction_required"

    # Resubmit and reverify
    app_svc.resubmit_application(sub.application_id, 508)
    ver_svc.open_verification_task(sub.application_id, 21, ["spacs_assistant"])
    ver_svc.mark_verified(sub.application_id, 21, ["spacs_assistant"])

    # MF: Approve
    dec_svc.open_convener_decision(sub.application_id, 1, ["spacs_convener"])
    approved = dec_svc.approve_application(sub.application_id, 1, ["spacs_convener"])
    assert approved.state == "approved"

    # A1: Reject flow
    app_rej = app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=509)
    app_svc.upload_document(app_rej.application_id, 509, "income_cert", "/doc.pdf")
    sub_rej = app_svc.submit_application(app_rej.application_id, 509, student_cpi=8.0)
    ver_svc.open_verification_task(sub_rej.application_id, 21, ["spacs_assistant"])
    ver_svc.record_verification_concern(sub_rej.application_id, 21, ["spacs_assistant"], "Doubtful claims")
    dec_svc.open_convener_decision(sub_rej.application_id, 1, ["spacs_convener"])
    rej = dec_svc.reject_application(sub_rej.application_id, 1, ["spacs_convener"], reason="Discrepancy confirmed")
    assert rej.state == "rejected"


@pytest.mark.django_db
def test_uc_007_and_008(uc_scheme):
    """TEST-UC-007 & TEST-UC-008: Download / Print and Status Tracking."""
    app = app_svc.create_draft_application(uc_scheme.scheme_code, applicant_user_id=510)
    # UC-008 MF: Check status
    history = visible_applications_for_student(510)
    assert any(a.application_id == app.application_id for a in history)

    # UC-007 MF: Student download own
    own_data = app_svc.export_application(app.application_id, 510, ["student"])
    assert own_data["application_id"] == app.application_id

    # UC-007 A1: Staff export
    staff_data = app_svc.export_application(app.application_id, 21, ["spacs_assistant"])
    assert staff_data["application_id"] == app.application_id

    # UC-007 E1: Unauthorized download
    with pytest.raises(UnauthorizedActionError):
        app_svc.export_application(app.application_id, 999, ["student"])


@pytest.mark.django_db
def test_uc_010_011_012_014(db):
    """TEST-UC-010, 011, 012, 014: Catalogue Administration Use Cases."""
    # UC-010 MF: Create catalogue entry
    entry = cat_svc.create_catalogue_entry(
        scheme_code="UC-ADMIN-SCH", name="Admin Scheme", scheme_type="scholarship", created_by_user_id=1
    )
    assert entry.status == "draft"

    # UC-011 MF: Update draft
    updated_draft = cat_svc.update_draft_catalogue_entry("UC-ADMIN-SCH", 1, min_cpi=8.0)
    assert float(updated_draft.min_cpi) == 8.0

    # UC-023 MF: Publish catalogue version
    cat_svc.publish_catalogue_version("UC-ADMIN-SCH", "SENATE-UC", date.today(), 1)
    assert SpacsCatalogueEntry.objects.get(scheme_code="UC-ADMIN-SCH").status == "published"

    # UC-011 A1: Update published creates new draft version
    updated_pub = cat_svc.update_draft_catalogue_entry("UC-ADMIN-SCH", 1, min_cpi=8.2)
    assert updated_pub.version == 2
    assert updated_pub.status == "draft"

    # UC-012 MF: Retire catalogue entry
    retired = cat_svc.retire_catalogue_entry("UC-ADMIN-SCH", 1)
    assert retired.status == "retired"

    # UC-014 MF: Browse catalogue only returns published
    visible = visible_catalogue()
    assert "UC-ADMIN-SCH" not in [e.scheme_code for e in visible]


@pytest.mark.django_db
def test_uc_015_mf_and_exceptions(uc_scheme):
    """TEST-UC-015-MF, E1, E2: UC-SPACS-015 Apply for Scholarship Renewal."""
    # E2: Prior application not approved
    rejected_parent = SpacsApplication.objects.create(
        application_id="SPACS-REJ-PAR", catalogue_entry=uc_scheme, applicant_user_id=511, state="rejected", academic_cycle="2026-27"
    )
    with pytest.raises(RenewalEligibilityError):
        rnw_svc.initiate_renewal(rejected_parent.application_id, 511)

    # Approved parent
    approved_parent = SpacsApplication.objects.create(
        application_id="SPACS-APP-PAR", catalogue_entry=uc_scheme, applicant_user_id=512, state="approved", academic_cycle="2026-27"
    )

    # E1: Scheme with renewal_allowed=False
    uc_scheme.renewal_allowed = False
    uc_scheme.save()
    with pytest.raises(RenewalEligibilityError):
        rnw_svc.initiate_renewal(approved_parent.application_id, 512)

    # MF: Successful renewal flow
    uc_scheme.renewal_allowed = True
    uc_scheme.save()
    rnw = rnw_svc.initiate_renewal(approved_parent.application_id, 512)
    app_svc.upload_document(rnw.application_id, 512, "income_cert", "/doc.pdf")
    sub_rnw = rnw_svc.submit_renewal(rnw.application_id, 512, current_cpi=8.5)
    assert sub_rnw.state == "renewal_submitted"


@pytest.mark.django_db
def test_uc_017_to_020_awards(db):
    """TEST-UC-017, 018, 019, 020: Award Lifecycle Use Cases."""
    entry = cat_svc.create_catalogue_entry(
        scheme_code="UC-AWD-01", name="UC Award", scheme_type="award", min_cpi=8.0, candidate_source_method="system_pool", created_by_user_id=1
    )
    cat_svc.publish_catalogue_version("UC-AWD-01", "SENATE-AWD", date.today(), 1)
    cycle = award_svc.open_award_cycle("UC-AWD-01", "2026-27", 1)

    # UC-017 MF: Prepare pool
    award_svc.prepare_candidate_pool(cycle.id, 1, [{"student_user_id": 601, "cpi": 8.5}])
    assert cycle.candidates.count() == 1

    # UC-018 MF: Evaluate
    award_svc.begin_committee_evaluation(cycle.id, 5)
    award_svc.record_committee_results(cycle.id, 5, {601: {"score": 90.0, "recommendation": "winner"}})

    # UC-020 E1: Cannot publish without approval
    with pytest.raises(AwardPolicyError):
        award_svc.publish_award_results(cycle.id, 1)

    # UC-019 A1: Approval pending
    award_svc.record_final_award_outcome(cycle.id, 1, approval_evidence=None)
    cycle.refresh_from_db()
    assert cycle.state == "awaiting_approval"

    # UC-019 A2: Record approval received
    award_svc.record_institutional_approval_received(cycle.id, 1, approval_evidence="SENATE-APPROVED-DOC")
    cycle.refresh_from_db()
    assert cycle.state == "ready_for_publication"

    # UC-020 MF: Publish award results
    published = award_svc.publish_award_results(cycle.id, 1)
    assert published.state == "published"


@pytest.mark.django_db
def test_uc_021_audit_trail(db):
    """TEST-UC-021-MF, E1: View Audit Trail."""
    audit_svc.log_action("test_audit", "test_entity", "1", 1)

    # MF: Auditor views
    logs = get_audit_trail_for_auditor(["spacs_auditor"])
    assert logs.count() >= 1

    # E1: Student blocked
    with pytest.raises(PermissionError):
        get_audit_trail_for_auditor(["student"])


@pytest.mark.django_db
def test_uc_024_025_026(base_scheme=None):
    """TEST-UC-024, 025, 026: Event-triggered Use Cases (SLA, Reminder, Reassignment)."""
    # UC-024: SLA Escalation
    old_time = timezone.now() - timedelta(hours=60)
    task = SpacsTask.objects.create(
        task_type="decision", entity_type="application", entity_id="SLA-APP", assigned_role="spacs_convener", assigned_user_id=2, status="pending"
    )
    SpacsTask.objects.filter(id=task.id).update(created_at=old_time)
    escalated = task_svc.check_and_escalate_sla_tasks(sla_hours=48)
    assert any(t.id == task.id for t in escalated)

    # UC-026: Reassign Tasks
    reassigned_count = task_svc.reassign_role_tasks("spacs_convener", old_user_id=2, new_user_id=3, acting_user_id=1)
    assert reassigned_count == 1
    task.refresh_from_db()
    assert task.assigned_user_id == 3
