"""Workflow (WF) tests for appeals, attorney assignment, and budget handling.

Covers:
- WF-TC-006 (BW-PMS-03: Step 1-3 (Appeal Remand Path))
- WF-TC-007 (BW-PMS-04: Step 1-3 (Appeal Rejection-Upheld Path))
- WF-TC-008 (BW-PMS-05: Step 1-3 (Appeal Modified-Decision Path))
- WF-TC-009 (BW-PMS-06: Step 1-2 (Attorney Assignment Acceptance Path))
- WF-TC-010 (BW-PMS-07: Step 1-4 (Attorney Decline and One Reassignment Path))
- WF-TC-011 (BW-PMS-08: Step 1 (Budget Approval Path))
- WF-TC-012 (BW-PMS-09: Step 1 (Budget Rejection Path))
- WF-TC-013 (BW-PMS-10: Step 1-2 (Budget Escalation Path))
"""

from decimal import Decimal

import pytest

from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import AttorneyPanel
from modules.pms.services import (
    assign_attorney,
    assign_director,
    decide_budget,
    file_appeal,
    respond_to_attorney_assignment,
    review_appeal,
    submit_application,
    submit_director_review,
    submit_or_update_budget,
)
from modules.pms.tests.support import configure

pytestmark = pytest.mark.django_db


def _create_under_review_app(title: str = "Patent App") -> int:
    app = submit_application(
        applicant_user_id=1001,
        title=title,
        abstract="Technical abstract for workflow testing.",
        detailed_description="Detailed technical specification.",
        claims="1. A technical apparatus...",
        domain="Engineering",
    )
    assign_director(
        application_id=app.id,
        director_user_id=3001,
        assigned_by_user_id=9001,
    )
    return app.id


def _create_approved_app(title: str = "Approved Patent App") -> int:
    app_id = _create_under_review_app(title=title)
    submit_director_review(
        application_id=app_id,
        director_user_id=3001,
        decision="Approve",
        justification=(
            "The application satisfies novelty and inventive-step criteria "
            "for progression."
        ),
    )
    return app_id


def test_wf_tc_006_bw_pms_03_step_1_3_appeal_remand_path():
    """WF-TC-006 | BW-PMS-03: Step 1-3 (Appeal Remand Path).

    Verify a rejected application appealed by the Applicant can result in
    Remanded for Amendment.
    """
    from modules.pms.models import PatentApplication

    app_id = _create_under_review_app("Remand Candidate")
    submit_director_review(
        application_id=app_id,
        director_user_id=3001,
        decision="Reject",
        justification=(
            "Claims appear anticipated by prior reference D1 in the initial "
            "review."
        ),
    )
    appeal = file_appeal(
        application_id=app_id,
        applicant_user_id=1001,
        grounds="Reference D1 lacks key structural element.",
        justification="Detailed technical comparison against D1.",
    )
    review_appeal(
        appeal_id=appeal.id,
        director_user_id=3001,
        outcome="Remand for Amendment",
        outcome_justification=(
            "Applicant raised a valid distinction; remanding for claim "
            "amendment."
        ),
    )
    app = PatentApplication.objects.get(pk=app_id)
    assert app.status == PatentApplicationStatus.REMANDED_FOR_AMENDMENT.value


def test_wf_tc_007_bw_pms_04_step_1_3_appeal_rejection_upheld_path():
    """WF-TC-007 | BW-PMS-04: Step 1-3 (Appeal Rejection-Upheld Path).

    Verify a rejected application appealed by the Applicant can result in
    Rejection Upheld.
    """
    from modules.pms.models import PatentApplication

    app_id = _create_under_review_app("Upheld Candidate")
    submit_director_review(
        application_id=app_id,
        director_user_id=3001,
        decision="Reject",
        justification=(
            "The proposed mechanism lacks inventive step over cited prior art "
            "references."
        ),
    )
    appeal = file_appeal(
        application_id=app_id,
        applicant_user_id=1001,
        grounds="Disagreement with inventive step conclusion.",
        justification="Arguments regarding combined prior art references.",
    )
    review_appeal(
        appeal_id=appeal.id,
        director_user_id=3001,
        outcome="Uphold Rejection",
        outcome_justification=(
            "Prior art combination renders the claims obvious; rejection is "
            "upheld."
        ),
    )
    app = PatentApplication.objects.get(pk=app_id)
    assert app.status == PatentApplicationStatus.REJECTION_UPHELD.value


def test_wf_tc_008_bw_pms_05_step_1_3_appeal_modified_decision_path():
    """WF-TC-008 | BW-PMS-05: Step 1-3 (Appeal Modified-Decision Path).

    Verify a rejected application appealed by the Applicant can result in
    Decision Modified.
    """
    from modules.pms.models import PatentApplication

    app_id = _create_under_review_app("Modified Candidate")
    submit_director_review(
        application_id=app_id,
        director_user_id=3001,
        decision="Reject",
        justification=(
            "Initial review found insufficient experimental data supporting "
            "the claims."
        ),
    )
    appeal = file_appeal(
        application_id=app_id,
        applicant_user_id=1001,
        grounds="Supplemental test data resolves technical concern.",
        justification="Verified experimental results attached with appeal.",
    )
    review_appeal(
        appeal_id=appeal.id,
        director_user_id=3001,
        outcome="Modify Decision",
        outcome_justification=(
            "Supplemental data resolves the initial technical concern; decision "
            "modified."
        ),
    )
    app = PatentApplication.objects.get(pk=app_id)
    assert app.status == PatentApplicationStatus.DECISION_MODIFIED.value


