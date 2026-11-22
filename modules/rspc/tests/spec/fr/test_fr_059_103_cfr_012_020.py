"""Spec tests for strategy FR, module rspc: CFR-012 to CFR-020 (appointments, finance, procurement, reports, closure).

One test per design case in docs/09-rspc/spec-tests/FR_DESIGN.json. Each test names its
test_id and source_id. Cases the shipped RSPC interfaces cannot express are skipped with
reason "NOT_AUTOMATED: <reason>".
"""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import (
    Project,
    ProjectBudgetHead,
    ProjectClosureRequest,
    ProjectFundTransaction,
)
from modules.rspc.registry import ROLE_GRANTS
from modules.rspc.services import (
    extension as extension_services,
)
from modules.rspc.services import (
    finance as finance_services,
)
from modules.rspc.services import (
    project as project_services,
)
from modules.rspc.services import (
    proposal as proposal_services,
)

URL = "/api/v1/rspc"
TODAY = datetime.date.today()
F1, F2, HOD, DEAN = 101, 102, 50, 100


def _client_for(stub_iam, session):
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


def _as(stub_iam, user_id, role):
    """Client acting as `user_id` holding `role` (grants taken from the RSPC registry).

    The IAM stub serves one session at a time, so build the client right before use.
    """
    session = make_session(
        user_id=user_id,
        permissions=ROLE_GRANTS[role],
        modules=("rspc",),
        kind="faculty",
        roles=(role,),
        active_role=role,
    )
    return _client_for(stub_iam, session)


def _payload(**overrides):
    data = {
        "title": "Spec Proposal",
        "proposal_type": "sponsored_research",
        "department": "CSE",
        "funding_agency": "DST",
        "proposed_budget": "1000000.00",
        "summary": "Spec test proposal.",
    }
    data.update(overrides)
    return data


def _proposal(user_id, kind, title):
    return proposal_services.create_proposal(
        user_id=user_id,
        title=title,
        proposal_type=kind,
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("1000000.00"),
    )


def _submitted(user_id, kind, title):
    prop = _proposal(user_id, kind, title)
    return proposal_services.submit_proposal(proposal=prop, actor_user_id=user_id)


def _endorsed(user_id, kind, title, hod_id=HOD):
    prop = _submitted(user_id, kind, title)
    return proposal_services.endorse_proposal(proposal=prop, actor_user_id=hod_id)


def _project(user_id, code, status="active", kind="sponsored"):
    project = project_services.sanction_and_register_project(
        user_id=user_id,
        project_code=code,
        project_type=kind,
        title=f"Project {code}",
        department="CSE",
        funding_agency="DST",
        sanction_order_no=f"ORD/{code}",
        sanction_date=TODAY,
        start_date=TODAY,
        end_date=TODAY + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("3000000.00"),
    )
    if status != "sanctioned":
        Project.objects.filter(pk=project.pk).update(status=status)
        project.refresh_from_db()
    return project


