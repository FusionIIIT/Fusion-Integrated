"""Use Case (UC) test suite for SPACS (UC-SPACS-001..026)."""
import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.spacs.models import (
    ApplicationDocument, AwardCandidate, AwardCycle, ScholarshipApplication,
    SchemeCatalogue, SchemePolicyVersion, SpacsAuditLog, SpacsNotification,
)
from modules.spacs.services import (
    applications as app_service, awards as award_service,
    catalogue as cat_service, documents as doc_service, tasks as task_service,
)
from modules.spacs import contracts

pytestmark = pytest.mark.django_db


# --- UC-SPACS-001: Apply for Scholarship ---
def test_uc_001_main_flow(student, scheme_mcm, policy_mcm):
    """TC-UC-001-MAIN | UC-SPACS-001 Main Flow: Student applies for scholarship successfully."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    submitted = app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    assert submitted.status == "submitted"


def test_uc_001_alt_a1_dup(student, scheme_mcm, policy_mcm):
    """TC-UC-001-Alt_A1 | UC-SPACS-001 Alt A1: Duplicate draft application rejected.

    CANDIDATE DEFECT (DEF-01): System should reject second active draft in cycle.
    """
    d1 = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    d1.application_number = "SPACS-DRAFT-UC-1"
    d1.save(update_fields=["application_number"])
    with pytest.raises(ConflictError) as exc:
        d2 = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
        if d2 is not None:
            raise AssertionError("Implementation permitted multiple active drafts for same scheme and cycle (DEF-01)")
    assert "duplicate" in str(exc.value).lower()


# --- UC-SPACS-002: Verify Scholarship Application ---
def test_uc_002_main_flow(student, assistant, scheme_mcm, policy_mcm):
    """TC-UC-002-MAIN | UC-SPACS-002 Main Flow: Assistant verifies application without issues."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    v = app_service.verify_application(application_id=app.id, action_type="verify", findings={"ok": True}, actor=assistant)
    assert v.status == "verified"


def test_uc_002_alt_a1_correction(student, assistant, scheme_mcm, policy_mcm):
    """TC-UC-002-Alt_A1 | UC-SPACS-002 Alt A1: Assistant requests correction."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    v = app_service.verify_application(application_id=app.id, action_type="request_correction", reason="Re-upload certificate", actor=assistant)
    assert v.status == "correction_required"


def test_uc_002_exc_e1_concern(student, assistant, scheme_mcm, policy_mcm):
    """TC-UC-002-Exc_E1 | UC-SPACS-002 Exc E1: Assistant records verification concern."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    v = app_service.verify_application(application_id=app.id, action_type="record_concern", reason="Suspicious seal", actor=assistant)
    assert v.verification_concern_details == "Suspicious seal"


# --- UC-SPACS-003: Modify / Correct Pending Application ---
def test_uc_003_main_flow(student, assistant, scheme_mcm, policy_mcm):
    """TC-UC-003-MAIN | UC-SPACS-003 Main Flow: Student updates and resubmits application."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="request_correction", reason="Re-upload", actor=assistant)
    mod = app_service.modify_application(application_id=app.id, updated_data={"note": "Fixed"}, resubmit=True, actor=student)
    assert mod.status == "resubmitted"


def test_uc_003_alt_a2_resubmit_facts(student, assistant, scheme_mcm, policy_mcm):
    """TC-UC-003-Alt_A1 | UC-SPACS-003 Alt A1: Resubmission re-evaluates eligibility snapshot.

    CANDIDATE DEFECT (DEF-02): Student corrects income facts during resubmission,
    but modify_application fails to re-evaluate criteria and refresh eligibility_snapshot.
    """
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 500000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="request_correction", reason="Check updated income", actor=assistant)
    # Student modifies income to 300000
    mod = app_service.modify_application(application_id=app.id, updated_data={"parental_income": 300000.0}, resubmit=True, actor=student)
    # Expected: snapshot should be re-evaluated reflecting updated parental income
    snapshot = mod.eligibility_snapshot or {}
    outcomes = {o.get("criterion"): o.get("actual") for o in snapshot.get("outcomes", [])}
    if outcomes.get("max_parental_income") != 300000.0:
        raise AssertionError("Stale eligibility snapshot: not re-evaluated upon correction resubmission (DEF-02)")


# --- UC-SPACS-004: Withdraw Application ---
def test_uc_004_main_flow(student, scheme_mcm, policy_mcm):
    """TC-UC-004-MAIN | UC-SPACS-004 Main Flow: Student withdraws submitted application."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    w = app_service.withdraw_application(application_id=app.id, reason="Changed mind", actor=student)
    assert w.status == "withdrawn"


