import pytest
from datetime import date
from decimal import Decimal
from modules.hreis.models import AppraisalSubmission, EmployeeServiceRecord
from modules.hreis.services.appraisals import (
    assign_appraisal_reviewers,
    finalize_appraisal,
    submit_appraisal,
    submit_appraisal_review,
)
from modules.hreis.services.workflow_config import update_workflow_config

pytestmark = pytest.mark.django_db


def test_fr_062_employee_submit_yearly_appraisal():
    """TEST-FR-062 [HR-AFR-044]: Verify HR-EIS allows Employees to submit yearly appraisal forms."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=210,
        username="u210",
        academic_year="2025-2026",
        content={"teaching_load": "4 courses", "publications": 3},
    )
    assert appraisal.id is not None
    assert appraisal.status == "submitted"


def test_fr_063_restrict_appraisal_to_configured_windows():
    """TEST-FR-063 [HR-AFR-045]: Verify HR-EIS restricts yearly appraisal form submission to configured submission windows."""
    from core.api.exceptions import BadRequestError

    update_workflow_config(
        "appraisal_window",
        {"active": False, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2025-06-30"},
    )
    with pytest.raises(BadRequestError):
        submit_appraisal(
            user_id=211,
            username="u211",
            academic_year="2025-2026",
            content={"teaching": "None"},
        )


def test_fr_064_hr_admin_assign_reviewers():
    """TEST-FR-064 [HR-AFR-046]: Verify HR-EIS allows HR Administrator to assign reviewers for appraisal evaluation."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=212,
        username="u212",
        academic_year="2025-2026",
        content={"publications": 2},
    )
    updated = assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[301, 302],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert updated.status == "under_review"
    assert 301 in updated.assigned_reviewers


def test_fr_065_appraisal_review_and_finalization():
    """TEST-FR-065 [HR-AFR-047]: Verify HR-EIS routes appraisal workflows through designated authorities for review and finalization."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=213,
        username="u213",
        academic_year="2025-2026",
        content={"teaching": "Satisfactory"},
    )
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[301],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    submit_appraisal_review(
        appraisal_id=appraisal.id,
        score=8.5,
        comments="Good teaching feedback",
        actor_id=301,
        actor_username="reviewer1",
        actor_role="hod",
    )
    finalized = finalize_appraisal(
        appraisal_id=appraisal.id,
        final_score=8.5,
        final_remarks="Approved by Director",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert finalized.status == "finalized"
    assert finalized.is_immutable is True


def test_fr_066_archive_finalized_appraisal_in_service_record():
    """TEST-FR-066 [HR-AFR-048]: Verify HR-EIS archives finalized appraisals in the employee service record."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=214,
        employee_id="EMP0214",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=214,
        username="u214",
        academic_year="2025-2026",
        content={"teaching": "Exemplary"},
    )
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[301],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    finalize_appraisal(
        appraisal_id=appraisal.id,
        final_score=9.0,
        final_remarks="Excellent work",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    rec.refresh_from_db()
    history_events = [h.get("event") for h in (rec.service_history or [])]
    assert any("Appraisal" in str(e) for e in history_events)


def test_fr_067_prevent_modification_after_closure():
    """TEST-FR-067 [HR-AFR-049]: Verify HR-EIS prevents modification of appraisal records after closure."""
    from core.api.exceptions import BadRequestError

    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=215,
        username="u215",
        academic_year="2025-2026",
        content={"teaching": "Initial submission"},
    )
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[301],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    finalize_appraisal(
        appraisal_id=appraisal.id,
        final_score=8.0,
        final_remarks="Closed",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    with pytest.raises(BadRequestError):
        submit_appraisal(
            user_id=215,
            username="u215",
            academic_year="2025-2026",
            content={"teaching": "Tampering after closure"},
        )
