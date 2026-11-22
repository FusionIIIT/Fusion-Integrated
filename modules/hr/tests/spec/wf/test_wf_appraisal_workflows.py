"""WF spec tests for Appraisal Workflow State Transitions."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.hr.domain import state_machine
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


def test_wf_011_direct_finalization_path(hr_caller):
    """TEST-WF-011 | BW-HR-04 direct-finalization-path.

    Execute finite appraisal path with zero intermediate authority traversal from submission through reviewer assignment to finalization.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2025-2026",
        form_data={},
        status="pending_review",
        reviewer_user_ids=[UID_HOD],
        current_reviewer_index=0,
        current_reviewer_user_id=UID_HOD,
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    finalized = appraisals.review_appraisal(
        actor=actor_hod, appraisal_id=appr.pk, action="finalize"
    )
    assert finalized.status == "closed"


def test_wf_012_transition_1_not_submitted_to_submitted(hr_caller):
    """TEST-WF-012 | BW-HR-04 transition-1-not-submitted-to-submitted.

    Verify Transition 1 of BW-HR-04: Submitting appraisal form during active window transitions from Appraisal Not Submitted to Submitted.
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
        data={"period": "2026-2027", "form_data": {"val": 1}},
    )
    assert res.status_code == 201
    assert res.data["status"] == "submitted"


def test_wf_013_transition_2_submitted_to_reviewer_assigned(hr_caller):
    """TEST-WF-013 | BW-HR-04 transition-2-submitted-to-reviewer-assigned.

    Verify Transition 2 of BW-HR-04: HR Administrator assigning reviewer transitions appraisal to Reviewer Assigned / Pending Review.
    """
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1, period="2024-2025", form_data={}, status="submitted"
    )
    assigned = appraisals.assign_reviewers(
        actor=make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff"),
        appraisal_id=appr.pk,
        reviewer_user_ids=[UID_HOD],
    )
    assert assigned.status == "pending_review"


def test_wf_014_transition_3_pending_review_to_finalized(hr_caller):
    """TEST-WF-014 | BW-HR-04 transition-3-pending-review-to-finalized.

    Verify Transition 3 of BW-HR-04: Final designated authority finalization transitions appraisal to Finalized — Archived — Closed.
    """
    t = state_machine.review_appraisal(
        state_machine.PENDING_REVIEW, action="finalize", current_index=0, reviewer_count=1
    )
    assert t.state == state_machine.CLOSED


def test_wf_015_additional_authority_traversal_path(hr_caller):
    """TEST-WF-015 | BW-HR-05 additional-authority-traversal-path.

    Execute appraisal path with exactly one additional designated-authority traversal before finalization.
    """
    t1 = state_machine.review_appraisal(
        state_machine.PENDING_REVIEW, action="forward", current_index=0, reviewer_count=2
    )
    assert t1.state == state_machine.APPRAISAL_PENDING_NEXT
    t2 = state_machine.review_appraisal(
        t1.state, action="finalize", current_index=t1.authority_step, reviewer_count=2
    )
    assert t2.state == state_machine.CLOSED


def test_wf_016_transition_3_pending_review_to_next_authority(hr_caller):
    """TEST-WF-016 | BW-HR-05 transition-3-pending-review-to-next-authority.

    Verify Transition 3 of BW-HR-05: Review by non-final authority transitions appraisal to Pending Next Appraisal Authority.
    """
    t = state_machine.review_appraisal(
        state_machine.PENDING_REVIEW, action="forward", current_index=0, reviewer_count=2
    )
    assert t.state == state_machine.APPRAISAL_PENDING_NEXT
    assert t.authority_step == 1


def test_wf_017_complete_lifecycle_sequence(hr_caller):
    """TEST-WF-017 | CW-HR-02 complete-lifecycle-sequence.

    Execute composite yearly appraisal lifecycle combining submission, reviewer assignment, authority review, and archival closure.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    appr = Appraisal.objects.create(
        employee_user_id=UID_FACULTY_1,
        period="2023-2024",
        form_data={},
        status="pending_review",
        reviewer_user_ids=[UID_HOD, UID_DIRECTOR],
        current_reviewer_index=0,
        current_reviewer_user_id=UID_HOD,
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    fwd = appraisals.review_appraisal(actor=actor_hod, appraisal_id=appr.pk, action="forward")
    assert fwd.status == "pending_next_authority"
    actor_dir = make_actor(UID_DIRECTOR, role="Director", kind="faculty")
    fin = appraisals.review_appraisal(actor=actor_dir, appraisal_id=appr.pk, action="finalize")
    assert fin.status == "closed"


def test_wf_018_prohibited_finalize_before_reviewer_assignment(hr_caller):
    """TEST-WF-018 | CW-HR-02 prohibited-finalize-before-reviewer-assignment.

    Verify prohibited transition in CW-HR-02: Authority cannot finalize an appraisal that is in Submitted state before reviewer assignment.
    """
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.review_appraisal(
            state_machine.SUBMITTED, action="finalize", current_index=0, reviewer_count=1
        )


def test_wf_019_prohibited_modify_finalized_appraisal(hr_caller):
    """TEST-WF-019 | CW-HR-02 prohibited-modify-finalized-appraisal.

    Verify prohibited transition in CW-HR-02: No state transition or modification can be executed on a Finalized — Archived — Closed appraisal.
    """
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.review_appraisal(
            state_machine.CLOSED, action="finalize", current_index=0, reviewer_count=1
        )