def test_uc_004_alt_a1_terminal_withdraw_blocked(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-UC-004-Alt_A1 | UC-SPACS-004 Alt A1: Cannot withdraw after approval."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="verify", actor=assistant)
    app_service.decide_application(application_id=app.id, decision="approve", actor=convener)
    with pytest.raises(ConflictError):
        app_service.withdraw_application(application_id=app.id, reason="Late cancel", actor=student)


# --- UC-SPACS-006: Make Scholarship Decision ---
def test_uc_006_main_flow_approve(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-UC-006-MAIN | UC-SPACS-006 Main Flow: Convener approves scholarship."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="verify", actor=assistant)
    decided = app_service.decide_application(application_id=app.id, decision="approve", actor=convener)
    assert decided.status == "approved"


def test_uc_006_alt_a1_reject(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-UC-006-Alt_A1 | UC-SPACS-006 Alt A1: Convener rejects scholarship."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="verify", actor=assistant)
    decided = app_service.decide_application(application_id=app.id, decision="reject", reason="Criteria rank", actor=convener)
    assert decided.status == "rejected"


def test_uc_006_exc_e1_return_correction(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-UC-006-Exc_E1 | UC-SPACS-006 Exc E1: Convener returns for correction."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="verify", actor=assistant)
    app.status = "under_convener_review"
    app.save(update_fields=["status"])
    decided = app_service.decide_application(application_id=app.id, decision="return_correction", reason="Check salary", actor=convener)
    assert decided.status == "correction_required"


# --- UC-SPACS-007: Download / Print Application ---
def test_uc_007_main_flow(student, scheme_mcm, policy_mcm):
    """TC-UC-007-MAIN | UC-SPACS-007 Main Flow: Download/export application summary."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    from modules.spacs.selectors.applications import get_application
    rec = get_application(app.id, student)
    assert rec is not None


# --- UC-SPACS-008: Check Application Status ---
def test_uc_008_main_flow(student, scheme_mcm, policy_mcm):
    """TC-UC-008-MAIN | UC-SPACS-008 Main Flow: Check own application status."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    from modules.spacs.selectors.applications import visible_applications
    apps = visible_applications(student)
    assert apps.filter(id=app.id).exists()


# --- UC-SPACS-010: Create Catalogue Entry ---
def test_uc_010_main_flow(convener):
    """TC-UC-010-MAIN | UC-SPACS-010 Main Flow: Convener creates scheme catalogue entry."""
    scheme = cat_service.create_catalogue_entry(code="SCHEME_UC10", name="UC Scheme", scheme_type="scholarship", actor=convener)
    assert scheme.status == "draft"


def test_uc_010_alt_a1_dup_code(convener, scheme_mcm):
    """TC-UC-010-Alt_A1 | UC-SPACS-010 Alt A1: Duplicate scheme code rejected."""
    with pytest.raises(ConflictError):
        cat_service.create_catalogue_entry(code="MCM_A8", name="Duplicate", scheme_type="scholarship", actor=convener)


# --- UC-SPACS-011: Modify Catalogue Entry / Version ---
def test_uc_011_main_flow(convener, scheme_mcm, policy_mcm):
    """TC-UC-011-MAIN | UC-SPACS-011 Main Flow: Create draft policy version."""
    v = cat_service.create_policy_version(scheme_id=scheme_mcm.id, title="v2 Criteria", actor=convener)
    assert v.version_number == 2


def test_uc_011_alt_a1_criteria_override(convener, scheme_mcm, policy_mcm):
    """TC-UC-011-Alt_A1 | UC-SPACS-011 Alt A1: Modify eligibility parameters."""
    v = cat_service.create_policy_version(scheme_id=scheme_mcm.id, title="v3 Higher CPI", eligibility_criteria={"min_cpi": 8.0}, actor=convener)
    assert v.eligibility_criteria["min_cpi"] == 8.0


# --- UC-SPACS-012: Retire / Deactivate Catalogue Entry ---
def test_uc_012_main_flow(convener, scheme_mcm):
    """TC-UC-012-MAIN | UC-SPACS-012 Main Flow: Retire catalogue entry prospectively."""
    ret = cat_service.retire_catalogue_entry(scheme_id=scheme_mcm.id, reason="End of cycle", actor=convener)
    assert ret.status == "retired"


def test_uc_012_alt_a1_already_retired(convener, scheme_mcm):
    """TC-UC-012-Alt_A1 | UC-SPACS-012 Alt A1: Retiring already retired scheme is idempotent."""
    cat_service.retire_catalogue_entry(scheme_id=scheme_mcm.id, reason="Retired 1", actor=convener)
    ret2 = cat_service.retire_catalogue_entry(scheme_id=scheme_mcm.id, reason="Retired 2", actor=convener)
    assert ret2.status == "retired"


# --- UC-SPACS-014: Browse Catalogue ---
def test_uc_014_main_flow(student, scheme_mcm, policy_mcm):
    """TC-UC-014-MAIN | UC-SPACS-014 Main Flow: Browse catalogue."""
    from modules.spacs.selectors.catalogue import visible_catalogue_entries
    assert visible_catalogue_entries(student).filter(code="MCM_A8").exists()


# --- UC-SPACS-015: Apply for Scholarship Renewal ---
def test_uc_015_main_flow(student, scheme_mcm, policy_mcm):
    """TC-UC-015-MAIN | UC-SPACS-015 Main Flow: Student renews awarded scholarship."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-PRIOR-AWARD", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="approved"
    )
    ren = app_service.submit_renewal(prior_application_id=app.id, academic_cycle="2024-25", current_facts={"cpi": 8.0, "active_backlogs": 0}, actor=student)
    assert ren.is_renewal is True


def test_uc_015_alt_a1_ineligible_backlogs(student, scheme_mcm, policy_mcm):
    """TC-UC-015-Alt_A1 | UC-SPACS-015 Alt A1: Renewal rejected due to backlogs."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-PRIOR-AWARD-2", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="approved"
    )
    with pytest.raises(ConflictError):
        app_service.submit_renewal(prior_application_id=app.id, academic_cycle="2024-25", current_facts={"cpi": 8.0, "active_backlogs": 1}, actor=student)


def test_uc_015_exc_e1_prior_not_approved(student, scheme_mcm, policy_mcm):
    """TC-UC-015-Exc_E1 | UC-SPACS-015 Exc E1: Cannot renew rejected application."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-PRIOR-REJ", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="rejected"
    )
    with pytest.raises(ConflictError):
        app_service.submit_renewal(prior_application_id=app.id, academic_cycle="2024-25", current_facts={"cpi": 8.0}, actor=student)


# --- UC-SPACS-017: Prepare Award Candidate Pool ---
def test_uc_017_main_flow(convener, award_scheme, award_policy):
    """TC-UC-017-MAIN | UC-SPACS-017 Main Flow: Prepare award candidate pool."""
    cycle = award_service.create_award_cycle(scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025, evaluating_body="Senate", actor=convener)
    c = award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.5}], actor=convener)
    assert c.status == "pool_prepared"


def test_uc_017_alt_a1_empty_pool(convener, award_scheme, award_policy):
    """TC-UC-017-Alt_A1 | UC-SPACS-017 Alt A1: Candidate pool with no initial nominees rejected."""
    cycle = award_service.create_award_cycle(scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025, evaluating_body="Senate", actor=convener)
    with pytest.raises(ConflictError) as exc:
        award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=[], actor=convener)
    assert "empty_pool" in str(exc.value) or "at least one candidate" in str(exc.value).lower()


# --- UC-SPACS-018: Evaluate and Shortlist Award Candidates ---
def test_uc_018_main_flow(convener, committee_member, award_scheme, award_policy):
    """TC-UC-018-MAIN | UC-SPACS-018 Main Flow: Committee scores candidates."""
    cycle = award_service.create_award_cycle(scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025, evaluating_body="Senate", actor=convener)
    award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.5}], actor=convener)
    evals = [{"student_user_id": 1001, "score": 98.0, "recommendation_status": "recommended"}]
    res = award_service.record_committee_evaluations(award_cycle_id=cycle.id, evaluations=evals, actor=committee_member)
    assert res.status == "result_recorded"


def test_uc_018_alt_a1_shortlist_filter(convener, committee_member, award_scheme, award_policy):
    """TC-UC-018-Alt_A1 | UC-SPACS-018 Alt A1: Shortlist selected candidate subset."""
    cycle = award_service.create_award_cycle(scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025, evaluating_body="Senate", actor=convener)
    award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.5}], actor=convener)
    evals = [{"student_user_id": 1001, "score": 90.0, "is_shortlisted": True}]
    res = award_service.record_committee_evaluations(award_cycle_id=cycle.id, evaluations=evals, actor=committee_member)
    assert AwardCandidate.objects.get(award_cycle=cycle, student_user_id=1001).is_shortlisted is True


# --- UC-SPACS-019: Record Final Award Outcome ---
def test_uc_019_main_flow(convener, committee_member, award_scheme, award_policy):
    """TC-UC-019-MAIN | UC-SPACS-019 Main Flow: Senate approves award results."""
    cycle = award_service.create_award_cycle(scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025, evaluating_body="Senate", actor=convener)
    award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.5}], actor=convener)
    award_service.record_committee_evaluations(award_cycle_id=cycle.id, evaluations=[{"student_user_id": 1001, "score": 98.0}], actor=committee_member)
    approved = award_service.record_final_approval(award_cycle_id=cycle.id, approval_reference="SEN/19", approving_authority="Senate", approved_candidate_ids=[1001], actor=convener)
    assert approved.status == "ready_for_publication"


def test_uc_019_alt_a1_pending_approval_flag(convener, committee_member, award_scheme, award_policy):
    """TC-UC-019-Alt_A1 | UC-SPACS-019 Alt A1: Awaiting approval when reference empty."""
    cycle = award_service.create_award_cycle(scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025, evaluating_body="Senate", actor=convener)
    award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.5}], actor=convener)
    award_service.record_committee_evaluations(award_cycle_id=cycle.id, evaluations=[{"student_user_id": 1001, "score": 98.0}], actor=committee_member)
    awaiting = award_service.record_final_approval(award_cycle_id=cycle.id, approval_reference="", actor=convener)
    assert awaiting.status == "awaiting_approval"


# --- UC-SPACS-020: Publish Award Results ---
def test_uc_020_main_flow(convener, committee_member, award_scheme, award_policy):
    """TC-UC-020-MAIN | UC-SPACS-020 Main Flow: Publish approved awards."""
    cycle = award_service.create_award_cycle(scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025, evaluating_body="Senate", actor=convener)
    award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.5}], actor=convener)
    award_service.record_committee_evaluations(award_cycle_id=cycle.id, evaluations=[{"student_user_id": 1001, "score": 98.0}], actor=committee_member)
    award_service.record_final_approval(award_cycle_id=cycle.id, approval_reference="SEN/20", approving_authority="Senate", approved_candidate_ids=[1001], actor=convener)
    pub = award_service.publish_award_results(award_cycle_id=cycle.id, actor=convener)
    assert pub.status == "published"


def test_uc_020_alt_a1_unapproved_publish_blocked(convener, award_scheme, award_policy):
    """TC-UC-020-Alt_A1 | UC-SPACS-020 Alt A1: Cannot publish unapproved cycle."""
    cycle = award_service.create_award_cycle(scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025, evaluating_body="Senate", actor=convener)
    with pytest.raises(ConflictError):
        award_service.publish_award_results(award_cycle_id=cycle.id, actor=convener)


# --- UC-SPACS-021: View SPACS Audit Trail ---
def test_uc_021_main_flow(convener):
    """TC-UC-021-MAIN | UC-SPACS-021 Main Flow: Authorized convener views audit logs."""
    from modules.spacs.selectors.audit import visible_audit_logs
    assert visible_audit_logs(convener) is not None


def test_uc_021_alt_a1_unauthorized_audit_view(student):
    """TC-UC-021-Alt_A1 | UC-SPACS-021 Alt A1: Student has no access to full audit logs."""
    from modules.spacs.selectors.audit import visible_audit_logs
    assert visible_audit_logs(student).count() == 0


# --- UC-SPACS-023: Publish / Activate Catalogue Version ---
def test_uc_023_main_flow(convener, scheme_mcm):
    """TC-UC-023-MAIN | UC-SPACS-023 Main Flow: Publish valid policy version."""
    v = cat_service.create_policy_version(
        scheme_id=scheme_mcm.id, title="v2 Approved", policy_approval_reference="BOG/RES/12",
        policy_approved_by="Senate", effective_from=timezone.now().date(), actor=convener
    )
    pub = cat_service.publish_policy_version(version_id=v.id, actor=convener)
    assert pub.status == "published"


def test_uc_023_alt_a1_missing_provenance(convener, scheme_mcm):
    """TC-UC-023-Alt_A1 | UC-SPACS-023 Alt A1: Publish blocked without approval reference."""
    v = cat_service.create_policy_version(scheme_id=scheme_mcm.id, title="v2 Unapproved", actor=convener)
    with pytest.raises(ConflictError):
        cat_service.publish_policy_version(version_id=v.id, actor=convener)


# --- UC-SPACS-024: Issue SLA Reminder / Escalation ---
def test_uc_024_main_flow(student, assistant, scheme_mcm, policy_mcm):
    """TC-UC-024-MAIN | UC-SPACS-024 Main Flow: SLA reminder triggered for overdue verification."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    ScholarshipApplication.objects.filter(id=app.id).update(submitted_at=timezone.now() - timedelta(days=12))
    count = task_service.send_sla_reminders()
    assert count >= 1


def test_uc_024_alt_a1_no_overdue_tasks(scheme_mcm, policy_mcm):
    """TC-UC-024-Alt_A1 | UC-SPACS-024 Alt A1: No reminders sent when all tasks are within SLA."""
    ScholarshipApplication.objects.all().delete()
    count = task_service.send_sla_reminders()
    assert count == 0


# --- UC-SPACS-025: Send Scholarship Renewal Reminder ---
def test_uc_025_main_flow(student, scheme_mcm, policy_mcm):
    """TC-UC-025-MAIN | UC-SPACS-025 Main Flow: Renewal reminders dispatched to prior awardees."""
    ScholarshipApplication.objects.create(
        application_number="SPACS-PRIOR-REM", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="approved"
    )
    count = task_service.send_renewal_reminders()
    assert count >= 1


def test_uc_025_alt_a1_window_closed_no_reminders(student, scheme_mcm, policy_mcm):
    """TC-UC-025-Alt_A1 | UC-SPACS-025 Alt A1: No renewal reminders when window is not open."""
    policy_mcm.renewal_window_start = timezone.now() + timedelta(days=10)
    policy_mcm.save(update_fields=["renewal_window_start"])
    count = task_service.send_renewal_reminders()
    assert count == 0


# --- UC-SPACS-026: Reassign Pending Role-Based Tasks ---
def test_uc_026_main_flow(student, assistant, scheme_mcm, policy_mcm):
    """TC-UC-026-MAIN | UC-SPACS-026 Main Flow: Reassign pending assistant tasks."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    ScholarshipApplication.objects.filter(id=app.id).update(assigned_assistant_user_id=assistant.user_id)
    reassigned = task_service.reassign_pending_tasks(role_code="spacs_assistant", from_user_id=assistant.user_id, to_user_id=2003)
    assert reassigned >= 1


def test_uc_026_alt_a1_no_matching_pending(assistant):
    """TC-UC-026-Alt_A1 | UC-SPACS-026 Alt A1: Reassignment when user has no pending tasks."""
    reassigned = task_service.reassign_pending_tasks(role_code="spacs_assistant", from_user_id=9999, to_user_id=2003)
    assert reassigned == 0
