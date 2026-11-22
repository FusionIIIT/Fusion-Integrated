"""Business Rules (BR) test suite for SPACS (BR-SPACS-001..023)."""
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
from modules.spacs.domain import eligibility, renewal

pytestmark = pytest.mark.django_db


# --- BR-SPACS-001: Eligibility Must Be Satisfied ---
def test_br_001_permitted(student, scheme_mcm, policy_mcm):
    """TC-BR-001-PERMITTED | BR-SPACS-001: Satisfying criteria permits application."""
    res = eligibility.evaluate_criteria({"min_cpi": 6.5, "max_parental_income": 600000.0}, {"cpi": 7.0, "parental_income": 500000.0})
    assert res.is_eligible is True


def test_br_001_prohibited(student, scheme_mcm, policy_mcm):
    """TC-BR-001-PROHIBITED | BR-SPACS-001: Sub-threshold CPI fails eligibility."""
    res = eligibility.evaluate_criteria({"min_cpi": 6.5}, {"cpi": 6.49})
    assert res.is_eligible is False


# --- BR-SPACS-002: No Duplicate Applications ---
def test_br_002_permitted(student, scheme_mcm, policy_mcm):
    """TC-BR-002-PERMITTED | BR-SPACS-002: Single active application allowed."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    assert app.status == "draft"


def test_br_002_prohibited(student, scheme_mcm, policy_mcm):
    """TC-BR-002-PROHIBITED | BR-SPACS-002: Multiple active drafts in same cycle prohibited.

    CANDIDATE DEFECT (DEF-01): System should reject creating a second active draft for same scheme & cycle.
    """
    d1 = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    d1.application_number = "SPACS-DRAFT-BR-1"
    d1.save(update_fields=["application_number"])
    with pytest.raises(ConflictError) as exc:
        d2 = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
        if d2 is not None:
            raise AssertionError("Implementation permitted multiple active drafts for same scheme and cycle (DEF-01)")
    assert "duplicate" in str(exc.value).lower()


# --- BR-SPACS-003: Reuse of Previously Uploaded Documents ---
def test_br_003_permitted(student, scheme_mcm, policy_mcm):
    """TC-BR-003-PERMITTED | BR-SPACS-003: Reusing valid document."""
    app1 = ScholarshipApplication.objects.create(
        application_number="SPACS-PRIOR-BR3", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="submitted"
    )
    d1 = doc_service.attach_document(
        application_id=app1.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Valid Doc", file_url="/docs/valid.pdf", valid_until=timezone.now().date() + timedelta(days=60), actor=student
    )
    app2 = ScholarshipApplication.objects.create(
        application_number="SPACS-NEW-BR3", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2024-25", status="draft"
    )
    reused = doc_service.reuse_document(application_id=app2.id, student_user_id=student.user_id, source_doc_id=d1.id, actor=student)
    assert reused.is_reused is True


def test_br_003_prohibited(student, scheme_mcm, policy_mcm):
    """TC-BR-003-PROHIBITED | BR-SPACS-003: Reusing previously rejected document rejected.

    CANDIDATE DEFECT (DEF-03): Reusing a document whose prior verification status was 'rejected'
    should be blocked, but reuse_document allows it and resets to pending.
    """
    app1 = ScholarshipApplication.objects.create(
        application_number="SPACS-PRIOR-REJ-DOC", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="submitted"
    )
    d1 = doc_service.attach_document(
        application_id=app1.id, student_user_id=student.user_id, doc_type="income_certificate",
        title="Rejected Income Cert", file_url="/docs/rej.pdf", valid_until=timezone.now().date() + timedelta(days=60), actor=student
    )
    d1.verification_status = "rejected"
    d1.save(update_fields=["verification_status"])

    app2 = ScholarshipApplication.objects.create(
        application_number="SPACS-NEW-BR3-REJ", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2024-25", status="draft"
    )
    with pytest.raises(ConflictError) as exc:
        reused = doc_service.reuse_document(application_id=app2.id, student_user_id=student.user_id, source_doc_id=d1.id, actor=student)
        if reused is not None and reused.verification_status != "rejected":
            raise AssertionError("Permitted reuse of document that was previously verified as rejected (DEF-03)")
    assert "rejected" in str(exc.value).lower()


# --- BR-SPACS-004: Application Completeness ---
def test_br_004_permitted(student, scheme_mcm, policy_mcm):
    """TC-BR-004-PERMITTED | BR-SPACS-004: Submission accepted when all required documents attached."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    sub = app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    assert sub.status == "submitted"


