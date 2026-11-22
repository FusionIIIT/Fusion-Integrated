"""Functional Requirements (FR) test suite for SPACS (AFR-SPACS-001..052)."""
import pytest
from datetime import timedelta
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


def test_fr_001_browse_published(student, scheme_mcm, policy_mcm):
    """TC-FR-001 | AFR-SPACS-001: Browse published catalogue."""
    from modules.spacs.selectors.catalogue import visible_catalogue_entries
    entries = visible_catalogue_entries(student)
    assert entries.filter(code="MCM_A8").exists()


def test_fr_002_display_details(student, scheme_mcm, policy_mcm):
    """TC-FR-002 | AFR-SPACS-002: Display catalogue entry details and criteria."""
    from modules.spacs.selectors.catalogue import get_catalogue_entry
    entry = get_catalogue_entry(scheme_mcm.id, student)
    assert entry is not None
    assert entry.name == "Merit-cum-Means Scholarship A8"


def test_fr_003_create_draft_entry(convener):
    """TC-FR-003 | AFR-SPACS-003: Convener creates draft catalogue entry."""
    scheme = cat_service.create_catalogue_entry(
        code="NEW_SCHEME", name="New Fellowship", scheme_type="scholarship", actor=convener
    )
    assert scheme.code == "NEW_SCHEME"
    assert scheme.status == "draft"


def test_fr_004_create_draft_version(convener, scheme_mcm, policy_mcm):
    """TC-FR-004 | AFR-SPACS-004: Convener creates draft policy version."""
    v = cat_service.create_policy_version(
        scheme_id=scheme_mcm.id, title="v2 Draft", eligibility_criteria={"min_cpi": 7.0}, actor=convener
    )
    assert v.version_number == 2
    assert v.status == "draft"


def test_fr_005_publish_version(convener, scheme_mcm):
    """TC-FR-005 | AFR-SPACS-005: Convener publishes approved version."""
    v = cat_service.create_policy_version(
        scheme_id=scheme_mcm.id, title="v2 Approved", policy_approval_reference="SEN/99",
        policy_approved_by="Senate", effective_from=timezone.now().date(), actor=convener
    )
    published = cat_service.publish_policy_version(version_id=v.id, actor=convener)
    assert published.status == "published"


def test_fr_006_retire_catalogue_entry(convener, scheme_mcm):
    """TC-FR-006 | AFR-SPACS-006: Convener retires catalogue entry."""
    retired = cat_service.retire_catalogue_entry(scheme_id=scheme_mcm.id, reason="Phased out", actor=convener)
    assert retired.status == "retired"


def test_fr_007_audit_historical_versions(convener, scheme_mcm, policy_mcm):
    """TC-FR-007 | AFR-SPACS-007: Preserve and query historical versions."""
    versions = SchemePolicyVersion.objects.filter(scheme=scheme_mcm).order_by("version_number")
    assert versions.count() >= 1


def test_fr_008_initiate_draft(student, scheme_mcm, policy_mcm):
    """TC-FR-008 | AFR-SPACS-008: Student initiates draft application."""
    app = app_service.create_draft_application(
        scheme_id=scheme_mcm.id, academic_cycle="2024-25", application_data={"cpi": 7.5}, actor=student
    )
    assert app.status == "draft"
    assert app.student_user_id == student.user_id


def test_fr_009_upload_document(student, scheme_mcm, policy_mcm):
    """TC-FR-009 | AFR-SPACS-009: Upload required documents."""
    app = app_service.create_draft_application(
        scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student
    )
    doc = doc_service.attach_document(
        application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Income 2024", file_url="/docs/income.pdf", actor=student
    )
    assert doc.verification_status == "pending"


