"""Automated tests for SPACS Workflow Specifications (WF Strategy).

Obligations:
- 11 Basis Workflows (BW-SPACS-01 through BW-SPACS-11)
- 3 Composite Workflows (CW-SPACS-01 through CW-SPACS-03)
- 10 Decision Branches (BRANCH-01 through BRANCH-10)
Total: 24 test cases.
"""
from __future__ import annotations

from datetime import timedelta
import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.spacs.models import (
    ApplicationDocument,
    ApplicationTransition,
    AwardCandidate,
    AwardCycle,
    ScholarshipApplication,
    SchemePolicyVersion,
    SpacsAuditLog,
    SpacsNotification,
)
from modules.spacs.services import applications as app_service
from modules.spacs.services import awards as award_service
from modules.spacs.services import documents as doc_service

pytestmark = pytest.mark.django_db


# ==============================================================================
# 1. BASIS WORKFLOWS (BW-SPACS-01 .. BW-SPACS-11)
# ==============================================================================

def test_wf_bw_01_main(student, assistant, scheme_mcm, policy_mcm):
    """TC-WF-BW-01-MAIN | BW-SPACS-01: New Application - Successful Verification.
    Path: Draft -> Submitted -> Under Verification -> Verified.
    """
    draft = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    assert draft.status == "draft"

    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Income Cert", file_url="/u/inc.pdf", actor=student
    )
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="grade_card",
        title="Grade Card", file_url="/u/gc.pdf", actor=student
    )
    sub = app_service.submit_application(
        application_id=draft.id,
        student_facts={"cpi": 8.5, "parental_income": 300000.0},
        actor=student,
    )
    assert sub.status == "submitted"

    under_v = app_service.verify_application(application_id=sub.id, action_type="start", actor=assistant)
    assert under_v.status == "under_verification"

    verified = app_service.verify_application(
        application_id=under_v.id, action_type="verify", findings={"cpi_verified": True}, actor=assistant
    )
    assert verified.status == "verified"


def test_wf_bw_02_main(student, assistant, scheme_mcm, policy_mcm):
    """TC-WF-BW-02-MAIN | BW-SPACS-02: Correction and Resubmission - One Traversal.
    Path: Submitted -> Under Verification -> Correction Required -> Resubmitted.
    """
    draft = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Income Cert", file_url="/u/inc.pdf", actor=student
    )
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="grade_card",
        title="Grade Card", file_url="/u/gc.pdf", actor=student
    )
    sub = app_service.submit_application(
        application_id=draft.id,
        student_facts={"cpi": 8.5, "parental_income": 300000.0},
        actor=student,
    )
    app_service.verify_application(application_id=sub.id, action_type="start", actor=assistant)
    corr = app_service.verify_application(
        application_id=sub.id, action_type="request_correction", reason="Upload clear income certificate", actor=assistant
    )
    assert corr.status == "correction_required"

    resub = app_service.modify_application(
        application_id=corr.id,
        updated_data={"cpi": 8.5, "parental_income": 300000.0},
        resubmit=True,
        actor=student,
    )
    assert resub.status == "resubmitted"


