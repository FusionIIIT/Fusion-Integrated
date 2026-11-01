"""Tests for Annual Appraisal lifecycle and workflow."""
from datetime import date
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import AppraisalSubmission, WorkflowConfiguration

pytestmark = pytest.mark.django_db


def test_appraisal_window_closed(stub_iam, user_ref):
    # Setup workflow config where window is closed
    WorkflowConfiguration.objects.create(
        setting_key="appraisal_window",
        description="Annual appraisal window",
        setting_value={"active": False},
    )

    stub_iam(
        make_session(
            user_id=202,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.appraisal.submit", "hr_eis.appraisal.view_self"),
        ),
        users={202: user_ref(202, name="Dr. Banner", kind="faculty")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    resp = client.post(
        "/api/v1/hreis/appraisals/",
        {
            "academic_year": "2025-2026",
            "teaching_engagement": {"courses": ["CS101", "CS201"]},
            "research_publications": [{"title": "Agentic Workflows in ERP", "venue": "IEEE"}],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "submission window is currently closed" in str(resp.json())


def test_appraisal_submission_and_review_lifecycle(stub_iam, user_ref):
    # 1. Open appraisal window
    WorkflowConfiguration.objects.create(
        setting_key="appraisal_window",
        description="Annual appraisal window",
        setting_value={
            "active": True,
            "start_date": "2020-01-01",
            "end_date": "2030-12-31",
        },
    )

    # 2. Faculty submits appraisal
    stub_iam(
        make_session(
            user_id=202,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.appraisal.submit", "hr_eis.appraisal.view_self"),
        ),
        users={
            202: user_ref(202, name="Dr. Banner", kind="faculty"),
            301: user_ref(301, name="HOD Reviewer", kind="faculty"),
            999: user_ref(999, name="HR Manager", kind="staff"),
        },
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    sub_resp = client.post(
        "/api/v1/hreis/appraisals/",
        {
            "academic_year": "2025-2026",
            "teaching_engagement": {"courses": ["CS101"]},
            "research_publications": [{"title": "Quantum AI", "venue": "ACM"}],
            "sponsored_projects": [],
            "administrative_responsibilities": [],
            "self_appraisal_summary": "Active teaching and research contributions.",
        },
        format="json",
    )
    assert sub_resp.status_code == 201
    appraisal_id = sub_resp.json()["id"]

    # 3. HR Admin assigns reviewer 301
    stub_iam(
        make_session(
            user_id=999,
            kind="staff",
            roles=("hr_admin",),
            modules=("hr_eis",),
            permissions=("hr_eis.appraisal.assign_reviewer", "hr_eis.appraisal.view_all"),
        ),
        users={
            202: user_ref(202, name="Dr. Banner", kind="faculty"),
            301: user_ref(301, name="HOD Reviewer", kind="faculty"),
            999: user_ref(999, name="HR Manager", kind="staff"),
        },
    )

    hr_client = APIClient()
    hr_client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    assign_resp = hr_client.post(
        f"/api/v1/hreis/appraisals/{appraisal_id}/assign-reviewers/",
        {"reviewer_ids": [301]},
        format="json",
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["status"] == "under_review"

    # 4. Reviewer 301 submits review
    stub_iam(
        make_session(
            user_id=301,
            kind="faculty",
            roles=("hod",),
            modules=("hr_eis",),
            permissions=("hr_eis.appraisal.review", "hr_eis.appraisal.view_all"),
        ),
        users={
            202: user_ref(202, name="Dr. Banner", kind="faculty"),
            301: user_ref(301, name="HOD Reviewer", kind="faculty"),
        },
    )

    rev_client = APIClient()
    rev_client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    rev_resp = rev_client.post(
        f"/api/v1/hreis/appraisals/{appraisal_id}/review/",
        {"score": 9.2, "comments": "Outstanding performance in teaching and research."},
        format="json",
    )
    assert rev_resp.status_code == 200

    # 5. Director finalizes appraisal
    stub_iam(
        make_session(
            user_id=1,
            kind="faculty",
            roles=("director",),
            modules=("hr_eis",),
            permissions=("hr_eis.appraisal.finalize", "hr_eis.appraisal.view_all"),
        ),
        users={
            1: user_ref(1, name="Director Sir", kind="faculty"),
            202: user_ref(202, name="Dr. Banner", kind="faculty"),
        },
    )

    dir_client = APIClient()
    dir_client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    fin_resp = dir_client.post(
        f"/api/v1/hreis/appraisals/{appraisal_id}/finalize/",
        {"final_score": 9.2, "final_remarks": "Approved and finalized."},
        format="json",
    )
    assert fin_resp.status_code == 200
    assert fin_resp.json()["status"] == "finalized"