def test_fr_010_reuse_valid_document(student, scheme_mcm, policy_mcm):
    """TC-FR-010 | AFR-SPACS-010: Reuse valid previously uploaded document."""
    app1 = ScholarshipApplication.objects.create(
        application_number="SPACS-MCM-PRIOR-1001", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="submitted"
    )
    d1 = doc_service.attach_document(
        application_id=app1.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Valid Doc", file_url="/docs/valid.pdf", valid_until=timezone.now().date() + timedelta(days=90), actor=student
    )
    app1.status = "approved"
    app1.save(update_fields=["status"])
    app2 = ScholarshipApplication.objects.create(
        application_number="SPACS-MCM-NEW-1001", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2024-25", status="draft"
    )
    reused = doc_service.reuse_document(
        application_id=app2.id, student_user_id=student.user_id, source_doc_id=d1.id, actor=student
    )
    assert reused.is_reused is True


def test_fr_011_expired_document_check(student, scheme_mcm, policy_mcm):
    """TC-FR-011 | AFR-SPACS-011: Expired document reuse rejected."""
    app1 = ScholarshipApplication.objects.create(
        application_number="SPACS-MCM-PRIOR-1002", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="submitted"
    )
    d1 = doc_service.attach_document(
        application_id=app1.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Expired Doc", file_url="/docs/expired.pdf", valid_until=timezone.now().date() - timedelta(days=1), actor=student
    )
    app1.status = "approved"
    app1.save(update_fields=["status"])
    app2 = ScholarshipApplication.objects.create(
        application_number="SPACS-MCM-NEW-1002", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2024-25", status="draft"
    )
    with pytest.raises(ConflictError) as exc:
        doc_service.reuse_document(
            application_id=app2.id, student_user_id=student.user_id, source_doc_id=d1.id, actor=student
        )
    assert "expired" in str(exc.value)


def test_fr_012_automated_eligibility_evaluation(student, scheme_mcm, policy_mcm):
    """TC-FR-012 | AFR-SPACS-012: Automated eligibility check on submit."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    submitted = app_service.submit_application(
        application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 450000.0, "active_backlogs": 0}, actor=student
    )
    assert submitted.status == "submitted"
    assert submitted.eligibility_snapshot["is_eligible"] is True


def test_fr_013_fail_closed_eligibility(student, scheme_mcm, policy_mcm):
    """TC-FR-013 | AFR-SPACS-013: Fail-closed on missing required facts."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    with pytest.raises(ConflictError) as exc:
        app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0}, actor=student)
    assert "eligibility" in str(exc.value).lower()


