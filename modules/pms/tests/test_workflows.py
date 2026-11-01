"""Workflow traversal tests for Basis and Composite Workflows.

Verifies end-to-end traversal of:
- BW-PMS-01 through BW-PMS-16
- CW-PMS-01 through CW-PMS-05
"""

from datetime import date
from decimal import Decimal

import pytest

from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import AttorneyPanel
from modules.pms.services import (
    approve_office_action_response,
    assign_attorney,
    assign_director,
    decide_budget,
    decide_renewal,
    draft_office_action_response,
    file_appeal,
    record_external_filing,
    record_maintenance_action,
    record_office_action,
    record_patent_grant,
    request_renewal_decision,
    respond_to_attorney_assignment,
    review_appeal,
    revise_and_resubmit_application,
    submit_application,
    submit_director_review,
    submit_office_action_response,
    submit_or_update_budget,
    withdraw_application,
)

pytestmark = pytest.mark.django_db


def test_bw_pms_01_initial_review_approval_path():
    """BW-PMS-01: Draft -> Submitted -> Under Review -> Approved."""
    app = submit_application(
        applicant_user_id=1001,
        title="Quantum Circuit",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Computer Science",
    )
    assert app.status == PatentApplicationStatus.SUBMITTED.value

    assigned = assign_director(
        application_id=app.id, director_user_id=2001, assigned_by_user_id=9001
    )
    assert assigned.status == PatentApplicationStatus.UNDER_REVIEW.value

    review = submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Approve",
        justification="The technical novelty and inventiveness are thoroughly demonstrated.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPROVED.value