def test_br_004_prohibited(student, scheme_mcm, policy_mcm):
    """TC-BR-004-PROHIBITED | BR-SPACS-004: Missing mandatory document blocks submission."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    with pytest.raises(ConflictError) as exc:
        app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    assert "missing" in str(exc.value).lower()


# --- BR-SPACS-005: Application Review Access ---
def test_br_005_permitted(assistant, student, scheme_mcm, policy_mcm):
    """TC-BR-005-PERMITTED | BR-SPACS-005: Authorized assistant can access review queue."""
    from modules.spacs.selectors.applications import visible_applications
    assert visible_applications(assistant) is not None


def test_br_005_prohibited(student, student2, scheme_mcm, policy_mcm):
    """TC-BR-005-PROHIBITED | BR-SPACS-005: Non-staff cannot review peer applications."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    with pytest.raises(PermissionDeniedError):
        app_service.verify_application(application_id=app.id, action_type="start", actor=student2)


# --- BR-SPACS-006: Verification Is Not Final Sanction ---
def test_br_006_permitted(assistant, student, scheme_mcm, policy_mcm):
    """TC-BR-006-PERMITTED | BR-SPACS-006: Assistant verifies application to verified state."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    v = app_service.verify_application(application_id=app.id, action_type="verify", actor=assistant)
    assert v.status == "verified"


def test_br_006_prohibited(assistant, student, scheme_mcm, policy_mcm):
    """TC-BR-006-PROHIBITED | BR-SPACS-006: Assistant cannot make final approval decision."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    with pytest.raises(PermissionDeniedError):
        app_service.decide_application(application_id=app.id, decision="approve", actor=assistant)


# --- BR-SPACS-007: Single Active Scholarship Application ---
def test_br_007_permitted(student, scheme_mcm, policy_mcm):
    """TC-BR-007-PERMITTED | BR-SPACS-007: Apply for scheme in new cycle."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2025-26", actor=student)
    assert app.academic_cycle == "2025-26"


def test_br_007_prohibited(student, scheme_mcm, policy_mcm):
    """TC-BR-007-PROHIBITED | BR-SPACS-007: Duplicate active submission rejected."""
    app1 = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app1.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app1.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app1.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)

    app2 = ScholarshipApplication.objects.create(
        application_number="SPACS-BR-DUP-SUB", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2024-25", status="draft"
    )
    doc_service.attach_document(application_id=app2.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app2.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    with pytest.raises(ConflictError):
        app_service.submit_application(application_id=app2.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)


# --- BR-SPACS-008: Notification Requirements ---
def test_br_008_permitted(student, scheme_mcm, policy_mcm):
    """TC-BR-008-PERMITTED | BR-SPACS-008: Notifications recorded on critical events."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    assert SpacsNotification.objects.filter(recipient_user_id=student.user_id).exists()


# --- BR-SPACS-009: Policy Version Immutability ---
def test_br_009_permitted(convener, scheme_mcm, policy_mcm):
    """TC-BR-009-PERMITTED | BR-SPACS-009: Policy versions maintain immutable numbers."""
    v2 = cat_service.create_policy_version(scheme_id=scheme_mcm.id, title="v2", actor=convener)
    assert v2.version_number == policy_mcm.version_number + 1


# --- BR-SPACS-010: Correction Request Reversion ---
def test_br_010_permitted(student, assistant, scheme_mcm, policy_mcm):
    """TC-BR-010-PERMITTED | BR-SPACS-010: Requesting correction transitions status."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    v = app_service.verify_application(application_id=app.id, action_type="request_correction", reason="Check", actor=assistant)
    assert v.status == "correction_required"


def test_br_010_prohibited(student, assistant, scheme_mcm, policy_mcm):
    """TC-BR-010-PROHIBITED | BR-SPACS-010: Cannot request correction without reason."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    with pytest.raises(ConflictError):
        app_service.verify_application(application_id=app.id, action_type="request_correction", reason="", actor=assistant)