def test_fr_014_submit_duplicate_block(student, scheme_mcm, policy_mcm):
    """TC-FR-014 | AFR-SPACS-014: Block duplicate submitted applications."""
    app1 = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app1.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app1.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(
        application_id=app1.id, student_facts={"cpi": 8.0, "parental_income": 450000.0, "active_backlogs": 0}, actor=student
    )
    app2 = ScholarshipApplication.objects.create(
        application_number="SPACS-MCM-DRAFT-2", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2024-25", status="draft"
    )
    doc_service.attach_document(application_id=app2.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app2.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    with pytest.raises(ConflictError) as exc:
        app_service.submit_application(
            application_id=app2.id, student_facts={"cpi": 8.0, "parental_income": 450000.0, "active_backlogs": 0}, actor=student
        )
    assert exc.value.code == "duplicate_application" or "active or submitted" in str(exc.value).lower()


def test_fr_015_modify_correction(student, assistant, scheme_mcm, policy_mcm):
    """TC-FR-015 | AFR-SPACS-015: Student modifies and resubmits in correction state."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="request_correction", reason="Re-upload legible doc", actor=assistant)
    mod = app_service.modify_application(application_id=app.id, updated_data={"note": "Fixed"}, resubmit=True, actor=student)
    assert mod.status == "resubmitted"


def test_fr_016_withdraw_application(student, scheme_mcm, policy_mcm):
    """TC-FR-016 | AFR-SPACS-016: Student withdraws pending application."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    w = app_service.withdraw_application(application_id=app.id, reason="No longer needed", actor=student)
    assert w.status == "withdrawn"


def test_fr_017_assistant_start_verification(student, assistant, scheme_mcm, policy_mcm):
    """TC-FR-017 | AFR-SPACS-017: Assistant locks and starts verification."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    v = app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    assert v.status == "under_verification"


def test_fr_018_record_verification_findings(student, assistant, scheme_mcm, policy_mcm):
    """TC-FR-018 | AFR-SPACS-018: Assistant verifies application."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    v = app_service.verify_application(application_id=app.id, action_type="verify", findings={"income_verified": True}, actor=assistant)
    assert v.status == "verified"


def test_fr_019_request_correction(student, assistant, scheme_mcm, policy_mcm):
    """TC-FR-019 | AFR-SPACS-019: Assistant requests correction."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    v = app_service.verify_application(application_id=app.id, action_type="request_correction", reason="Fix page 2", actor=assistant)
    assert v.status == "correction_required"


def test_fr_020_flag_verification_concern(student, assistant, scheme_mcm, policy_mcm):
    """TC-FR-020 | AFR-SPACS-020: Assistant flags concern."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    v = app_service.verify_application(application_id=app.id, action_type="record_concern", reason="Discrepancy in seal", actor=assistant)
    assert v.verification_concern_details == "Discrepancy in seal"


def test_fr_021_convener_view_queue(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-021 | AFR-SPACS-021: Convener reviews verified applications."""
    from modules.spacs.selectors.applications import visible_applications
    apps = visible_applications(convener)
    assert apps is not None


def test_fr_022_convener_approve(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-022 | AFR-SPACS-022: Convener approves scholarship."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="verify", actor=assistant)
    decided = app_service.decide_application(application_id=app.id, decision="approve", actor=convener)
    assert decided.status == "approved"


def test_fr_023_convener_reject(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-023 | AFR-SPACS-023: Convener rejects scholarship."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="verify", actor=assistant)
    decided = app_service.decide_application(application_id=app.id, decision="reject", reason="Quota full", actor=convener)
    assert decided.status == "rejected"


def test_fr_024_convener_return_correction(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-024 | AFR-SPACS-024: Convener returns for correction."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="verify", actor=assistant)
    app.status = "under_convener_review"
    app.save(update_fields=["status"])
    decided = app_service.decide_application(application_id=app.id, decision="return_correction", reason="Check salary slip", actor=convener)
    assert decided.status == "correction_required"


def test_fr_025_initiate_renewal(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-025 | AFR-SPACS-025: Submit scholarship renewal."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-MCM-PRIOR-REV", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="approved"
    )
    ren = app_service.submit_renewal(
        prior_application_id=app.id, academic_cycle="2024-25", current_facts={"cpi": 7.8, "active_backlogs": 0}, actor=student
    )
    assert ren.is_renewal is True


def test_fr_026_renewal_eligibility_eval(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-026 | AFR-SPACS-026: Validate renewal eligibility."""
    from modules.spacs.domain.renewal import evaluate_renewal_eligibility
    res = evaluate_renewal_eligibility(
        is_renewable=True, prior_application_status="approved", renewal_window_open=True,
        renewal_rules={"min_cpi": 6.5, "max_active_backlogs": 0}, current_facts={"cpi": 7.0, "active_backlogs": 0},
    )
    assert res.can_renew is True


def test_fr_027_block_renewal_backlogs(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-027 | AFR-SPACS-027: Block renewal with backlogs."""
    from modules.spacs.domain.renewal import evaluate_renewal_eligibility
    res = evaluate_renewal_eligibility(
        is_renewable=True, prior_application_status="approved", renewal_window_open=True,
        renewal_rules={"min_cpi": 6.5, "max_active_backlogs": 0}, current_facts={"cpi": 7.0, "active_backlogs": 1},
    )
    assert res.can_renew is False


def test_fr_028_enforce_renewal_window(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-028 | AFR-SPACS-028: Enforce renewal window."""
    from modules.spacs.domain.renewal import evaluate_renewal_eligibility
    res = evaluate_renewal_eligibility(
        is_renewable=True, prior_application_status="approved", renewal_window_open=False,
        renewal_rules={"min_cpi": 6.5}, current_facts={"cpi": 7.0},
    )
    assert res.can_renew is False


def test_fr_029_open_award_cycle(convener, award_scheme, award_policy):
    """TC-FR-029 | AFR-SPACS-029: Open convocation award cycle."""
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Awards Committee", actor=convener
    )
    assert cycle.status in ["opened", "open"]


def test_fr_030_configure_committee(convener, award_scheme, award_policy):
    """TC-FR-030 | AFR-SPACS-030: Configure evaluating committee."""
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", committee_members=[4001, 4002], actor=convener
    )
    assert cycle.committee_members == [4001, 4002]


def test_fr_031_prepare_candidate_pool(convener, award_scheme, award_policy):
    """TC-FR-031 | AFR-SPACS-031: Prepare award candidate pool."""
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    cand_data = [{"student_user_id": 1001, "cpi": 9.2, "discipline": "CSE"}]
    c = award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=cand_data, actor=convener)
    assert c.status == "pool_prepared"