def _head(project, head_type, amount):
    return finance_services.allocate_budget_head(
        project=project,
        head_type=head_type,
        allocated_amount=Decimal(amount),
        actor_user_id=1,
    )


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_059():
    """TC-FR-059 | source RSPC-FR-039 (parent RSPC-CFR-012) | Faculty can request a project-based staff appointment

    Action: Faculty submits an appointment request
    Expected: The request is created (CW-RSPC-03 T1) and retrievable
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_060():
    """TC-FR-060 | source RSPC-FR-040 | RSPC Admin can manage advertisement records

    Action: RSPC Admin creates and then updates a advertisement record
    Expected: The advertisement record is persisted and the update is reflected
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_061():
    """TC-FR-061 | source RSPC-FR-041 | RSPC Admin can manage application records

    Action: RSPC Admin creates and then updates a application record
    Expected: The application record is persisted and the update is reflected
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_062():
    """TC-FR-062 | source RSPC-FR-042 | RSPC Admin can manage stipend structure records

    Action: RSPC Admin creates and then updates a stipend structure record
    Expected: The stipend structure record is persisted and the update is reflected
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_063():
    """TC-FR-063 | source RSPC-FR-129 | RSPC Admin can manage staff-selection records

    Action: RSPC Admin creates and then updates a staff-selection record
    Expected: The staff-selection record is persisted and the update is reflected
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_064():
    """TC-FR-064 | source RSPC-FR-131 | RSPC Admin can manage stipend-workflow records

    Action: RSPC Admin creates and then updates a stipend-workflow record
    Expected: The stipend-workflow record is persisted and the update is reflected
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_065():
    """TC-FR-065 | source RSPC-FR-046 | RSPC maintains appointment duration records for staff appointments

    Action: Record appointment duration information for the appointment and retrieve it
    Expected: The appointment duration record is persisted and retrievable
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_066():
    """TC-FR-066 | source RSPC-FR-047 | RSPC maintains payment records for staff appointments

    Action: Record payment information for the appointment and retrieve it
    Expected: The payment record is persisted and retrievable
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_067():
    """TC-FR-067 | source RSPC-FR-048 | RSPC maintains compliance records for staff appointments

    Action: Record compliance information for the appointment and retrieve it
    Expected: The compliance record is persisted and retrievable
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_068():
    """TC-FR-068 | source RSPC-FR-043 (parent RSPC-CFR-013) | Faculty can record participation in selection

    Action: Faculty records participation in the selection process
    Expected: Participation is persisted
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_069():
    """TC-FR-069 | source RSPC-FR-044 | Faculty can submit staff selection recommendation

    Action: Faculty submits a recommendation
    Expected: Recommendation is persisted against the appointment
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_070():
    """TC-FR-070 | source RSPC-FR-045 (parent RSPC-CFR-014) | Staff appointment approvals routed via Dean-RSPC and Director as applicable (BR-RSPC-026)

    Action: Dean-RSPC approves and forwards, Director acts
    Expected: Approvals follow Dean-RSPC then Director and are recorded (CW-RSPC-03 T5-T9)
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_071():
    """TC-FR-071 | source RSPC-FR-045 Director not applicable | Director stage skipped where not applicable

    Action: Dean-RSPC approves
    Expected: No Director stage is created
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_072(stub_iam):
    """TC-FR-072 | source RSPC-FR-049 (parent RSPC-CFR-015) | Faculty can submit fund utilization request

    Action: Submit fund utilization request
    Expected: Request created (CW-RSPC-04 T1)
    """

    project = _project(F1, "RSPC/FR/072", status="active")
    _head(project, "consumables", "200000.00")
    client = _as(stub_iam, F1, "faculty")
    resp = client.post(
        f"{URL}/projects/{project.id}/disburse/",
        data={"head_type": "consumables", "amount": "25000.00",
              "reference_no": "FUR-FR-072", "description": "Fund utilization request"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["transaction_type"] == "disbursement"
    assert ProjectFundTransaction.objects.filter(
        project=project, reference_no="FUR-FR-072", amount=Decimal("25000.00")
    ).exists()


@pytest.mark.django_db
def test_tc_fr_073(stub_iam):
    """TC-FR-073 | source RSPC-FR-050 | Faculty can submit expenditure request

    Action: Submit expenditure request
    Expected: Request created (CW-RSPC-04 T1)
    """

    project = _project(F1, "RSPC/FR/073", status="active")
    _head(project, "travel", "80000.00")
    client = _as(stub_iam, F1, "faculty")
    resp = client.post(
        f"{URL}/projects/{project.id}/disburse/",
        data={"head_type": "travel", "amount": "15000.00",
              "reference_no": "EXP-FR-073", "description": "Expenditure request"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["head_type"] == "travel"
    assert ProjectFundTransaction.objects.filter(
        project=project, reference_no="EXP-FR-073", amount=Decimal("15000.00")
    ).exists()


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no financial-request verification/escalation workflow; the disbursement-approve endpoint is a stub that records nothing')
def test_tc_fr_074():
    """TC-FR-074 | source RSPC-FR-051 | RSPC Admin performs initial financial verification of fund requests

    Action: Verify the request
    Expected: Verification outcome recorded and request progresses (CW-RSPC-04 T2-T3)
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no financial-request verification/escalation workflow; the disbursement-approve endpoint is a stub that records nothing')
def test_tc_fr_075():
    """TC-FR-075 | source RSPC-FR-052 | RSPC Admin performs initial financial verification of expenditure requests

    Action: Verify the request
    Expected: Verification outcome recorded and request progresses
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no financial-request verification/escalation workflow; the disbursement-approve endpoint is a stub that records nothing')
def test_tc_fr_076():
    """TC-FR-076 | source RSPC-FR-053 (parent RSPC-CFR-016) | Dean-RSPC approves financial requests within delegated powers (BR-RSPC-032)

    Action: Dean-RSPC approves
    Expected: Approval recorded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no financial-request verification/escalation workflow; the disbursement-approve endpoint is a stub that records nothing')