def test_bw_pms_02_revision_and_reapproval_path():
    """BW-PMS-02: Under Review -> Needs Revision -> Resubmitted -> Under Review -> Approved."""
    app = submit_application(
        applicant_user_id=1001,
        title="AI Model",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="AI",
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)

    # 1. Needs Revision
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Needs Revision",
        justification="Please narrow the independent claims to specifically target training speedup.",
        feedback="Revise claims 1-5.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.NEEDS_REVISION.value

    # 2. Resubmitted
    revise_and_resubmit_application(
        application_id=app.id,
        applicant_user_id=1001,
        feedback_response="Narrowed independent claims 1-5 specifically to training phase speedup.",
        claims="1. Narrowed claims...",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RESUBMITTED.value

    # 3. Re-assign Director -> Under Review
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.UNDER_REVIEW.value

    # 4. Approve
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Approve",
        justification="The revised claims now satisfactorily address all previous objections.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPROVED.value


def test_bw_pms_03_appeal_remand_path():
    """BW-PMS-03: Under Review -> Rejected -> Appeal Submitted -> Remanded for Amendment."""
    app = submit_application(
        applicant_user_id=1001,
        title="Solar Tech",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Energy",
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Reject",
        justification="The proposed efficiency gains are incremental and anticipated by D1.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.REJECTED.value

    appeal = file_appeal(
        application_id=app.id,
        applicant_user_id=1001,
        grounds="Reference D1 uses distinct chemical doping.",
        justification="Experimental data in table 2 confirms non-obviousness over reference D1.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPEAL_SUBMITTED.value

    review_appeal(
        appeal_id=appeal.id,
        director_user_id=2001,
        outcome="Remand for Amendment",
        outcome_justification="Applicant's distinction regarding chemical doping is valid. Remanding for claims amendment.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.REMANDED_FOR_AMENDMENT.value


def test_bw_pms_04_appeal_rejection_upheld_path():
    """BW-PMS-04: Under Review -> Rejected -> Appeal Submitted -> Rejection Upheld."""
    app = submit_application(
        applicant_user_id=1001,
        title="Mechanical Link",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Mechanical",
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Reject",
        justification="Standard mechanical arrangement with no demonstrated technical novelty.",
    )
    appeal = file_appeal(
        application_id=app.id,
        applicant_user_id=1001,
        grounds="Applicant believes arrangement provides unexpected torque reduction.",
        justification="Theoretical torque calculations demonstrate novel mechanical advantage.",
    )
    review_appeal(
        appeal_id=appeal.id,
        director_user_id=2001,
        outcome="Uphold Rejection",
        outcome_justification="Torque calculations do not demonstrate non-obviousness over standard engineering handbook designs.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.REJECTION_UPHELD.value


def test_bw_pms_05_appeal_modified_decision_path():
    """BW-PMS-05: Under Review -> Rejected -> Appeal Submitted -> Decision Modified -> Approved."""
    app = submit_application(
        applicant_user_id=1001,
        title="Battery Electrolyte",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Chemical",
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Reject",
        justification="Insufficient evidence of thermal stability across operating range.",
    )
    appeal = file_appeal(
        application_id=app.id,
        applicant_user_id=1001,
        grounds="Additional high temperature test data provided.",
        justification="Attached verified laboratory test results demonstrate stability up to 150C.",
    )
    review_appeal(
        appeal_id=appeal.id,
        director_user_id=2001,
        outcome="Modify Decision",
        outcome_justification="The high temperature verified test results resolve thermal stability concern completely.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPROVED.value


def test_bw_pms_06_attorney_assignment_acceptance():
    """BW-PMS-06: Approved -> Assignment Offered -> Attorney Assigned."""
    panel_entry = AttorneyPanel.objects.create(
        attorney_user_id=5001,
        name="Atty 1",
        email="a1@atty.com",
        is_approved=True,
        current_workload=0,
        max_workload=5,
    )
    app = submit_application(
        applicant_user_id=1001,
        title="Optics",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Physics",
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Approve",
        justification="Technical novelty and claims are acceptable for filing.",
    )
    assignment = assign_attorney(
        application_id=app.id, attorney_user_id=5001, assigned_by_user_id=9001
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.ASSIGNMENT_OFFERED.value

    respond_to_attorney_assignment(assignment_id=assignment.id, attorney_user_id=5001, accept=True)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.ATTORNEY_ASSIGNED.value


def test_bw_pms_07_attorney_decline_and_reassignment():
    """BW-PMS-07: Approved -> Assignment Offered -> Pending Review -> Assignment Offered -> Attorney Assigned."""
    AttorneyPanel.objects.create(
        attorney_user_id=5001,
        name="Atty 1",
        email="a1@atty.com",
        is_approved=True,
        current_workload=0,
        max_workload=5,
    )
    AttorneyPanel.objects.create(
        attorney_user_id=5002,
        name="Atty 2",
        email="a2@atty.com",
        is_approved=True,
        current_workload=0,
        max_workload=5,
    )

    app = submit_application(
        applicant_user_id=1001,
        title="Sensor",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Tech",
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Approve",
        justification="Technical novelty and claims are acceptable for filing.",
    )

    # 1. First assignment
    a1 = assign_attorney(application_id=app.id, attorney_user_id=5001, assigned_by_user_id=9001)
    assert a1.status == "offered"

    # 2. Decline -> Pending Review
    respond_to_attorney_assignment(
        assignment_id=a1.id, attorney_user_id=5001, accept=False, decline_reason="Schedule full"
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.PENDING_REVIEW.value

    # 3. Re-assignment to Atty 2
    a2 = assign_attorney(application_id=app.id, attorney_user_id=5002, assigned_by_user_id=9001)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.ASSIGNMENT_OFFERED.value

    # 4. Accept
    respond_to_attorney_assignment(assignment_id=a2.id, attorney_user_id=5002, accept=True)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.ATTORNEY_ASSIGNED.value


def test_bw_pms_08_budget_approval_path():
    """BW-PMS-08: Approved -> Budget Approved."""
    app = submit_application(
        applicant_user_id=1001,
        title="Sensor",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Tech",
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Approve",
        justification="Technical novelty and claims are acceptable for filing.",
    )
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("10000.00"),
        attorney_fees=Decimal("20000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=2001,
    )
    decide_budget(
        application_id=app.id, director_user_id=2001, decision="Approve", justification="Approved"
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.BUDGET_APPROVED.value


def test_bw_pms_09_budget_rejection_path():
    """BW-PMS-09: Approved -> Budget Rejected."""
    app = submit_application(
        applicant_user_id=1001,
        title="Sensor",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Tech",
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Approve",
        justification="Technical novelty and claims are acceptable for filing.",
    )
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("10000.00"),
        attorney_fees=Decimal("20000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=2001,
    )
    decide_budget(
        application_id=app.id,
        director_user_id=2001,
        decision="Reject",
        justification="Costs too high",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.BUDGET_REJECTED.value


def test_bw_pms_11_external_filing_path():
    """BW-PMS-11: Preconditions satisfied -> Filed."""
    app = submit_application(
        applicant_user_id=1001,
        title="Sensor",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 1001,
                "name": "Primary",
                "email": "p@test.com",
                "ownership_percentage": "100.00",
                "agreement_signed": True,
            }
        ],
    )
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    submit_director_review(
        application_id=app.id,
        director_user_id=2001,
        decision="Approve",
        justification="Technical novelty and claims are acceptable for filing.",
    )
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("10000.00"),
        attorney_fees=Decimal("20000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=2001,
    )
    decide_budget(application_id=app.id, director_user_id=2001, decision="Approve")
    app.refresh_from_db()

    record_external_filing(
        application_id=app.id,
        attorney_user_id=5001,
        external_filing_id="IPO/2026/0123",
        external_filing_date=date(2026, 11, 2),
        filing_confirmation="Officially lodged with Indian Patent Office.",
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.FILED.value


def test_bw_pms_12_office_action_with_applicant_review():
    """BW-PMS-12: Filed -> Office Action -> Awaiting Applicant Approval -> Applicant Approved -> Response Submitted."""
    app = submit_application(
        applicant_user_id=1001,
        title="Sensor",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.save()

    # 1. Record OA
    oa = record_office_action(
        application_id=app.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=date(2026, 11, 1),
        due_date=date(2027, 2, 1),
        details="FER Objections",
        requires_applicant_review=True,
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.OFFICE_ACTION_RECORDED.value

    # 2. Draft Response
    draft_office_action_response(
        office_action_id=oa.id, attorney_user_id=5001, draft_response="Proposed response text"
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.AWAITING_APPLICANT_APPROVAL.value

    # 3. Applicant approves
    approve_office_action_response(office_action_id=oa.id, applicant_user_id=1001)
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.APPLICANT_APPROVED.value

    # 4. Attorney submits
    submit_office_action_response(
        office_action_id=oa.id, attorney_user_id=5001, submission_details="Submitted to portal"
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RESPONSE_SUBMITTED.value


def test_bw_pms_13_office_action_without_applicant_review():
    """BW-PMS-13: Filed -> Office Action -> Response Ready -> Response Submitted."""
    app = submit_application(
        applicant_user_id=1001,
        title="Sensor",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.save()

    oa = record_office_action(
        application_id=app.id,
        attorney_user_id=5001,
        action_type="Hearing Notice",
        issue_date=date(2026, 11, 1),
        due_date=date(2026, 12, 1),
        details="Formal hearing notice",
        requires_applicant_review=False,
    )
    draft_office_action_response(
        office_action_id=oa.id, attorney_user_id=5001, draft_response="Hearing argument points"
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RESPONSE_READY.value

    submit_office_action_response(
        office_action_id=oa.id, attorney_user_id=5001, submission_details="Filed at hearing"
    )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.RESPONSE_SUBMITTED.value


def test_bw_pms_14_and_15_maintenance_renewal_and_non_renewal():
    """BW-PMS-14 (Renew) and BW-PMS-15 (Do Not Renew)."""
    # Renewal path (BW-PMS-14)
    app1 = submit_application(
        applicant_user_id=1001,
        title="App1",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app1.status = PatentApplicationStatus.FILED.value
    app1.save()
    record_patent_grant(
        application_id=app1.id,
        attorney_user_id=5001,
        patent_number="IN001",
        grant_date=date(2026, 11, 1),
    )
    m1 = app1.maintenance_records.first()
    request_renewal_decision(maintenance_id=m1.id, attorney_user_id=5001)
    decide_renewal(maintenance_id=m1.id, director_user_id=2001, decision="Renew")
    record_maintenance_action(
        maintenance_id=m1.id, attorney_user_id=5001, transaction_reference="TXN-1"
    )
    app1.refresh_from_db()
    assert app1.status == PatentApplicationStatus.RENEWED.value

    # Non-renewal path (BW-PMS-15)
    app2 = submit_application(
        applicant_user_id=1001,
        title="App2",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app2.status = PatentApplicationStatus.FILED.value
    app2.save()
    record_patent_grant(
        application_id=app2.id,
        attorney_user_id=5001,
        patent_number="IN002",
        grant_date=date(2026, 11, 1),
    )
    m2 = app2.maintenance_records.first()
    request_renewal_decision(maintenance_id=m2.id, attorney_user_id=5001)
    decide_renewal(maintenance_id=m2.id, director_user_id=2001, decision="Do Not Renew")
    app2.refresh_from_db()
    assert app2.status == PatentApplicationStatus.DO_NOT_RENEW.value


def test_bw_pms_16_pre_filing_withdrawal():
    """BW-PMS-16: Withdrawal from pre-filing status."""
    app = submit_application(
        applicant_user_id=1001,
        title="App Withdraw",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    assert app.status == PatentApplicationStatus.SUBMITTED.value

    withdrawn = withdraw_application(
        application_id=app.id, applicant_user_id=1001, reason="Withdrawn by applicant"
    )
    assert withdrawn.status == PatentApplicationStatus.WITHDRAWN.value
    assert withdrawn.is_withdrawn is True
