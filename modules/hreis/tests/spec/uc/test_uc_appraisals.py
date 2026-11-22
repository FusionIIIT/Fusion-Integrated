import pytest
from rest_framework import status

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.hreis.services.appraisals import (
    assign_appraisal_reviewers,
    finalize_appraisal,
    submit_appraisal,
    submit_appraisal_review,
)
from modules.hreis.services.workflow_config import update_workflow_config

pytestmark = pytest.mark.django_db


def test_uc_017_submit_appraisal_active_window():
    """TEST-UC-017 [HR-UC-006 Main Flow]: Verify employee can submit yearly appraisal during active submission window."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=230,
        username="u230",
        academic_year="2025-2026",
        content={"teaching": "Full load", "publications": 2},
    )
    assert appraisal.id is not None
    assert appraisal.status == "submitted"


def test_uc_018_appraisal_submission_closed_window():
    """TEST-UC-018 [HR-UC-006 Alternative A1]: Verify appraisal submission is rejected when cycle window is closed."""
    update_workflow_config(
        "appraisal_window",
        {"active": False, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2025-06-30"},
    )
    with pytest.raises(BadRequestError):
        submit_appraisal(
            user_id=231,
            username="u231",
            academic_year="2025-2026",
            content={"teaching": "Load"},
        )


def test_uc_019_unauthorized_appraisal_submission(auth_client_factory):
    """TEST-UC-019 [HR-UC-006 Exception E1]: Verify unauthorized actor cannot submit appraisal."""
    from rest_framework.test import APIClient
    client = APIClient()
    response = client.post(
        "/api/v1/hreis/appraisals/",
        {"academic_year": "2025-2026", "content": {}},
        format="json",
    )
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_uc_020_hr_admin_assign_reviewers():
    """TEST-UC-020 [HR-UC-007 Main Flow]: Verify HR Administrator can assign reviewers to a submitted appraisal."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=232,
        username="u232",
        academic_year="2025-2026",
        content={"publications": 1},
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


def test_uc_021_hr_admin_revise_reviewer_assignment():
    """TEST-UC-021 [HR-UC-007 Alternative A1]: Verify HR Admin can revise reviewer assignment before review begins."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=233,
        username="u233",
        academic_year="2025-2026",
        content={"publications": 1},
    )
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[401],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    revised = assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[402, 403],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert 402 in revised.assigned_reviewers
    assert 401 not in revised.assigned_reviewers


def test_uc_022_non_admin_cannot_assign_reviewers():
    """TEST-UC-022 [HR-UC-007 Exception E1]: Verify non-HR admin cannot assign appraisal reviewers."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=234,
        username="u234",
        academic_year="2025-2026",
        content={"publications": 1},
    )
    with pytest.raises((BadRequestError, PermissionDeniedError)):
        assign_appraisal_reviewers(
            appraisal_id=appraisal.id,
            reviewer_ids=[401],
            actor_id=500,
            actor_username="regular_user",
            actor_role="faculty",
        )


def test_uc_023_reviewer_review_and_finalize():
    """TEST-UC-023 [HR-UC-008 Main Flow]: Verify designated reviewer/authority can review and finalize appraisal."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=235,
        username="u235",
        academic_year="2025-2026",
        content={"teaching": "Satisfactory"},
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
        comments="Excellent",
        actor_id=401,
        actor_username="reviewer1",
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
    assert finalized.is_immutable is True


def test_uc_024_multi_level_review_traversal():
    """TEST-UC-024 [HR-UC-008 Alternative A1]: Verify multi-level appraisal review traversal preserves workflow semantics."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=236,
        username="u236",
        academic_year="2025-2026",
        content={"teaching": "Exemplary"},
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
        comments="First review",
        actor_id=401,
        actor_username="hod",
        actor_role="hod",
    )
    assert rev1.status == "under_review"
    rev2 = submit_appraisal_review(
        appraisal_id=appraisal.id,
        score=8.5,
        comments="Second review",
        actor_id=402,
        actor_username="dean",
        actor_role="dean",
    )
    assert rev2.status == "under_review"


def test_uc_025_modification_of_closed_appraisal_blocked():
    """TEST-UC-025 [HR-UC-008 Exception E1]: Verify modification or re-finalization of a closed appraisal is blocked."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=237,
        username="u237",
        academic_year="2025-2026",
        content={"teaching": "Closed test"},
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
        final_remarks="Closed",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    with pytest.raises(BadRequestError):
        submit_appraisal_review(
            appraisal_id=appraisal.id,
            score=9.0,
            comments="Attempt post-finalization",
            actor_id=401,
            actor_username="reviewer1",
            actor_role="hod",
        )


def test_uc_026_non_designated_actor_cannot_finalize():
    """TEST-UC-026 [HR-UC-008 Exception E2]: Verify actor not designated as reviewer/authority cannot finalize appraisal."""
    update_workflow_config(
        "appraisal_window",
        {"active": True, "academic_year": "2025-2026", "start_date": "2025-01-01", "end_date": "2026-12-31"},
    )
    appraisal = submit_appraisal(
        user_id=238,
        username="u238",
        academic_year="2025-2026",
        content={"teaching": "Auth test"},
    )
    with pytest.raises((BadRequestError, PermissionDeniedError)):
        finalize_appraisal(
            appraisal_id=appraisal.id,
            final_score=8.0,
            final_remarks="Unauthorized attempt",
            actor_id=500,
            actor_username="regular_faculty",
            actor_role="faculty",
        )