def test_tc_fr_077():
    """TC-FR-077 | source RSPC-FR-053 beyond delegated powers | Dean-RSPC cannot approve beyond delegated powers

    Action: Dean-RSPC attempts approval
    Expected: Approval is not granted at Dean-RSPC stage
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no financial-request verification/escalation workflow; the disbursement-approve endpoint is a stub that records nothing')
def test_tc_fr_078():
    """TC-FR-078 | source RSPC-FR-054 | High-value financial requests escalated to Director (BR-RSPC-033)

    Action: Dean-RSPC stage processes the request
    Expected: Request is escalated to the Director and escalation recorded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no financial-request verification/escalation workflow; the disbursement-approve endpoint is a stub that records nothing')
def test_tc_fr_079():
    """TC-FR-079 | source RSPC-FR-054 not high-value | Non-high-value request not escalated

    Action: Dean-RSPC approves
    Expected: No escalation to Director occurs
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no financial-request verification/escalation workflow; the disbursement-approve endpoint is a stub that records nothing; no audit log exists')
def test_tc_fr_080():
    """TC-FR-080 | source RSPC-FR-055 | Financial request lifecycle logged (BR-RSPC-034)

    Action: Retrieve the audit log of the request
    Expected: Request, verification, approval, escalation and transaction-record entries are all present
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_081(stub_iam):
    """TC-FR-081 | source RSPC-FR-056 (parent RSPC-CFR-017) | Faculty can request equipment procurement

    Action: Submit an equipment procurement request
    Expected: Request created (CW-RSPC-05 T1)
    """

    project = _project(F1, "RSPC/FR/081", status="active")
    _head(project, "equipment", "1000000.00")
    client = _as(stub_iam, F1, "faculty")
    resp = client.post(
        f"{URL}/projects/{project.id}/disburse/",
        data={"head_type": "equipment", "amount": "250000.00",
              "reference_no": "PRC-EQ-081", "description": "Equipment procurement"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["head_type"] == "equipment"
    assert ProjectFundTransaction.objects.filter(reference_no="PRC-EQ-081").count() == 1


@pytest.mark.django_db
def test_tc_fr_082(stub_iam):
    """TC-FR-082 | source RSPC-FR-057 | Faculty can request consumables procurement

    Action: Submit a consumables procurement request
    Expected: Request created
    """

    project = _project(F1, "RSPC/FR/082", status="active")
    _head(project, "consumables", "400000.00")
    client = _as(stub_iam, F1, "faculty")
    resp = client.post(
        f"{URL}/projects/{project.id}/disburse/",
        data={"head_type": "consumables", "amount": "60000.00",
              "reference_no": "PRC-CO-082", "description": "Consumables procurement"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["head_type"] == "consumables"
    assert ProjectFundTransaction.objects.filter(reference_no="PRC-CO-082").count() == 1


@pytest.mark.django_db
def test_tc_fr_083(stub_iam):
    """TC-FR-083 | source RSPC-FR-058 within budget | Procurement validated against sanctioned budget (BR-RSPC-035)

    Action: Submit a request within sanctioned budget
    Expected: Request passes validation and advances
    """

    project = _project(F1, "RSPC/FR/083", status="active")
    _head(project, "equipment", "100000.00")
    client = _as(stub_iam, F1, "faculty")
    resp = client.post(
        f"{URL}/projects/{project.id}/disburse/",
        data={"head_type": "equipment", "amount": "40000.00", "reference_no": "PRC-083"},
        format="json",
    )
    assert resp.status_code == 201
    head = ProjectBudgetHead.objects.get(project=project, head_type="equipment")
    assert head.spent_amount == Decimal("40000.00")
    assert head.available_balance == Decimal("60000.00")


@pytest.mark.django_db
def test_tc_fr_084(stub_iam):
    """TC-FR-084 | source RSPC-FR-058 exceeds budget | Procurement exceeding sanctioned budget is rejected

    Action: Submit a request exceeding sanctioned budget
    Expected: Request fails validation and does not advance
    """

    project = _project(F1, "RSPC/FR/084", status="active")
    _head(project, "equipment", "100000.00")
    client = _as(stub_iam, F1, "faculty")
    resp = client.post(
        f"{URL}/projects/{project.id}/disburse/",
        data={"head_type": "equipment", "amount": "100000.01", "reference_no": "PRC-084"},
        format="json",
    )
    # Balance-dependent refusal: state conflict (api-conventions "409 vs 422").
    assert resp.status_code == 409
    head = ProjectBudgetHead.objects.get(project=project, head_type="equipment")
    assert head.spent_amount == Decimal("0.00")
    assert not ProjectFundTransaction.objects.filter(transaction_type="disbursement").exists()


@pytest.mark.django_db
def test_tc_fr_085(stub_iam):
    """TC-FR-085 | source RSPC-FR-058 equals budget | Procurement equal to sanctioned budget boundary

    Action: Submit a request equal to the remaining sanctioned budget
    Expected: Request is validated as within budget (no unspecified rejection)
    """

    project = _project(F1, "RSPC/FR/085", status="active")
    _head(project, "equipment", "100000.00")
    finance_services.disburse_funds(
        project=project, head_type="equipment", amount=Decimal("40000.00"),
        reference_no="PRC-085-A", description="", actor_user_id=F1,
    )
    client = _as(stub_iam, F1, "faculty")
    resp = client.post(
        f"{URL}/projects/{project.id}/disburse/",
        data={"head_type": "equipment", "amount": "60000.00", "reference_no": "PRC-085-B"},
        format="json",
    )
    assert resp.status_code == 201
    head = ProjectBudgetHead.objects.get(project=project, head_type="equipment")
    assert head.spent_amount == Decimal("100000.00")
    assert head.available_balance == Decimal("0.00")


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no procurement-request workflow, status or approval hierarchy (no model, service or endpoint)')
def test_tc_fr_086():
    """TC-FR-086 | source RSPC-FR-059 | Procurement approval hierarchy enforced (BR-RSPC-036)

    Action: Approvers act in the represented order
    Expected: Request advances only along the hierarchy
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no procurement-request workflow, status or approval hierarchy (no model, service or endpoint)')
def test_tc_fr_087():
    """TC-FR-087 | source RSPC-FR-059 bypass | Procurement hierarchy cannot be bypassed

    Action: Actor at a later stage attempts approval
    Expected: Action rejected
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no procurement-request workflow, status or approval hierarchy (no model, service or endpoint)')
def test_tc_fr_088():
    """TC-FR-088 | source RSPC-FR-060 | Faculty can track procurement request status

    Action: Open the request status
    Expected: Current status displayed and updates after each stage
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no progress/utilization report submission, schedule or history interface (only a summary count report exists)')
def test_tc_fr_089():
    """TC-FR-089 | source RSPC-FR-061 (parent RSPC-CFR-018) | Faculty can submit periodic progress report

    Action: Submit progress report
    Expected: Report stored
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no progress/utilization report submission, schedule or history interface (only a summary count report exists)')
def test_tc_fr_090():
    """TC-FR-090 | source RSPC-FR-062 | Faculty can submit periodic utilization report

    Action: Submit utilization report
    Expected: Report stored
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no progress/utilization report submission, schedule or history interface (only a summary count report exists)')
def test_tc_fr_091():
    """TC-FR-091 | source RSPC-FR-063 in schedule | Reporting schedule enforced (BR-RSPC-037)

    Action: Submit a report within the scheduled period
    Expected: Accepted
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no progress/utilization report submission, schedule or history interface (only a summary count report exists)')
def test_tc_fr_092():
    """TC-FR-092 | source RSPC-FR-063 outside schedule | Report outside represented schedule not accepted as scheduled

    Action: Submit a report outside the represented schedule
    Expected: Submission is handled per the schedule rule (rejected or flagged) and not accepted as on schedule
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no progress/utilization report submission, schedule or history interface (only a summary count report exists)')
def test_tc_fr_093():
    """TC-FR-093 | source RSPC-FR-066 (parent RSPC-CFR-019) | Authorized stakeholders access historical progress reports (BR-RSPC-038)

    Action: Authorized stakeholder opens history
    Expected: Historical progress reports listed
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no progress/utilization report submission, schedule or history interface (only a summary count report exists)')
def test_tc_fr_094():
    """TC-FR-094 | source RSPC-FR-067 | Authorized stakeholders access historical utilization reports (BR-RSPC-039)

    Action: Authorized stakeholder opens history
    Expected: Historical utilization reports listed
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no progress/utilization report submission, schedule or history interface (only a summary count report exists)')
def test_tc_fr_095():
    """TC-FR-095 | source RSPC-CFR-019 unauthorized | Unauthorized users cannot access historical reports

    Action: User without authorization requests reports
    Expected: Access denied
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_096(stub_iam):
    """TC-FR-096 | source RSPC-FR-068 (parent RSPC-CFR-020) | Faculty can submit closure report

    Action: Submit closure report
    Expected: Stored (CW-RSPC-06 T1)
    """

    project = _project(F1, "RSPC/FR/096", status="active")
    client = _as(stub_iam, F1, "faculty")
    resp = client.post(
        f"{URL}/projects/{project.id}/closure/",
        data={"remarks": "Closure report: all objectives met."},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["status"] == "pending"
    closure = ProjectClosureRequest.objects.get(project=project)
    assert closure.remarks == "Closure report: all objectives met."
    project.refresh_from_db()
    assert project.status == "closure_pending"


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no interface to submit a completion report (the closure record has a completion_report_submitted flag that no endpoint sets)')
def test_tc_fr_097():
    """TC-FR-097 | source RSPC-FR-069 | Faculty can submit completion report

    Action: Submit completion report
    Expected: Stored
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no settlement-record verification step in the closure workflow')
def test_tc_fr_098():
    """TC-FR-098 | source RSPC-FR-070 | Financial settlement verified during closure

    Action: Verify settlement records
    Expected: Verification outcome recorded (CW-RSPC-06 T2-T3)
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no asset-declaration record or verification step in the closure workflow')
def test_tc_fr_099():
    """TC-FR-099 | source RSPC-FR-071 | Asset declarations verified during closure

    Action: Verify asset declaration records
    Expected: Verification outcome recorded
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_100(stub_iam):
    """TC-FR-100 | source RSPC-FR-072 | Closure approvals recorded

    Action: Dean-RSPC approves closure
    Expected: Approval recorded with decision
    """

    project = _project(F1, "RSPC/FR/100", status="active")
    extension_services.request_project_closure(project=project, actor_user_id=F1)
    client = _as(stub_iam, DEAN, "Dean (RSPC)")
    resp = client.post(f"{URL}/projects/{project.id}/closure/approve/")
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"
    closure = ProjectClosureRequest.objects.get(project=project)
    assert closure.status == "approved"
    assert closure.closed_by_user_id == DEAN
    assert closure.closed_at is not None


@pytest.mark.skip(reason="NOT_AUTOMATED: RSPC closure ends at status 'closed' with no archive state and no project audit trail to retrieve")
def test_tc_fr_101():
    """TC-FR-101 | source RSPC-FR-073 | Closed projects archived with complete audit trails (BR-RSPC-043)

    Action: Closure completes
    Expected: Project archived and its complete audit trail is retrievable
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no reviewer-remarks interface for closure (remarks are only supplied by the requester at submission)')
def test_tc_fr_102():
    """TC-FR-102 | source RSPC-FR-130 | Closure-related remarks recorded

    Action: Reviewer enters remarks
    Expected: Remarks persisted
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC closure has no Verified or Archived step (pending, approved, rejected only)')
def test_tc_fr_103():
    """TC-FR-103 | source RSPC-CFR-020 full path | Closure path from submission to archival

    Action: Verify, approve and archive in order
    Expected: Project goes Submitted, Verified, Approved, Archived with each step recorded
    """
    raise NotImplementedError