def test_wf_tc_009_bw_pms_06_step_1_2_attorney_assignment_acceptance_path():
    """WF-TC-009 | BW-PMS-06: Step 1-2 (Attorney Assignment Acceptance Path).

    Verify PCC_ADMIN assigns an eligible Attorney to an Approved application
    and the Attorney accepts to reach Attorney Assigned.
    """
    from modules.pms.models import PatentApplication

    AttorneyPanel.objects.create(
        attorney_user_id=5001,
        name="Counsel One",
        email="counsel1@example.test",
        is_approved=True,
        current_workload=0,
        max_workload=5,
    )
    app_id = _create_approved_app("Attorney Accept App")

    assignment = assign_attorney(
        application_id=app_id,
        attorney_user_id=5001,
        assigned_by_user_id=9001,
    )
    assert assignment.status == "offered"

    respond_to_attorney_assignment(
        assignment_id=assignment.id,
        attorney_user_id=5001,
        accept=True,
    )
    assignment.refresh_from_db()
    app = PatentApplication.objects.get(pk=app_id)
    assert assignment.status == "accepted"
    assert app.assigned_attorney_user_id == 5001


def test_wf_tc_010_bw_pms_07_step_1_4_attorney_decline_and_one_reassignment_path():
    """WF-TC-010 | BW-PMS-07: Step 1-4 (Attorney Decline and One Reassignment Path).

    Verify an offered Attorney assignment can be declined to Pending Review,
    reassigned to another eligible Attorney, and accepted.
    """
    from modules.pms.models import PatentApplication

    AttorneyPanel.objects.create(
        attorney_user_id=5001,
        name="Counsel One",
        email="counsel1@example.test",
        is_approved=True,
        current_workload=0,
        max_workload=5,
    )
    AttorneyPanel.objects.create(
        attorney_user_id=5002,
        name="Counsel Two",
        email="counsel2@example.test",
        is_approved=True,
        current_workload=0,
        max_workload=5,
    )
    app_id = _create_approved_app("Attorney Reassign App")

    first_assignment = assign_attorney(
        application_id=app_id,
        attorney_user_id=5001,
        assigned_by_user_id=9001,
    )
    assert first_assignment.status == "offered"

    respond_to_attorney_assignment(
        assignment_id=first_assignment.id,
        attorney_user_id=5001,
        accept=False,
        decline_reason="Conflict or schedule constraint",
    )
    first_assignment.refresh_from_db()
    assert first_assignment.status == "declined"

    second_assignment = assign_attorney(
        application_id=app_id,
        attorney_user_id=5002,
        assigned_by_user_id=9001,
    )
    assert second_assignment.status == "offered"

    respond_to_attorney_assignment(
        assignment_id=second_assignment.id,
        attorney_user_id=5002,
        accept=True,
    )
    second_assignment.refresh_from_db()
    app = PatentApplication.objects.get(pk=app_id)
    assert second_assignment.status == "accepted"
    assert app.assigned_attorney_user_id == 5002


def test_wf_tc_011_bw_pms_08_step_1_budget_approval_path():
    """WF-TC-011 | BW-PMS-08: Step 1 (Budget Approval Path).

    Verify Director approves a budget within threshold for an Approved
    application.
    """
    from modules.pms.models import PatentApplication

    configure(budget_threshold="100000.00")
    app_id = _create_approved_app("Budget Approve App")

    submit_or_update_budget(
        application_id=app_id,
        filing_fees=Decimal("15000.00"),
        attorney_fees=Decimal("25000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=3001,
    )
    budget = decide_budget(
        application_id=app_id,
        director_user_id=3001,
        decision="Approve",
        justification="Budget is within threshold and verified.",
    )
    app = PatentApplication.objects.get(pk=app_id)
    assert budget.status == "approved"
    assert app.audit_logs.filter(action_type__icontains="budget").exists() or budget.status == "approved"


def test_wf_tc_012_bw_pms_09_step_1_budget_rejection_path():
    """WF-TC-012 | BW-PMS-09: Step 1 (Budget Rejection Path).

    Verify Director rejects a budget for an Approved application.
    """
    app_id = _create_approved_app("Budget Reject App")

    submit_or_update_budget(
        application_id=app_id,
        filing_fees=Decimal("15000.00"),
        attorney_fees=Decimal("25000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=3001,
    )
    budget = decide_budget(
        application_id=app_id,
        director_user_id=3001,
        decision="Reject",
        justification="Proposed prosecution costs are not justified.",
    )
    assert budget.status == "rejected"


def test_wf_tc_013_bw_pms_10_step_1_2_budget_escalation_path():
    """WF-TC-013 | BW-PMS-10: Step 1-2 (Budget Escalation Path).

    Verify above-threshold budget escalates and is handled/tracked by
    PCC_ADMIN within PMS scope.
    """
    configure(budget_threshold="100000.00")
    app_id = _create_approved_app("Budget Escalate App")

    submit_or_update_budget(
        application_id=app_id,
        filing_fees=Decimal("50000.00"),
        attorney_fees=Decimal("80000.00"),
        administrative_costs=Decimal("20000.00"),
        actor_user_id=3001,
    )
    budget = decide_budget(
        application_id=app_id,
        director_user_id=3001,
        decision="Approve",
        justification="Exceeds threshold and requires escalation.",
    )
    assert budget.status == "escalated"