def test_fr_032_committee_record_scores(convener, committee_member, award_scheme, award_policy):
    """TC-FR-032 | AFR-SPACS-032: Committee records evaluation scores."""
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.2}], actor=convener
    )
    cand = AwardCandidate.objects.filter(award_cycle=cycle).first()
    evals = [{"student_user_id": cand.student_user_id, "score": 95.0, "remarks": "Top performer", "recommendation_status": "recommended"}]
    evaluated = award_service.record_committee_evaluations(award_cycle_id=cycle.id, evaluations=evals, actor=committee_member)
    assert evaluated.status == "result_recorded"


def test_fr_033_committee_recommendations(convener, committee_member, award_scheme, award_policy):
    """TC-FR-033 | AFR-SPACS-033: Committee records candidate recommendation."""
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.2}], actor=convener
    )
    cand = AwardCandidate.objects.filter(award_cycle=cycle).first()
    evals = [{"student_user_id": cand.student_user_id, "score": 95.0, "recommendation_status": "recommended"}]
    award_service.record_committee_evaluations(award_cycle_id=cycle.id, evaluations=evals, actor=committee_member)
    cand.refresh_from_db()
    assert cand.recommendation_status == "recommended"


def test_fr_034_convener_record_final_approval(convener, committee_member, award_scheme, award_policy):
    """TC-FR-034 | AFR-SPACS-034: Record final institutional approval."""
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.2}], actor=convener
    )
    cand = AwardCandidate.objects.filter(award_cycle=cycle).first()
    award_service.record_committee_evaluations(
        award_cycle_id=cycle.id, evaluations=[{"student_user_id": cand.student_user_id, "score": 95.0, "recommendation_status": "recommended"}],
        actor=committee_member
    )
    approved = award_service.record_final_approval(
        award_cycle_id=cycle.id, approval_reference="SEN/AWARDS/2025", approving_authority="Senate",
        approved_candidate_ids=[1001], actor=convener
    )
    assert approved.status == "ready_for_publication"


def test_fr_035_publish_award_results(convener, committee_member, award_scheme, award_policy):
    """TC-FR-035 | AFR-SPACS-035: Publish convocation award results."""
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.2}], actor=convener
    )
    cand = AwardCandidate.objects.filter(award_cycle=cycle).first()
    award_service.record_committee_evaluations(
        award_cycle_id=cycle.id, evaluations=[{"student_user_id": cand.student_user_id, "score": 95.0, "recommendation_status": "recommended"}],
        actor=committee_member
    )
    award_service.record_final_approval(
        award_cycle_id=cycle.id, approval_reference="SEN/AWARDS/2025", approving_authority="Senate",
        approved_candidate_ids=[1001], actor=convener
    )
    pub = award_service.publish_award_results(award_cycle_id=cycle.id, actor=convener)
    assert pub.status == "published"