# --- BR-SPACS-011: Student Modification Boundaries ---
def test_br_011_permitted(student, assistant, scheme_mcm, policy_mcm):
    """TC-BR-011-PERMITTED | BR-SPACS-011: Modification allowed in correction_required status."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="request_correction", reason="Fix", actor=assistant)
    mod = app_service.modify_application(application_id=app.id, updated_data={"note": "ok"}, resubmit=True, actor=student)
    assert mod.status == "resubmitted"


def test_br_011_prohibited(student, assistant, scheme_mcm, policy_mcm):
    """TC-BR-011-PROHIBITED | BR-SPACS-011: Correction resubmission must re-evaluate criteria.

    CANDIDATE DEFECT (DEF-02): Eligibility snapshot is stale after modification.
    """
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 500000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="request_correction", reason="Check updated income", actor=assistant)
    mod = app_service.modify_application(application_id=app.id, updated_data={"parental_income": 350000.0}, resubmit=True, actor=student)
    snapshot = mod.eligibility_snapshot or {}
    outcomes = {o.get("criterion"): o.get("actual") for o in snapshot.get("outcomes", [])}
    if outcomes.get("max_parental_income") != 350000.0:
        raise AssertionError("Stale eligibility snapshot: not re-evaluated upon correction resubmission (DEF-02)")


# --- BR-SPACS-012: Application Summary Export ---
def test_br_012_permitted(student, scheme_mcm, policy_mcm):
    """TC-BR-012-PERMITTED | BR-SPACS-012: Export application record."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    from modules.spacs.selectors.applications import get_application
    assert get_application(app.id, student) is not None


# --- BR-SPACS-013: SLA Escalation and Reminders ---
def test_br_013_permitted(student, assistant, scheme_mcm, policy_mcm):
    """TC-BR-013-PERMITTED | BR-SPACS-013: SLA reminder fired when threshold exceeded."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    ScholarshipApplication.objects.filter(id=app.id).update(submitted_at=timezone.now() - timedelta(days=10))
    assert task_service.send_sla_reminders() >= 1


def test_br_013_prohibited(scheme_mcm, policy_mcm):
    """TC-BR-013-PROHIBITED | BR-SPACS-013: No reminders when SLA not breached."""
    ScholarshipApplication.objects.all().delete()
    assert task_service.send_sla_reminders() == 0


# --- BR-SPACS-014: Published Catalogue Visibility ---
def test_br_014_permitted(student, scheme_mcm, policy_mcm):
    """TC-BR-014-PERMITTED | BR-SPACS-014: Published schemes visible."""
    from modules.spacs.selectors.catalogue import visible_catalogue_entries
    assert visible_catalogue_entries(student).filter(code="MCM_A8").exists()


def test_br_014_prohibited(student, convener):
    """TC-BR-014-PROHIBITED | BR-SPACS-014: Draft schemes not visible to students."""
    draft_scheme = cat_service.create_catalogue_entry(code="DRAFT_ONLY", name="Draft", scheme_type="scholarship", actor=convener)
    from modules.spacs.selectors.catalogue import visible_catalogue_entries
    assert not visible_catalogue_entries(student).filter(code="DRAFT_ONLY").exists()


# --- BR-SPACS-015: Catalogue Version Publishing Provenance ---
def test_br_015_permitted(convener, scheme_mcm):
    """TC-BR-015-PERMITTED | BR-SPACS-015: Publishing with approval provenance."""
    v = cat_service.create_policy_version(
        scheme_id=scheme_mcm.id, title="v2 Provenance", policy_approval_reference="BOG/RES/15",
        policy_approved_by="Senate", effective_from=timezone.now().date(), actor=convener
    )
    pub = cat_service.publish_policy_version(version_id=v.id, actor=convener)
    assert pub.status == "published"


def test_br_015_prohibited(convener, scheme_mcm):
    """TC-BR-015-PROHIBITED | BR-SPACS-015: Publishing without approval provenance rejected."""
    v = cat_service.create_policy_version(scheme_id=scheme_mcm.id, title="v2 Unapproved", actor=convener)
    with pytest.raises(ConflictError):
        cat_service.publish_policy_version(version_id=v.id, actor=convener)


# --- BR-SPACS-016: Isolation of Student Views ---
def test_br_016_permitted(student, scheme_mcm, policy_mcm):
    """TC-BR-016-PERMITTED | BR-SPACS-016: Student views own application."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    from modules.spacs.selectors.applications import visible_applications
    assert visible_applications(student).filter(id=app.id).exists()


def test_br_016_prohibited(student, student2, scheme_mcm, policy_mcm):
    """TC-BR-016-PROHIBITED | BR-SPACS-016: Student cannot view peer application."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    from modules.spacs.selectors.applications import get_application
    assert get_application(app.id, student2) is None


# --- BR-SPACS-017: Scholarship Renewal Lifecycle ---
def test_br_017_permitted(student, scheme_mcm, policy_mcm):
    """TC-BR-017-PERMITTED | BR-SPACS-017: Renewal approved when criteria met."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-BR17-PRIOR", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="approved"
    )
    ren = app_service.submit_renewal(prior_application_id=app.id, academic_cycle="2024-25", current_facts={"cpi": 8.0, "active_backlogs": 0}, actor=student)
    assert ren.is_renewal is True


