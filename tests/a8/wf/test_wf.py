"""Automated Backend Tests for Workflow Strategy (WF: Basis and Composite Workflows).
Frozen Design: a8_design/WF_DESIGN.json
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


@pytest.fixture
def wf_scheme(db):
    now = timezone.now()
    entry = cat_svc.create_catalogue_entry(
        scheme_code="WF-SCH-01",
        name="Workflow Scholarship",
        scheme_type="scholarship",
        description="Scholarship scheme for workflow tests",
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
        policy_approval_ref="POLICY-WF-2026",
        effective_from=date.today(),
        actor_user_id=1,
    )
    return entry


@pytest.mark.django_db
def test_wf_bw01_new_app_successful_verification(wf_scheme):
    """TEST-WF-BW01: BW-SPACS-01 New Application - Successful Verification."""
    app = app_svc.create_draft_application(wf_scheme.scheme_code, applicant_user_id=801)
    app_svc.upload_document(app.application_id, 801, "income_cert", "/doc.pdf")
    sub = app_svc.submit_application(app.application_id, 801, student_cpi=8.0)
    assert sub.state == "submitted"

    ver = ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    assert ver.state == "under_verification"

    verified = ver_svc.mark_verified(sub.application_id, 20, ["spacs_assistant"])
    assert verified.state == "verified"


@pytest.mark.django_db
def test_wf_bw02_correction_resubmission(wf_scheme):
    """TEST-WF-BW02: BW-SPACS-02 Correction and Resubmission - One Traversal."""
    app = app_svc.create_draft_application(wf_scheme.scheme_code, applicant_user_id=802)
    app_svc.upload_document(app.application_id, 802, "income_cert", "/doc.pdf")
    sub = app_svc.submit_application(app.application_id, 802, student_cpi=8.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])

    # 1. Assistant requests correction
    corr = ver_svc.request_correction(sub.application_id, 20, ["spacs_assistant"], reason="Need correction")
    assert corr.state == "correction_required"

    # 2. Student resubmits
    app_svc.modify_application_in_correction(corr.application_id, 802, {"info": "corrected"})
    resub = app_svc.resubmit_application(corr.application_id, 802)
    assert resub.state == "resubmitted"

    # 3. Assistant reverifies
    ver_svc.open_verification_task(resub.application_id, 20, ["spacs_assistant"])
    verified = ver_svc.mark_verified(resub.application_id, 20, ["spacs_assistant"])
    assert verified.state == "verified"


@pytest.mark.django_db
def test_wf_bw03_scholarship_approval(wf_scheme):
    """TEST-WF-BW03: BW-SPACS-03 Scholarship Approval."""
    app = app_svc.create_draft_application(wf_scheme.scheme_code, applicant_user_id=803)
    app_svc.upload_document(app.application_id, 803, "income_cert", "/doc.pdf")
    sub = app_svc.submit_application(app.application_id, 803, student_cpi=8.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    verified = ver_svc.mark_verified(sub.application_id, 20, ["spacs_assistant"])

    review = dec_svc.open_convener_decision(verified.application_id, 1, ["spacs_convener"])
    assert review.state == "under_convener_review"

    approved = dec_svc.approve_application(review.application_id, 1, ["spacs_convener"], reason="Approved")
    assert approved.state == "approved"


@pytest.mark.django_db
def test_wf_bw04_scholarship_rejection_and_alt(wf_scheme):
    """TEST-WF-BW04 & ALT: BW-SPACS-04 Scholarship Rejection and Return for Correction."""
    # Rejection from concern
    app = app_svc.create_draft_application(wf_scheme.scheme_code, applicant_user_id=804)
    app_svc.upload_document(app.application_id, 804, "income_cert", "/doc.pdf")
    sub = app_svc.submit_application(app.application_id, 804, student_cpi=8.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    concern = ver_svc.record_verification_concern(sub.application_id, 20, ["spacs_assistant"], "Concern noted")
    assert concern.state == "verification_concern"

    review = dec_svc.open_convener_decision(concern.application_id, 1, ["spacs_convener"])
    rej = dec_svc.reject_application(review.application_id, 1, ["spacs_convener"], reason="Rejected on concern")
    assert rej.state == "rejected"

    # Alt: Convener returns for correction
    app2 = app_svc.create_draft_application(wf_scheme.scheme_code, applicant_user_id=805)
    app_svc.upload_document(app2.application_id, 805, "income_cert", "/doc.pdf")
    sub2 = app_svc.submit_application(app2.application_id, 805, student_cpi=8.0)
    ver_svc.open_verification_task(sub2.application_id, 20, ["spacs_assistant"])
    ver_svc.mark_verified(sub2.application_id, 20, ["spacs_assistant"])
    dec_svc.open_convener_decision(sub2.application_id, 1, ["spacs_convener"])
    ret = dec_svc.return_for_correction(sub2.application_id, 1, ["spacs_convener"], reason="Fix info")
    assert ret.state == "correction_required"


@pytest.mark.django_db
def test_wf_bw05_withdrawals(wf_scheme):
    """TEST-WF-BW05: BW-SPACS-05 Cross-Cutting Application Withdrawal."""
    # From submitted
    a1 = app_svc.create_draft_application(wf_scheme.scheme_code, applicant_user_id=806)
    app_svc.upload_document(a1.application_id, 806, "income_cert", "/doc.pdf")
    s1 = app_svc.submit_application(a1.application_id, 806, student_cpi=8.0)
    w1 = app_svc.withdraw_application(s1.application_id, 806)
    assert w1.state == "withdrawn"

    # From under_verification
    a2 = app_svc.create_draft_application(wf_scheme.scheme_code, applicant_user_id=807)
    app_svc.upload_document(a2.application_id, 807, "income_cert", "/doc.pdf")
    s2 = app_svc.submit_application(a2.application_id, 807, student_cpi=8.0)
    ver_svc.open_verification_task(s2.application_id, 20, ["spacs_assistant"])
    w2 = app_svc.withdraw_application(s2.application_id, 807)
    assert w2.state == "withdrawn"

    # From correction_required
    a3 = app_svc.create_draft_application(wf_scheme.scheme_code, applicant_user_id=808)
    app_svc.upload_document(a3.application_id, 808, "income_cert", "/doc.pdf")
    s3 = app_svc.submit_application(a3.application_id, 808, student_cpi=8.0)
    ver_svc.open_verification_task(s3.application_id, 20, ["spacs_assistant"])
    c3 = ver_svc.request_correction(s3.application_id, 20, ["spacs_assistant"], reason="Corr")
    w3 = app_svc.withdraw_application(c3.application_id, 808)
    assert w3.state == "withdrawn"

    # From verified (before convener review)
    a4 = app_svc.create_draft_application(wf_scheme.scheme_code, applicant_user_id=809)
    app_svc.upload_document(a4.application_id, 809, "income_cert", "/doc.pdf")
    s4 = app_svc.submit_application(a4.application_id, 809, student_cpi=8.0)
    ver_svc.open_verification_task(s4.application_id, 20, ["spacs_assistant"])
    v4 = ver_svc.mark_verified(s4.application_id, 20, ["spacs_assistant"])
    w4 = app_svc.withdraw_application(v4.application_id, 809, convener_review_started=False)
    assert w4.state == "withdrawn"


@pytest.mark.django_db
def test_wf_bw06_bw07_bw10_renewals(wf_scheme):
    """TEST-WF-BW06, BW07, BW10: Renewal Submission, Verification, Approval, and Rejection."""
    parent = SpacsApplication.objects.create(
        application_id="SPACS-PAR-WF",
        catalogue_entry=wf_scheme,
        applicant_user_id=810,
        state="approved",
        academic_cycle="2026-27",
    )

    # BW-06: Submission and Verification
    rnw = rnw_svc.initiate_renewal(parent.application_id, 810)
    app_svc.upload_document(rnw.application_id, 810, "income_cert", "/doc.pdf")
    sub_rnw = rnw_svc.submit_renewal(rnw.application_id, 810, current_cpi=8.5)
    assert sub_rnw.state == "renewal_submitted"

    ver_svc.open_verification_task(sub_rnw.application_id, 20, ["spacs_assistant"])
    assert SpacsApplication.objects.get(application_id=rnw.application_id).state == "renewal_under_verification"

    ver = ver_svc.mark_verified(sub_rnw.application_id, 20, ["spacs_assistant"])
    assert ver.state == "renewal_verified"

    # BW-07: Approval
    dec_svc.open_convener_decision(ver.application_id, 1, ["spacs_convener"])
    assert SpacsApplication.objects.get(application_id=rnw.application_id).state == "renewal_under_decision"
    renewed = dec_svc.approve_application(ver.application_id, 1, ["spacs_convener"])
    assert renewed.state == "renewed"

    # BW-10: Rejection on another renewal
    parent2 = SpacsApplication.objects.create(
        application_id="SPACS-PAR-WF2", catalogue_entry=wf_scheme, applicant_user_id=811, state="approved", academic_cycle="2026-27"
    )
    rnw2 = rnw_svc.initiate_renewal(parent2.application_id, 811)
    app_svc.upload_document(rnw2.application_id, 811, "income_cert", "/doc.pdf")
    sub_rnw2 = rnw_svc.submit_renewal(rnw2.application_id, 811, current_cpi=8.5)
    ver_svc.open_verification_task(sub_rnw2.application_id, 20, ["spacs_assistant"])
    ver2 = ver_svc.mark_verified(sub_rnw2.application_id, 20, ["spacs_assistant"])
    dec_svc.open_convener_decision(ver2.application_id, 1, ["spacs_convener"])
    rej_rnw = dec_svc.reject_application(ver2.application_id, 1, ["spacs_convener"], reason="Low performance")
    assert rej_rnw.state == "renewal_rejected"


@pytest.mark.django_db
def test_wf_bw08_bw09_bw11_awards(db):
    """TEST-WF-BW08, BW09, BW11: Award Candidate Preparation, Approval Available & Pending."""
    award_entry = cat_svc.create_catalogue_entry(
        scheme_code="WF-AWD", name="Award WF", scheme_type="award", min_cpi=8.0, candidate_source_method="system_pool", created_by_user_id=1
    )
    cat_svc.publish_catalogue_version("WF-AWD", "SENATE-WF", date.today(), 1)
    cycle = award_svc.open_award_cycle("WF-AWD", "2026-27", 1)

    # BW-08: Prepare and evaluate
    award_svc.prepare_candidate_pool(cycle.id, 1, [{"student_user_id": 901, "cpi": 9.0}])
    award_svc.begin_committee_evaluation(cycle.id, 5)
    res = award_svc.record_committee_results(cycle.id, 5, {901: {"score": 98.0, "recommendation": "winner"}})
    assert res.state == "committee_result_recorded"

    # BW-09: Approval Available immediately
    award_svc.record_final_award_outcome(cycle.id, 1, approval_evidence="SENATE-MINUTES-AWD")
    cycle.refresh_from_db()
    assert cycle.state == "ready_for_publication"
    pub = award_svc.publish_award_results(cycle.id, 1)
    assert pub.state == "published"

    # BW-11: Approval Pending then Received
    cycle2 = award_svc.open_award_cycle("WF-AWD", "2027-28", 1)
    award_svc.prepare_candidate_pool(cycle2.id, 1, [{"student_user_id": 902, "cpi": 8.8}])
    award_svc.begin_committee_evaluation(cycle2.id, 5)
    award_svc.record_committee_results(cycle2.id, 5, {902: {"score": 92.0, "recommendation": "winner"}})

    # Await approval
    award_svc.record_final_award_outcome(cycle2.id, 1, approval_evidence=None)
    cycle2.refresh_from_db()
    assert cycle2.state == "awaiting_approval"

    # Later recorded
    award_svc.record_institutional_approval_received(cycle2.id, 1, approval_evidence="SENATE-LATE-CONFIRM")
    cycle2.refresh_from_db()
    assert cycle2.state == "ready_for_publication"

    pub2 = award_svc.publish_award_results(cycle2.id, 1)
    assert pub2.state == "published"


@pytest.mark.django_db
def test_wf_cw01_cw02_cw03_composites(wf_scheme):
    """TEST-WF-CW01, CW02, CW03: End-to-End Composite Workflows."""
    # CW-01: End-to-end Scholarship Lifecycle with correction and approval
    app = app_svc.create_draft_application(wf_scheme.scheme_code, applicant_user_id=820)
    app_svc.upload_document(app.application_id, 820, "income_cert", "/doc.pdf")
    sub = app_svc.submit_application(app.application_id, 820, student_cpi=8.0)
    ver_svc.open_verification_task(sub.application_id, 20, ["spacs_assistant"])
    corr = ver_svc.request_correction(sub.application_id, 20, ["spacs_assistant"], reason="Upload clearer doc")
    app_svc.modify_application_in_correction(corr.application_id, 820, {"doc_note": "uploaded"})
    resub = app_svc.resubmit_application(corr.application_id, 820)
    ver_svc.open_verification_task(resub.application_id, 20, ["spacs_assistant"])
    ver_svc.mark_verified(resub.application_id, 20, ["spacs_assistant"])
    dec_svc.open_convener_decision(sub.application_id, 1, ["spacs_convener"])
    final_app = dec_svc.approve_application(sub.application_id, 1, ["spacs_convener"])
    assert final_app.state == "approved"

    # CW-02: End-to-end Renewal Lifecycle with correction and renewal
    rnw = rnw_svc.initiate_renewal(final_app.application_id, 820)
    app_svc.upload_document(rnw.application_id, 820, "income_cert", "/doc.pdf")
    sub_rnw = rnw_svc.submit_renewal(rnw.application_id, 820, current_cpi=8.2)
    ver_svc.open_verification_task(sub_rnw.application_id, 20, ["spacs_assistant"])
    corr_rnw = ver_svc.request_correction(sub_rnw.application_id, 20, ["spacs_assistant"], reason="Update seal")
    app_svc.modify_application_in_correction(corr_rnw.application_id, 820, {"updated": True})
    resub_rnw = app_svc.resubmit_application(corr_rnw.application_id, 820)
    ver_svc.mark_verified(resub_rnw.application_id, 20, ["spacs_assistant"])
    dec_svc.open_convener_decision(resub_rnw.application_id, 1, ["spacs_convener"])
    final_rnw = dec_svc.approve_application(resub_rnw.application_id, 1, ["spacs_convener"])
    assert final_rnw.state == "renewed"

    # CW-03: End-to-end Convocation Award Lifecycle
    awd_entry = cat_svc.create_catalogue_entry(
        scheme_code="CW-AWD", name="CW Medal", scheme_type="award", min_cpi=8.5, candidate_source_method="system_pool", created_by_user_id=1
    )
    cat_svc.publish_catalogue_version("CW-AWD", "SENATE-CW", date.today(), 1)
    cycle = award_svc.open_award_cycle("CW-AWD", "2026-27", 1)
    award_svc.prepare_candidate_pool(cycle.id, 1, [{"student_user_id": 999, "cpi": 9.5}])
    award_svc.begin_committee_evaluation(cycle.id, 5)
    award_svc.record_committee_results(cycle.id, 5, {999: {"score": 99.0, "recommendation": "winner"}})
    award_svc.record_final_award_outcome(cycle.id, 1, approval_evidence=None)
    award_svc.record_institutional_approval_received(cycle.id, 1, approval_evidence="SENATE-APPROVED-CW")
    pub = award_svc.publish_award_results(cycle.id, 1)
    assert pub.state == "published"