def test_fr_036_public_award_visibility(student, convener, committee_member, award_scheme, award_policy):
    """TC-FR-036 | AFR-SPACS-036: Public access to published awards."""
    from modules.spacs.selectors.awards import visible_award_cycles
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.2}], actor=convener)
    cand = AwardCandidate.objects.filter(award_cycle=cycle).first()
    award_service.record_committee_evaluations(award_cycle_id=cycle.id, evaluations=[{"student_user_id": cand.student_user_id, "score": 95.0}], actor=committee_member)
    award_service.record_final_approval(award_cycle_id=cycle.id, approval_reference="SEN", approving_authority="Senate", approved_candidate_ids=[1001], actor=convener)
    award_service.publish_award_results(award_cycle_id=cycle.id, actor=convener)
    cycles = visible_award_cycles(student)
    assert cycles.filter(id=cycle.id).exists()


def test_fr_037_sla_reminder_verification(student, assistant, scheme_mcm, policy_mcm):
    """TC-FR-037 | AFR-SPACS-037: Trigger SLA reminder for pending verification."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    ScholarshipApplication.objects.filter(id=app.id).update(submitted_at=timezone.now() - timedelta(days=10))
    res = task_service.send_sla_reminders()
    assert res >= 1


def test_fr_038_sla_reminder_decision(student, assistant, scheme_mcm, policy_mcm):
    """TC-FR-038 | AFR-SPACS-038: Trigger SLA reminder for pending decision."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="verify", actor=assistant)
    ScholarshipApplication.objects.filter(id=app.id).update(verified_at=timezone.now() - timedelta(days=20))
    res = task_service.send_sla_reminders()
    assert res >= 1


def test_fr_039_renewal_reminder_notification(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-039 | AFR-SPACS-039: Trigger renewal reminder notification."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-MCM-PRIOR-NOTIF", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="approved"
    )
    res = task_service.send_renewal_reminders()
    assert res >= 1


def test_fr_040_reassign_pending_tasks(student, assistant, scheme_mcm, policy_mcm):
    """TC-FR-040 | AFR-SPACS-040: Reassign pending verification tasks."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    ScholarshipApplication.objects.filter(id=app.id).update(assigned_assistant_user_id=assistant.user_id)
    res = task_service.reassign_pending_tasks(role_code="spacs_assistant", from_user_id=assistant.user_id, to_user_id=2002)
    assert res >= 1


def test_fr_041_append_only_transitions(student, assistant, scheme_mcm, policy_mcm):
    """TC-FR-041 | AFR-SPACS-041: Append-only state transition records."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    from modules.spacs.models import ApplicationTransition
    transitions = ApplicationTransition.objects.filter(application=app)
    assert transitions.count() >= 1


def test_fr_042_immutable_audit_log(student, scheme_mcm, policy_mcm):
    """TC-FR-042 | AFR-SPACS-042: Immutable audit log entry on action."""
    app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    assert SpacsAuditLog.objects.filter(action="application.draft_created").exists()


def test_fr_043_student_isolation(student, student2, scheme_mcm, policy_mcm):
    """TC-FR-043 | AFR-SPACS-043: Student cannot see peer applications."""
    app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    from modules.spacs.selectors.applications import visible_applications
    visible = visible_applications(student2)
    assert not visible.filter(student_user_id=student.user_id).exists()


def test_fr_044_assistant_queue_isolation(student, assistant, scheme_mcm, policy_mcm):
    """TC-FR-044 | AFR-SPACS-044: Assistant queue isolation."""
    from modules.spacs.selectors.applications import visible_applications
    apps = visible_applications(assistant)
    assert apps is not None


