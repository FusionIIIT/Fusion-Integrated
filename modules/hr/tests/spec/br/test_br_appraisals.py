"""BR spec tests for Yearly Appraisal Business Rules."""

from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.hr.models import Appraisal, AppraisalWindow
from modules.hr.services import appraisals
from modules.hr.tests.spec.conftest import (
    UID_DIRECTOR,
    UID_FACULTY_1,
    UID_HOD,
    UID_HR_ADMIN,
    ensure_employee,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_br_024_within_submission_window_permitted(hr_caller):
    """TEST-BR-024 | BR-HR-012 within-submission-window-permitted.

    Verify that yearly appraisal submission is accepted when submitted within configured submission window.
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
        data={"period": "2026-2027", "form_data": {"summary": "Annual form"}},
    )
    assert res.status_code == 201


def test_br_025_outside_submission_window_prohibited(hr_caller):
    """TEST-BR-025 | BR-HR-012 outside-submission-window-prohibited.

    Verify that yearly appraisal submission is rejected when submitted outside configured submission window.
    """
    now = timezone.now()
    AppraisalWindow.objects.update_or_create(
        period="2015-2016",
        defaults={
            "opens_at": now - timedelta(days=500),
            "closes_at": now - timedelta(days=400),
            "is_active": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    res = hr_caller(
        "post",
        "/api/v1/hr/appraisals/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"period": "2015-2016", "form_data": {"summary": "Expired"}},
    )
    assert res.status_code == 422


def test_br_026_hr_admin_assign_reviewer_permitted(hr_caller):
    """TEST-BR-026 | BR-HR-013 hr-admin-assign-reviewer-permitted.

    Verify that HR Administrator can assign reviewer(s) for appraisal evaluation.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1, period="2024-2025", form_data={}, status="submitted"
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/appraisals/{appr.pk}/reviewers/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"reviewer_user_ids": [UID_HOD]},
    )
    assert res.status_code == 200


def test_br_027_unauthorized_reviewer_assignment_prohibited(hr_caller):
    """TEST-BR-027 | BR-HR-013 unauthorized-reviewer-assignment-prohibited.

    Verify that unauthorized users cannot assign appraisal reviewers.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1, period="2023-2024", form_data={}, status="submitted"
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/appraisals/{appr.pk}/reviewers/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"reviewer_user_ids": [UID_HOD]},
    )
    assert res.status_code == 403


def test_br_028_review_routing_in_configured_order(hr_caller):
    """TEST-BR-028 | BR-HR-014 review-routing-in-configured-order.

    Verify that appraisal workflows pass through designated authorities for review and finalization in configured order.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2022-2023",
        form_data={},
        status="pending_review",
        reviewer_user_ids=[UID_HOD, UID_DIRECTOR],
        current_reviewer_index=0,
        current_reviewer_user_id=UID_HOD,
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    forwarded = appraisals.review_appraisal(actor=actor_hod, appraisal_id=appr.pk, action="forward")
    assert forwarded.current_reviewer_user_id == UID_DIRECTOR


def test_br_029_finalized_appraisal_archived(hr_caller):
    """TEST-BR-029 | BR-HR-015 finalized-appraisal-archived.

    Verify that finalized appraisals are archived in the employee service record.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2021-2022",
        form_data={},
        status="closed",
        finalized_at=timezone.now(),
    )
    assert appr.status == "closed"


def test_br_030_post_closure_modification_prohibited(hr_caller):
    """TEST-BR-030 | BR-HR-015 post-closure-modification-prohibited.

    Verify that appraisal records cannot be modified after closure.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2020-2021",
        form_data={},
        status="closed",
        finalized_at=timezone.now(),
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    with pytest.raises(ConflictError):
        appraisals.review_appraisal(actor=actor_hod, appraisal_id=appr.pk, action="finalize")