def test_wf_bw_03_main(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-WF-BW-03-MAIN | BW-SPACS-03: Scholarship Approval.
    Path: Verified -> Under Convener Review -> Approved.
    """
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-BW03-APP",
        student_user_id=student.user_id,
        scheme=scheme_mcm,
        policy_version=policy_mcm,
        academic_cycle="2024-25",
        status="verified",
    )
    approved = app_service.decide_application(
        application_id=app.id, decision="approve", reason="Meets all criteria per policy", actor=convener
    )
    assert approved.status == "approved"


def test_wf_bw_04_main(student, convener, scheme_mcm, policy_mcm):
    """TC-WF-BW-04-MAIN | BW-SPACS-04: Scholarship Rejection.
    Path: Verified -> Rejected by Convener.
    """
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-BW04-APP",
        student_user_id=student.user_id,
        scheme=scheme_mcm,
        policy_version=policy_mcm,
        academic_cycle="2024-25",
        status="verified",
    )
    rejected = app_service.decide_application(
        application_id=app.id, decision="reject", reason="Quota exhausted", actor=convener
    )
    assert rejected.status == "rejected"


def test_wf_bw_05_main(student, scheme_mcm, policy_mcm):
    """TC-WF-BW-05-MAIN | BW-SPACS-05: Cross-Cutting Application Withdrawal.
    Path: Submitted -> Withdrawn.
    """
    draft = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Income Cert", file_url="/u/inc.pdf", actor=student
    )
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="grade_card",
        title="Grade Card", file_url="/u/gc.pdf", actor=student
    )
    sub = app_service.submit_application(
        application_id=draft.id,
        student_facts={"cpi": 8.5, "parental_income": 300000.0},
        actor=student,
    )
    withdrawn = app_service.withdraw_application(
        application_id=sub.id, reason="Student opt-out", actor=student
    )
    assert withdrawn.status == "withdrawn"


def test_wf_bw_06_main(student, assistant, scheme_mcm, policy_mcm):
    """TC-WF-BW-06-MAIN | BW-SPACS-06: Renewal Submission and Verification.
    Path: Prior Approved Application -> Submit Renewal -> Verified.
    """
    prior = ScholarshipApplication.objects.create(
        application_number="SPACS-BW06-PRIOR",
        student_user_id=student.user_id,
        scheme=scheme_mcm,
        policy_version=policy_mcm,
        academic_cycle="2023-24",
        status="approved",
    )
    renewal = app_service.submit_renewal(
        prior_application_id=prior.id,
        academic_cycle="2024-25",
        current_facts={"cpi": 8.2, "active_backlogs": 0},
        actor=student,
    )
    assert renewal.status == "submitted"
    assert renewal.is_renewal is True

    app_service.verify_application(application_id=renewal.id, action_type="start", actor=assistant)
    ver = app_service.verify_application(application_id=renewal.id, action_type="verify", actor=assistant)
    assert ver.status == "verified"


def test_wf_bw_07_main(student, convener, scheme_mcm, policy_mcm):
    """TC-WF-BW-07-MAIN | BW-SPACS-07: Renewal Approval.
    Path: Renewal Verified -> Approved by Convener.
    """
    renewal = ScholarshipApplication.objects.create(
        application_number="SPACS-BW07-REN",
        student_user_id=student.user_id,
        scheme=scheme_mcm,
        policy_version=policy_mcm,
        academic_cycle="2024-25",
        status="verified",
        is_renewal=True,
    )
    appr = app_service.decide_application(
        application_id=renewal.id, decision="approve", reason="Renewal verified and confirmed", actor=convener
    )
    assert appr.status == "approved"


def test_wf_bw_08_main(convener, committee_member, award_scheme, award_policy):
    """TC-WF-BW-08-MAIN | BW-SPACS-08: Award Candidate Preparation and Committee Evaluation.
    Path: Open Award Cycle -> Prepare Pool -> Committee Records Evaluations.
    """
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Awards Committee", actor=convener
    )
    award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id, candidates=[{"student_user_id": 2001, "cpi": 9.5}], actor=convener
    )
    cand = AwardCandidate.objects.filter(award_cycle=cycle).first()
    res = award_service.record_committee_evaluations(
        award_cycle_id=cycle.id,
        evaluations=[{"student_user_id": cand.student_user_id, "score": 95.0, "recommendation_status": "recommended"}],
        actor=committee_member,
    )
    assert res.status == "result_recorded"


def test_wf_bw_09_main(convener, committee_member, award_scheme, award_policy):
    """TC-WF-BW-09-MAIN | BW-SPACS-09: Award Finalization and Publication - Approval Available.
    Path: Committee Evaluated -> Institutional Approval Recorded -> Published.
    """
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id, candidates=[{"student_user_id": 2002, "cpi": 9.6}], actor=convener
    )
    cand = AwardCandidate.objects.filter(award_cycle=cycle).first()
    award_service.record_committee_evaluations(
        award_cycle_id=cycle.id,
        evaluations=[{"student_user_id": cand.student_user_id, "score": 97.0, "recommendation_status": "recommended"}],
        actor=committee_member,
    )
    approved = award_service.record_final_approval(
        award_cycle_id=cycle.id, approval_reference="SEN/RES/2025/11", approving_authority="Senate",
        approved_candidate_ids=[2002], actor=convener
    )
    assert approved.status == "ready_for_publication"

    pub = award_service.publish_award_results(award_cycle_id=cycle.id, actor=convener)
    assert pub.status == "published"


def test_wf_bw_10_main(student, convener, scheme_mcm, policy_mcm):
    """TC-WF-BW-10-MAIN | BW-SPACS-10: Renewal Rejection.
    Path: Renewal Verified (or Under Review) -> Rejected by Convener.
    """
    renewal = ScholarshipApplication.objects.create(
        application_number="SPACS-BW10-REN",
        student_user_id=student.user_id,
        scheme=scheme_mcm,
        policy_version=policy_mcm,
        academic_cycle="2024-25",
        status="verified",
        is_renewal=True,
    )
    rej = app_service.decide_application(
        application_id=renewal.id, decision="reject", reason="Failed CPI renewal threshold in audit", actor=convener
    )
    assert rej.status == "rejected"


def test_wf_bw_11_main(convener, committee_member, award_scheme, award_policy):
    """TC-WF-BW-11-MAIN | BW-SPACS-11: Award Finalization and Publication - Approval Pending.
    Path: Results Recorded -> Approval Reference Empty -> Retains Ready/Evaluated Status (Not Published).
    """
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id, candidates=[{"student_user_id": 2003, "cpi": 9.1}], actor=convener
    )
    cand = AwardCandidate.objects.filter(award_cycle=cycle).first()
    award_service.record_committee_evaluations(
        award_cycle_id=cycle.id,
        evaluations=[{"student_user_id": cand.student_user_id, "score": 88.0, "recommendation_status": "recommended"}],
        actor=committee_member,
    )
    # Publishing without approval fails with ConflictError
    with pytest.raises(ConflictError):
        award_service.publish_award_results(award_cycle_id=cycle.id, actor=convener)


# ==============================================================================
# 2. COMPOSITE LIFECYCLES (CW-SPACS-01 .. CW-SPACS-03)
# ==============================================================================

def test_wf_cw_01_end2end(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-WF-CW-01-END2END | CW-SPACS-01: Scholarship Application Lifecycle.
    Full composition: Draft -> Document Attached -> Submit -> Under Verification -> Verified -> Approved.
    """
    draft = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(
        application_id=draft.id,
        student_user_id=student.user_id,
        doc_type="income_certificate",
        title="Income 2024",
        file_url="/cw1/inc.pdf",
        valid_until=timezone.now().date() + timedelta(days=90),
        actor=student,
    )
    doc_service.attach_document(
        application_id=draft.id,
        student_user_id=student.user_id,
        doc_type="grade_card",
        title="Grade Card 2024",
        file_url="/cw1/gc.pdf",
        valid_until=timezone.now().date() + timedelta(days=90),
        actor=student,
    )
    sub = app_service.submit_application(
        application_id=draft.id,
        student_facts={"cpi": 8.9, "parental_income": 250000.0},
        actor=student,
    )
    app_service.verify_application(application_id=sub.id, action_type="start", actor=assistant)
    ver = app_service.verify_application(application_id=sub.id, action_type="verify", actor=assistant)
    appr = app_service.decide_application(
        application_id=ver.id, decision="approve", reason="Full criteria met", actor=convener
    )
    assert appr.status == "approved"
    assert ApplicationTransition.objects.filter(application=appr).count() >= 3


def test_wf_cw_02_end2end(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-WF-CW-02-END2END | CW-SPACS-02: Scholarship Renewal Lifecycle.
    Full composition: Prior Approved -> Renewal Application -> Assistant Verification -> Convener Approval.
    """
    prior = ScholarshipApplication.objects.create(
        application_number="SPACS-CW02-PRIOR",
        student_user_id=student.user_id,
        scheme=scheme_mcm,
        policy_version=policy_mcm,
        academic_cycle="2023-24",
        status="approved",
    )
    renewal = app_service.submit_renewal(
        prior_application_id=prior.id,
        academic_cycle="2024-25",
        current_facts={"cpi": 8.4, "active_backlogs": 0},
        actor=student,
    )
    app_service.verify_application(application_id=renewal.id, action_type="start", actor=assistant)
    ver = app_service.verify_application(application_id=renewal.id, action_type="verify", actor=assistant)
    appr = app_service.decide_application(
        application_id=ver.id, decision="approve", reason="Renewal verified", actor=convener
    )
    assert appr.status == "approved"
    assert appr.is_renewal is True


def test_wf_cw_03_end2end(convener, committee_member, award_scheme, award_policy):
    """TC-WF-CW-03-END2END | CW-SPACS-03: Convocation Award Lifecycle.
    Full composition: Create Cycle -> Prepare Pool -> Committee Evaluation -> Senate Approval -> Public Release.
    """
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id, candidates=[{"student_user_id": 3001, "cpi": 9.8}], actor=convener
    )
    cand = AwardCandidate.objects.filter(award_cycle=cycle).first()
    award_service.record_committee_evaluations(
        award_cycle_id=cycle.id,
        evaluations=[{"student_user_id": cand.student_user_id, "score": 98.0, "recommendation_status": "recommended"}],
        actor=committee_member,
    )
    award_service.record_final_approval(
        award_cycle_id=cycle.id, approval_reference="SEN/CW03", approving_authority="Senate",
        approved_candidate_ids=[3001], actor=convener
    )
    pub = award_service.publish_award_results(award_cycle_id=cycle.id, actor=convener)
    assert pub.status == "published"


# ==============================================================================
# 3. WORKFLOW DECISION BRANCHES (BRANCH-01 .. BRANCH-10)
# ==============================================================================

def test_wf_branch_01(student, assistant, scheme_mcm, policy_mcm):
    """TC-WF-BRANCH-01 | BW-SPACS-01 assistant-reject-path: Assistant cannot make terminal approval/rejection."""
    draft = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Income Cert", file_url="/u/inc.pdf", actor=student
    )
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="grade_card",
        title="Grade Card", file_url="/u/gc.pdf", actor=student
    )
    sub = app_service.submit_application(
        application_id=draft.id,
        student_facts={"cpi": 8.0, "parental_income": 300000.0},
        actor=student,
    )
    app_service.verify_application(application_id=sub.id, action_type="start", actor=assistant)
    with pytest.raises(PermissionDeniedError):
        app_service.decide_application(application_id=sub.id, decision="reject", actor=assistant)


def test_wf_branch_02(student, assistant, scheme_mcm, policy_mcm):
    """TC-WF-BRANCH-02 | BW-SPACS-02 multi-cycle-correction-path: Multiple correction iterations."""
    draft = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Income Cert", file_url="/u/inc.pdf", actor=student
    )
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="grade_card",
        title="Grade Card", file_url="/u/gc.pdf", actor=student
    )
    sub = app_service.submit_application(
        application_id=draft.id,
        student_facts={"cpi": 8.5, "parental_income": 300000.0},
        actor=student,
    )
    # Cycle 1
    app_service.verify_application(application_id=sub.id, action_type="start", actor=assistant)
    c1 = app_service.verify_application(
        application_id=sub.id, action_type="request_correction", reason="Fix income certificate format", actor=assistant
    )
    r1 = app_service.modify_application(
        application_id=c1.id,
        updated_data={"cpi": 8.5, "parental_income": 300000.0},
        resubmit=True,
        actor=student,
    )
    # Cycle 2
    app_service.verify_application(application_id=r1.id, action_type="start", actor=assistant)
    c2 = app_service.verify_application(
        application_id=r1.id, action_type="request_correction", reason="Fix page 2 stamp", actor=assistant
    )
    assert c2.status == "correction_required"


def test_wf_branch_03(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-WF-BRANCH-03 | BW-SPACS-03 conditional-approval-path: Convener conditional approval with remarks."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-BW-BR03",
        student_user_id=student.user_id,
        scheme=scheme_mcm,
        policy_version=policy_mcm,
        academic_cycle="2024-25",
        status="verified",
    )
    appr = app_service.decide_application(
        application_id=app.id, decision="approve", reason="Approved conditional on semester 6 marksheet submission", actor=convener
    )
    assert appr.status == "approved"
    assert "conditional" in appr.decision_reason


def test_wf_branch_04(student, convener, scheme_mcm, policy_mcm):
    """TC-WF-BRANCH-04 | BW-SPACS-04 final-rejection-appeal-path: Convener rejection recorded in transition."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-BW-BR04",
        student_user_id=student.user_id,
        scheme=scheme_mcm,
        policy_version=policy_mcm,
        academic_cycle="2024-25",
        status="verified",
    )
    rej = app_service.decide_application(
        application_id=app.id, decision="reject", reason="Annual parental income exceeds statutory threshold", actor=convener
    )
    assert rej.status == "rejected"
    t = ApplicationTransition.objects.filter(application=rej, to_status="rejected").first()
    assert t is not None


def test_wf_branch_05(student, assistant, scheme_mcm, policy_mcm):
    """TC-WF-BRANCH-05 | BW-SPACS-05 post-verification-withdrawal-path: Withdrawal allowed from verified state."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-BW-BR05",
        student_user_id=student.user_id,
        scheme=scheme_mcm,
        policy_version=policy_mcm,
        academic_cycle="2024-25",
        status="verified",
    )
    w = app_service.withdraw_application(
        application_id=app.id, reason="Relocating to another university", actor=student
    )
    assert w.status == "withdrawn"


def test_wf_branch_06(student, assistant, scheme_mcm, policy_mcm):
    """TC-WF-BRANCH-06 | BW-SPACS-06 concern-escalation-path: Escalation notification to Convener.

    CANDIDATE DEFECT (DEF-04): When an assistant flags a verification concern, the system
    logs the audit event and changes status to verification_concern, but fails to dispatch
    an escalation notification to the SPACS Convener outbox as required by CFR-SPACS-015 and BW-SPACS-06.
    """
    draft = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Income Cert", file_url="/u/inc.pdf", actor=student
    )
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="grade_card",
        title="Grade Card", file_url="/u/gc.pdf", actor=student
    )
    sub = app_service.submit_application(
        application_id=draft.id,
        student_facts={"cpi": 8.5, "parental_income": 300000.0},
        actor=student,
    )
    app_service.verify_application(application_id=sub.id, action_type="start", actor=assistant)
    concern = app_service.verify_application(
        application_id=sub.id,
        action_type="record_concern",
        reason="Discrepancy in parental salary slip and tax form",
        actor=assistant,
    )
    assert concern.status == "verification_concern"

    # Specification requirement (CFR-SPACS-015, BW-SPACS-06):
    # An escalation notification MUST be dispatched to the SPACS Convener
    convener_notes = SpacsNotification.objects.filter(
        reference_id=str(concern.id),
        recipient_role__in=["convener", "spacs_convener"],
    )
    if not convener_notes.exists():
        raise AssertionError("Escalation notification not dispatched to Convener upon verification concern (DEF-04)")


def test_wf_branch_07(student, scheme_mcm, policy_mcm):
    """TC-WF-BRANCH-07 | BW-SPACS-07 renewal-disqualification-path: Renewal disqualified for backlogs."""
    prior = ScholarshipApplication.objects.create(
        application_number="SPACS-BW-BR07-PRIOR",
        student_user_id=student.user_id,
        scheme=scheme_mcm,
        policy_version=policy_mcm,
        academic_cycle="2023-24",
        status="approved",
    )
    with pytest.raises(ConflictError) as exc:
        app_service.submit_renewal(
            prior_application_id=prior.id,
            academic_cycle="2024-25",
            current_facts={"cpi": 8.0, "active_backlogs": 2},
            actor=student,
        )
    assert "active backlogs" in str(exc.value)


def test_wf_branch_08(convener, award_scheme, award_policy):
    """TC-WF-BRANCH-08 | BW-SPACS-08 manual-nomination-addition-path: Manual nomination addition to pool."""
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id,
        candidates=[{"student_user_id": 4001, "cpi": 9.1, "source_method": "manual_nomination", "discipline": "CSE"}],
        actor=convener,
    )
    cand = AwardCandidate.objects.filter(award_cycle=cycle, student_user_id=4001).first()
    assert cand is not None
    assert cand.source_method == "manual_nomination"


def test_wf_branch_09(convener, committee_member, award_scheme, award_policy):
    """TC-WF-BRANCH-09 | BW-SPACS-09 committee-split-recommendation-path: Committee records non-unanimous scores."""
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id, candidates=[{"student_user_id": 5001, "cpi": 9.3}], actor=convener
    )
    cand = AwardCandidate.objects.filter(award_cycle=cycle, student_user_id=5001).first()
    res = award_service.record_committee_evaluations(
        award_cycle_id=cycle.id,
        evaluations=[{"student_user_id": cand.student_user_id, "score": 55.0, "recommendation_status": "not_recommended"}],
        actor=committee_member,
    )
    cand.refresh_from_db()
    assert cand.recommendation_status == "not_recommended"


def test_wf_branch_10(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-WF-BRANCH-10 | CW-SPACS-01 application-correction-resubmission-lifecycle complete path."""
    draft = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Income Cert", file_url="/u/inc.pdf", actor=student
    )
    doc_service.attach_document(
        application_id=draft.id, student_user_id=student.user_id, doc_type="grade_card",
        title="Grade Card", file_url="/u/gc.pdf", actor=student
    )
    sub = app_service.submit_application(
        application_id=draft.id,
        student_facts={"cpi": 8.5, "parental_income": 300000.0},
        actor=student,
    )
    app_service.verify_application(application_id=sub.id, action_type="start", actor=assistant)
    corr = app_service.verify_application(
        application_id=sub.id, action_type="request_correction", reason="Update document", actor=assistant
    )
    resub = app_service.modify_application(
        application_id=corr.id,
        updated_data={"cpi": 8.5, "parental_income": 300000.0},
        resubmit=True,
        actor=student,
    )
    app_service.verify_application(application_id=resub.id, action_type="start", actor=assistant)
    ver = app_service.verify_application(application_id=resub.id, action_type="verify", actor=assistant)
    appr = app_service.decide_application(
        application_id=ver.id, decision="approve", reason="Resubmission verified and approved", actor=convener
    )
    assert appr.status == "approved"