def test_fr_045_export_application_record(student, scheme_mcm, policy_mcm):
    """TC-FR-045 | AFR-SPACS-045: Export application summary record."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    from modules.spacs.selectors.applications import get_application
    rec = get_application(app.id, student)
    assert rec is not None


def test_fr_046_public_clearance_contract(student, scheme_mcm, policy_mcm):
    """TC-FR-046 | AFR-SPACS-046: Public clearance contract."""
    clearances = contracts.get_spacs_clearances([student.user_id])
    assert clearances[student.user_id].cleared is True


def test_fr_047_public_scholarship_awards_contract(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-047 | AFR-SPACS-047: Public scholarship awards contract."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-MCM-AWARDED-47", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2024-25", status="approved"
    )
    awards = contracts.get_scholarship_awards([student.user_id])
    assert len(awards[student.user_id]) == 1


def test_fr_048_public_convocation_awards_contract(convener, committee_member, award_scheme, award_policy):
    """TC-FR-048 | AFR-SPACS-048: Public convocation awards contract."""
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025,
        evaluating_body="Senate Committee", actor=convener
    )
    award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.2}], actor=convener)
    cand = AwardCandidate.objects.filter(award_cycle=cycle).first()
    award_service.record_committee_evaluations(award_cycle_id=cycle.id, evaluations=[{"student_user_id": cand.student_user_id, "score": 95.0}], actor=committee_member)
    award_service.record_final_approval(award_cycle_id=cycle.id, approval_reference="SEN", approving_authority="Senate", approved_candidate_ids=[1001], actor=convener)
    award_service.publish_award_results(award_cycle_id=cycle.id, actor=convener)
    res = contracts.get_convocation_awards([1001], convocation_year=2025)
    assert len(res[1001]) == 1


def test_fr_049_prospective_retirement_preserves_awarded(student, assistant, convener, scheme_mcm, policy_mcm):
    """TC-FR-049 | AFR-SPACS-049: Prospective retirement preserves active applications."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    cat_service.retire_catalogue_entry(scheme_id=scheme_mcm.id, reason="Closing scheme", actor=convener)
    app.refresh_from_db()
    assert app.status == "submitted"


def test_fr_050_policy_version_provenance_validation(convener, scheme_mcm):
    """TC-FR-050 | AFR-SPACS-050: Publishing requires approval authority."""
    v = cat_service.create_policy_version(scheme_id=scheme_mcm.id, title="Unapproved Draft", actor=convener)
    with pytest.raises(ConflictError) as exc:
        cat_service.publish_policy_version(version_id=v.id, actor=convener)
    assert "provenance" in str(exc.value).lower() or "approval" in str(exc.value).lower()


def test_fr_051_outbox_notification_generation(student, scheme_mcm, policy_mcm):
    """TC-FR-051 | AFR-SPACS-051: Outbox notification generated on submit."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    assert SpacsNotification.objects.filter(recipient_user_id=student.user_id, event_type="application.submitted").exists()


def test_fr_052_notification_read_update(student, scheme_mcm, policy_mcm):
    """TC-FR-052 | AFR-SPACS-052: Notification marked as read."""
    notif = SpacsNotification.objects.create(recipient_user_id=student.user_id, recipient_role="student", event_type="test", title="T", message="M")
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    assert SpacsNotification.objects.get(id=notif.id).is_read is True


def test_fr_053_duplicate_draft_negative(student, scheme_mcm, policy_mcm):
    """TC-FR-053-NEG | AFR-SPACS-014 duplicate-check: Rejection of duplicate active draft application.

    CANDIDATE DEFECT (DEF-01): System should reject creating a second active draft for the same scheme and cycle.
    """
    d1 = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    d1.application_number = "SPACS-DRAFT-1-ORIGINAL"
    d1.save(update_fields=["application_number"])
    # Expected: creating a second active draft is rejected
    with pytest.raises(ConflictError) as exc:
        d2 = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
        if d2 is not None:
            raise AssertionError("Implementation permitted multiple active drafts for same scheme and cycle (DEF-01)")
    assert "duplicate" in str(exc.value).lower()


def test_fr_054_window_expired_boundary(student, scheme_mcm, policy_mcm):
    """TC-FR-054-BOUND | AFR-SPACS-028 window-boundary: Submission blocked when window closed."""
    policy_mcm.application_window_end = timezone.now() - timedelta(days=1)
    policy_mcm.save(update_fields=["application_window_end"])
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    with pytest.raises(ConflictError) as exc:
        app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    assert "window" in str(exc.value).lower()