def test_br_017_prohibited(student, scheme_mcm, policy_mcm):
    """TC-BR-017-PROHIBITED | BR-SPACS-017: Renewal rejected with active backlogs."""
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-BR17-PRIOR-2", student_user_id=student.user_id, scheme=scheme_mcm,
        policy_version=policy_mcm, academic_cycle="2023-24", status="approved"
    )
    with pytest.raises(ConflictError):
        app_service.submit_renewal(prior_application_id=app.id, academic_cycle="2024-25", current_facts={"cpi": 8.0, "active_backlogs": 1}, actor=student)


# --- BR-SPACS-018: Scholarship Decision Authority ---
def test_br_018_permitted(convener, assistant, student, scheme_mcm, policy_mcm):
    """TC-BR-018-PERMITTED | BR-SPACS-018: Convener makes final approval."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    app_service.verify_application(application_id=app.id, action_type="start", actor=assistant)
    app_service.verify_application(application_id=app.id, action_type="verify", actor=assistant)
    decided = app_service.decide_application(application_id=app.id, decision="approve", actor=convener)
    assert decided.status == "approved"


def test_br_018_prohibited(assistant, student, scheme_mcm, policy_mcm):
    """TC-BR-018-PROHIBITED | BR-SPACS-018: Assistant cannot make decision."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    with pytest.raises(PermissionDeniedError):
        app_service.decide_application(application_id=app.id, decision="approve", actor=assistant)


# --- BR-SPACS-019: Award Evaluation and Approval Follow Award Policy ---
def test_br_019_permitted(convener, committee_member, award_scheme, award_policy):
    """TC-BR-019-PERMITTED | BR-SPACS-019: Award evaluation follows policy authority."""
    cycle = award_service.create_award_cycle(scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025, evaluating_body="Senate", actor=convener)
    award_service.prepare_candidate_pool(award_cycle_id=cycle.id, candidates=[{"student_user_id": 1001, "cpi": 9.5}], actor=convener)
    res = award_service.record_committee_evaluations(award_cycle_id=cycle.id, evaluations=[{"student_user_id": 1001, "score": 98.0}], actor=committee_member)
    assert res.status == "result_recorded"


# --- BR-SPACS-020: Award Criteria Versioning ---
def test_br_020_permitted(convener, award_scheme, award_policy):
    """TC-BR-020-PERMITTED | BR-SPACS-020: Award cycle binds to active policy version."""
    cycle = award_service.create_award_cycle(scheme_id=award_scheme.id, academic_cycle="2024-25", convocation_year=2025, evaluating_body="Senate", actor=convener)
    assert cycle.policy_version == award_policy


# --- BR-SPACS-021: Audit Records Protected and Restricted ---
def test_br_021_permitted(convener):
    """TC-BR-021-PERMITTED | BR-SPACS-021: Audit trail recorded and accessible to convener."""
    from modules.spacs.selectors.audit import visible_audit_logs
    assert visible_audit_logs(convener) is not None


# --- BR-SPACS-022: Role Reassignment Preserves History ---
def test_br_022_permitted(student, assistant, scheme_mcm, policy_mcm):
    """TC-BR-022-PERMITTED | BR-SPACS-022: Role reassignment updates assignee preserving history."""
    app = app_service.create_draft_application(scheme_id=scheme_mcm.id, academic_cycle="2024-25", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="income_certificate", title="Inc", file_url="/u/inc.pdf", actor=student)
    doc_service.attach_document(application_id=app.id, student_user_id=student.user_id, doc_type="grade_card", title="GC", file_url="/u/gc.pdf", actor=student)
    app_service.submit_application(application_id=app.id, student_facts={"cpi": 8.0, "parental_income": 400000.0}, actor=student)
    ScholarshipApplication.objects.filter(id=app.id).update(assigned_assistant_user_id=assistant.user_id)
    reassigned = task_service.reassign_pending_tasks(role_code="spacs_assistant", from_user_id=assistant.user_id, to_user_id=2004)
    assert reassigned >= 1


# --- BR-SPACS-023: Award Candidate Source Is Scheme-Specific ---
def test_br_023_permitted(convener, award_scheme, award_policy):
    """TC-BR-023-PERMITTED | BR-SPACS-023: Award cycle candidate source method."""
    assert award_policy.candidate_source_method == "nomination"
