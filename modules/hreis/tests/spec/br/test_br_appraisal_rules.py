import pytest

from core.api.exceptions import BadRequestError
from modules.hreis.models import EmployeeServiceRecord
from modules.hreis.services.appraisals import (
    assign_appraisal_reviewers,
    finalize_appraisal,
    submit_appraisal,
    submit_appraisal_review,
)
from modules.hreis.services.workflow_config import update_workflow_config

pytestmark = pytest.mark.django_db


def test_br_019_appraisal_window_active():
    """TEST-BR-019 [BR-HR-012 Permitted Window]: Verify appraisal submission is accepted within active submission window."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=370,
        username="u370",
        academic_year="2025-2026",
        content={"teaching": "Full"},
    )
    assert appraisal.id is not None
    assert appraisal.status == "submitted"


def test_br_020_appraisal_window_closed():
    """TEST-BR-020 [BR-HR-012 Prohibited Window]: Verify appraisal submission is rejected outside active submission window."""
    update_workflow_config(
        "appraisal_window",
        {"active": False, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2025-06-30"},
    )
    with pytest.raises(BadRequestError):
        submit_appraisal(
            user_id=371,
            username="u371",
            academic_year="2025-2026",
            content={"teaching": "Full"},
        )


def test_br_021_hr_admin_assign_reviewers():
    """TEST-BR-021 [BR-HR-013 Permitted]: Verify HR Administrator can assign reviewer(s) for appraisal evaluation."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=372,
        username="u372",
        academic_year="2025-2026",
        content={"teaching": "Full"},
    )
    updated = assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[401, 402],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert updated.status == "under_review"
    assert 401 in updated.assigned_reviewers


def test_br_022_appraisal_review_routing_and_finalization():
    """TEST-BR-022 [BR-HR-014 Permitted]: Verify appraisal passes through designated authorities for review and finalization."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=373,
        username="u373",
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
        comments="Very good",
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


def test_br_023_appraisal_archive_in_service_record():
    """TEST-BR-023 [BR-HR-015 Archive]: Verify finalized appraisal is archived in employee service record."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=374,
        employee_id="EMP0374",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=374,
        username="u374",
        academic_year="2025-2026",
        content={"teaching": "Good"},
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
        final_score=8.5,
        final_remarks="Complete",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    rec.refresh_from_db()
    assert any("Appraisal" in str(e) for e in (rec.service_history or []))


def test_br_024_appraisal_immutability():
    """TEST-BR-024 [BR-HR-015 Immutability]: Verify finalized appraisal cannot be modified after finalization."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=375,
        username="u375",
        academic_year="2025-2026",
        content={"teaching": "Good"},
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
        final_score=8.5,
        final_remarks="Finalized",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    appraisal.refresh_from_db()
    assert appraisal.is_immutable is True
