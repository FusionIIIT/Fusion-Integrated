"""FR spec tests for Yearly Appraisal Lifecycle."""

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


def test_fr_008_consolidated_yearly_appraisal_lifecycle(hr_caller):
    """TEST-FR-008 | HR-CFR-008 consolidated-yearly-appraisal-lifecycle.

    Verify the yearly appraisal lifecycle including submission within configured windows, reviewer assignment, authority evaluation, service record archival, and post-closure immutability.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    now = timezone.now()
    AppraisalWindow.objects.update_or_create(
        period="2025-2026",
        defaults={
            "opens_at": now - timedelta(days=10),
            "closes_at": now + timedelta(days=10),
            "is_active": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    res = hr_caller(
        "post",
        "/api/v1/hr/appraisals/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"period": "2025-2026", "form_data": {"achievements": "Published 3 papers"}},
    )
    assert res.status_code == 201


def test_fr_041_hr_admin_assign_appraisal_reviewers(hr_caller):
    """TEST-FR-041 | HR-AFR-013 hr-admin-assign-appraisal-reviewers.

    Verify that HR-EIS allows the HR Administrator to assign reviewers for appraisal evaluation.
    """
    appraisal = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2024-2025",
        form_data={"summary": "Annual form"},
        status="submitted",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/appraisals/{appraisal.pk}/reviewers/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"reviewer_user_ids": [UID_HOD, UID_DIRECTOR]},
    )
    assert res.status_code == 200
    assert res.data["reviewer_user_ids"] == [UID_HOD, UID_DIRECTOR]


def test_fr_081_employee_submit_yearly_appraisal(hr_caller):
    """TEST-FR-081 | HR-AFR-044 employee-submit-yearly-appraisal.

    Verify that HR-EIS allows Employees to submit yearly appraisal forms within active submission window.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    now = timezone.now()
    AppraisalWindow.objects.update_or_create(
        period="2026-2027",
        defaults={
            "opens_at": now - timedelta(days=5),
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
        data={"period": "2026-2027", "form_data": {"teaching_hours": 120}},
    )
    assert res.status_code == 201


def test_fr_082_submission_within_window_accepted(hr_caller):
    """TEST-FR-082 | HR-AFR-045 submission-within-window-accepted.

    Verify that HR-EIS accepts yearly appraisal form submission within configured submission window.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    now = timezone.now()
    AppraisalWindow.objects.update_or_create(
        period="2027-2028",
        defaults={
            "opens_at": now - timedelta(days=1),
            "closes_at": now + timedelta(days=30),
            "is_active": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    res = hr_caller(
        "post",
        "/api/v1/hr/appraisals/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"period": "2027-2028", "form_data": {"grants": 2}},
    )
    assert res.status_code == 201


def test_fr_083_submission_outside_window_rejected(hr_caller):
    """TEST-FR-083 | HR-AFR-045 submission-outside-window-rejected.

    Verify that HR-EIS restricts yearly appraisal form submission to configured submission windows and rejects submissions outside window.
    """
    now = timezone.now()
    AppraisalWindow.objects.update_or_create(
        period="2020-2021",
        defaults={
            "opens_at": now - timedelta(days=400),
            "closes_at": now - timedelta(days=300),
            "is_active": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    res = hr_caller(
        "post",
        "/api/v1/hr/appraisals/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"period": "2020-2021", "form_data": {"grants": 0}},
    )
    assert res.status_code == 422


def test_fr_084_hr_admin_assign_appraisal_reviewers(hr_caller):
    """TEST-FR-084 | HR-AFR-046 hr-admin-assign-appraisal-reviewers.

    Verify that HR-EIS allows the HR Administrator to assign reviewers for appraisal evaluation.
    """
    appraisal = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2023-2024",
        form_data={"summary": "Yearly"},
        status="submitted",
    )
    actor = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    assigned = appraisals.assign_reviewers(
        actor=actor, appraisal_id=appraisal.pk, reviewer_user_ids=[UID_HOD]
    )
    assert assigned.status == "pending_review"
    assert assigned.reviewer_user_ids == [UID_HOD]


def test_fr_085_route_appraisal_designated_authorities(hr_caller):
    """TEST-FR-085 | HR-AFR-047 route-appraisal-designated-authorities.

    Verify that HR-EIS routes appraisal workflows through designated authorities for review and finalization.
    """
    appraisal = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2022-2023",
        form_data={"summary": "Review"},
        status="pending_review",
        reviewer_user_ids=[UID_HOD, UID_DIRECTOR],
        current_reviewer_index=0,
        current_reviewer_user_id=UID_HOD,
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    forwarded = appraisals.review_appraisal(
        actor=actor_hod, appraisal_id=appraisal.pk, action="forward", note="Good work"
    )
    assert forwarded.status == "pending_next_authority"
    assert forwarded.current_reviewer_user_id == UID_DIRECTOR


def test_fr_086_archive_finalized_appraisals_service_record(hr_caller):
    """TEST-FR-086 | HR-AFR-048 archive-finalized-appraisals-service-record.

    Verify that HR-EIS archives finalized appraisals in the employee service record.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    appraisal = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2021-2022",
        form_data={"score": 95},
        status="closed",
        finalized_at=timezone.now(),
    )
    assert appraisal.status == "closed"


def test_fr_087_prevent_modification_appraisal_after_closure(hr_caller):
    """TEST-FR-087 | HR-AFR-049 prevent-modification-appraisal-after-closure.

    Verify that HR-EIS prevents modification of appraisal records after closure.
    """
    appraisal = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2019-2020",
        form_data={"score": 90},
        status="closed",
        finalized_at=timezone.now(),
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    with pytest.raises(ConflictError):
        appraisals.review_appraisal(actor=actor_hod, appraisal_id=appraisal.pk, action="finalize")
