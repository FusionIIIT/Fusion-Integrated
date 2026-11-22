import pytest
from core.api.exceptions import BadRequestError
from modules.hreis.models import AppraisalSubmission, EmployeeServiceRecord, HrAuditLog
from modules.hreis.services.appraisals import (
    assign_appraisal_reviewers,
    finalize_appraisal,
    submit_appraisal,
    submit_appraisal_review,
)
from modules.hreis.services.workflow_config import update_workflow_config

pytestmark = pytest.mark.django_db


def test_wf_010_appraisal_direct_finalization():
    """TEST-WF-010 [BW-HR-04 Direct Finalization Path]: Verify appraisal workflow with zero intermediate traversal before finalization."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=520,
        username="u520",
        academic_year="2025-2026",
        content={"teaching": "Full load", "publications": 2},
    )
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[401],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    submit_appraisal_review(
        appraisal_id=appraisal.id,
        score=8.5,
        comments="Satisfactory",
        actor_id=401,
        actor_username="hod",
        actor_role="hod",
    )
    finalized = finalize_appraisal(
        appraisal_id=appraisal.id,
        final_score=8.5,
        final_remarks="Approved",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert finalized.status == "finalized"
    assert finalized.is_immutable is True


def test_wf_011_appraisal_immutability_guard():
    """TEST-WF-011 [BW-HR-04 Immutability Guard]: Verify finalized appraisal cannot undergo further review."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=521,
        username="u521",
        academic_year="2025-2026",
        content={"teaching": "Load"},
    )
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[401],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    finalize_appraisal(
        appraisal_id=appraisal.id,
        final_score=8.0,
        final_remarks="Approved",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    with pytest.raises(BadRequestError):
        submit_appraisal_review(
            appraisal_id=appraisal.id,
            score=9.0,
            comments="Post-closure review",
            actor_id=401,
            actor_username="hod",
            actor_role="hod",
        )


def test_wf_012_appraisal_one_additional_authority():
    """TEST-WF-012 [BW-HR-05 One Additional Authority Path]: Verify appraisal path with exactly one additional designated-authority review before finalization."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=522,
        username="u522",
        academic_year="2025-2026",
        content={"teaching": "Excellent"},
    )
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[401, 402],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    rev1 = submit_appraisal_review(
        appraisal_id=appraisal.id,
        score=8.0,
        comments="Review 1",
        actor_id=401,
        actor_username="hod",
        actor_role="hod",
    )
    assert rev1.status == "under_review"
    rev2 = submit_appraisal_review(
        appraisal_id=appraisal.id,
        score=8.5,
        comments="Review 2",
        actor_id=402,
        actor_username="dean",
        actor_role="dean",
    )
    assert rev2.status == "under_review"
    final = finalize_appraisal(
        appraisal_id=appraisal.id,
        final_score=8.5,
        final_remarks="Finalized after two reviewers",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert final.status == "finalized"


def test_wf_013_appraisal_review_order_guard():
    """TEST-WF-013 [BW-HR-05 Review Order Guard]: Verify unassigned reviewer cannot submit appraisal review."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=523,
        username="u523",
        academic_year="2025-2026",
        content={"teaching": "Standard"},
    )
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[401],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    with pytest.raises(BadRequestError):
        submit_appraisal_review(
            appraisal_id=appraisal.id,
            score=7.0,
            comments="Unassigned reviewer review",
            actor_id=999,
            actor_username="unassigned_user",
            actor_role="faculty",
        )


def test_wf_014_cw_appraisal_lifecycle_complete():
    """TEST-WF-014 [CW-HR-02 Composite Appraisal Lifecycle]: Verify complete composite appraisal lifecycle: window check -> submit -> assign -> review -> finalize -> archive."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=524,
        employee_id="EMP0524",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=524,
        username="u524",
        academic_year="2025-2026",
        content={"teaching": "Exemplary"},
    )
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[401],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    submit_appraisal_review(
        appraisal_id=appraisal.id,
        score=9.0,
        comments="Outstanding",
        actor_id=401,
        actor_username="hod",
        actor_role="hod",
    )
    finalized = finalize_appraisal(
        appraisal_id=appraisal.id,
        final_score=9.0,
        final_remarks="Approved",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert finalized.status == "finalized"
    rec.refresh_from_db()
    assert any("Appraisal" in str(e) for e in (rec.service_history or []))


def test_wf_015_cw_appraisal_closed_window_guard():
    """TEST-WF-015 [CW-HR-02 Closed Window Guard]: Verify appraisal lifecycle cannot start when window is inactive."""
    update_workflow_config(
        "appraisal_window",
        {"active": False, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2025-06-30"},
    )
    with pytest.raises(BadRequestError):
        submit_appraisal(
            user_id=525,
            username="u525",
            academic_year="2025-2026",
            content={"teaching": "Attempt during closed window"},
        )


def test_wf_016_cw_appraisal_audit_trail_consistency():
    """TEST-WF-016 [CW-HR-02 Audit Trail Consistency]: Verify composite appraisal lifecycle produces complete immutable audit trail."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=526,
        username="u526",
        academic_year="2025-2026",
        content={"teaching": "Audit check"},
    )
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[401],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    finalize_appraisal(
        appraisal_id=appraisal.id,
        final_score=8.0,
        final_remarks="Approved",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert HrAuditLog.objects.filter(entity_type="appraisal_submission", entity_id=str(appraisal.id)).count() >= 2
