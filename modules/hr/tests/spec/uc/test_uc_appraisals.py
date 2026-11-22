"""UC spec tests for Appraisal Submission, Reviewer Assignment, and Review."""

from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.hr.models import Appraisal, AppraisalWindow
from modules.hr.services import appraisals
from modules.hr.tests.spec.conftest import (
    UID_DIRECTOR,
    UID_FACULTY_1,
    UID_FACULTY_2,
    UID_HOD,
    UID_HR_ADMIN,
    UID_UNAUTHORIZED,
    ensure_employee,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_uc_017_main_flow_submit_appraisal(hr_caller):
    """TEST-UC-017 | HR-UC-006 Main Flow.

    Verify that an Employee can complete and submit the yearly appraisal form when the configured submission window is active.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    now = timezone.now()
    AppraisalWindow.objects.update_or_create(
        period="2026-2027",
        defaults={
            "opens_at": now - timedelta(days=2),
            "closes_at": now + timedelta(days=20),
            "is_active": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    res = hr_caller(
        "post",
        "/api/v1/hr/appraisals/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"period": "2026-2027", "form_data": {"key": "val"}},
    )
    assert res.status_code == 201


def test_uc_018_alternative_a1_window_inactive(hr_caller):
    """TEST-UC-018 | HR-UC-006 Alternative A1.

    Verify that if the configured appraisal submission window is not active, HR-EIS does not accept the submission.
    """
    now = timezone.now()
    AppraisalWindow.objects.update_or_create(
        period="2018-2019",
        defaults={
            "opens_at": now - timedelta(days=60),
            "closes_at": now - timedelta(days=30),
            "is_active": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    res = hr_caller(
        "post",
        "/api/v1/hr/appraisals/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"period": "2018-2019", "form_data": {"key": "val"}},
    )
    assert res.status_code == 422


def test_uc_019_exception_e1_unauthorized_appraisal_submission(hr_caller):
    """TEST-UC-019 | HR-UC-006 Exception E1.

    Verify that unauthorized appraisal submission attempts are blocked by RBAC.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/appraisals/create/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        permissions=(),
        data={"period": "2026-2027", "form_data": {}},
    )
    assert res.status_code == 403


def test_uc_020_main_flow_assign_reviewers(hr_caller):
    """TEST-UC-020 | HR-UC-007 Main Flow.

    Verify that HR Administrator can assign required reviewers for appraisal evaluation.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1, period="2024-2025", form_data={}, status="submitted"
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/appraisals/{appr.pk}/reviewers/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"reviewer_user_ids": [UID_HOD, UID_DIRECTOR]},
    )
    assert res.status_code == 200
    assert res.data["status"] == "pending_review"


def test_uc_021_alternative_a1_revise_reviewers_before_review(hr_caller):
    """TEST-UC-021 | HR-UC-007 Alternative A1.

    Verify that HR Administrator can revise reviewer assignment before review begins without altering appraisal outcome.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1, period="2023-2024", form_data={}, status="submitted"
    )
    actor = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    appraisals.assign_reviewers(actor=actor, appraisal_id=appr.pk, reviewer_user_ids=[UID_HOD])
    # Reset status for revision before review starts
    appr.status = "submitted"
    appr.save()
    revised = appraisals.assign_reviewers(
        actor=actor, appraisal_id=appr.pk, reviewer_user_ids=[UID_DIRECTOR]
    )
    assert revised.reviewer_user_ids == [UID_DIRECTOR]


def test_uc_022_exception_e1_unauthorized_reviewer_assignment(hr_caller):
    """TEST-UC-022 | HR-UC-007 Exception E1.

    Verify that an unauthorized user cannot assign appraisal reviewers.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1, period="2022-2023", form_data={}, status="submitted"
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/appraisals/{appr.pk}/reviewers/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"reviewer_user_ids": [UID_HOD]},
    )
    assert res.status_code == 403


def test_uc_023_main_flow_review_and_finalize_appraisal(hr_caller):
    """TEST-UC-023 | HR-UC-008 Main Flow.

    Verify that Approving Authority can review an assigned appraisal, record evaluation ratings, and finalize it into the employee service record.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2021-2022",
        form_data={},
        status="pending_review",
        reviewer_user_ids=[UID_HOD],
        current_reviewer_index=0,
        current_reviewer_user_id=UID_HOD,
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    finalized = appraisals.review_appraisal(
        actor=actor_hod, appraisal_id=appr.pk, action="finalize", note="Outstanding"
    )
    assert finalized.status == "closed"
    assert finalized.finalized_at is not None


def test_uc_024_alternative_a1_multi_stage_review_traversal(hr_caller):
    """TEST-UC-024 | HR-UC-008 Alternative A1.

    Verify that an additional designated-authority review traversal occurs before finalization when configured, following configured routes.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2020-2021",
        form_data={},
        status="pending_review",
        reviewer_user_ids=[UID_HOD, UID_DIRECTOR],
        current_reviewer_index=0,
        current_reviewer_user_id=UID_HOD,
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    forwarded = appraisals.review_appraisal(
        actor=actor_hod, appraisal_id=appr.pk, action="forward", note="Good"
    )
    assert forwarded.status == "pending_next_authority"
    assert forwarded.current_reviewer_user_id == UID_DIRECTOR


def test_uc_025_exception_e1_modify_after_closure_blocked(hr_caller):
    """TEST-UC-025 | HR-UC-008 Exception E1.

    Verify that modification of an appraisal record after closure is blocked.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2017-2018",
        form_data={},
        status="closed",
        finalized_at=timezone.now(),
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    with pytest.raises(ConflictError):
        appraisals.review_appraisal(actor=actor_hod, appraisal_id=appr.pk, action="finalize")


def test_uc_026_exception_e2_non_designated_reviewer_blocked(hr_caller):
    """TEST-UC-026 | HR-UC-008 Exception E2.

    Verify that an actor not currently designated for review cannot finalize the appraisal.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2016-2017",
        form_data={},
        status="pending_review",
        reviewer_user_ids=[UID_HOD],
        current_reviewer_index=0,
        current_reviewer_user_id=UID_HOD,
    )
    # Actor UID_FACULTY_2 is not the designated reviewer
    res = hr_caller(
        "post",
        f"/api/v1/hr/appraisals/{appr.pk}/review/",
        user_id=UID_FACULTY_2,
        role="Head of Department",
        kind="faculty",
        data={"action": "finalize"},
    )
    assert res.status_code in (403, 404)
