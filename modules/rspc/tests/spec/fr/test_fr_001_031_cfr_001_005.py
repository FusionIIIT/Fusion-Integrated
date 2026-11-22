"""Spec tests for strategy FR, module rspc: CFR-001 to CFR-005 (views, audit, HoD, Dean, Director).

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


@pytest.mark.django_db
def test_tc_fr_001(stub_iam):
    """TC-FR-001 | source RSPC-FR-004 (parent RSPC-CFR-001) | Faculty can view ongoing and completed project portfolio

    Action: F1 opens the own-projects list
    Expected: both the ongoing and the completed project of F1 are listed and F2's project is not listed
    """

    ongoing = _project(F1, "RSPC/FR/001-A", status="active")
    done = _project(F1, "RSPC/FR/001-B", status="closed")
    other = _project(F2, "RSPC/FR/001-C", status="active")
    client = _as(stub_iam, F1, "faculty")
    resp = client.get(f"{URL}/projects/")
    assert resp.status_code == 200
    ids = {row["id"] for row in resp.data}
    assert ids == {ongoing.id, done.id}
    assert other.id not in ids


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no project history or project approval-history view (only proposal reviews and the fund ledger exist)')
def test_tc_fr_002():
    """TC-FR-002 | source RSPC-FR-005 | Faculty can view approval history of own project

    Action: F1 opens the approval history of an own project
    Expected: the approval decisions recorded for that project are displayed
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_003(stub_iam):
    """TC-FR-003 | source RSPC-FR-006 | Faculty can view financial transaction records of own project

    Action: F1 opens the financial transaction records of an own project
    Expected: the financial transaction records recorded for that project are displayed
    """

    project = _project(F1, "RSPC/FR/003", status="active")
    _head(project, "consumables", "500000.00")
    finance_services.disburse_funds(
        project=project, head_type="consumables", amount=Decimal("120000.00"),
        reference_no="INV-FR-003", description="Lab material", actor_user_id=F1,
    )
    client = _as(stub_iam, F1, "faculty")
    resp = client.get(f"{URL}/projects/{project.id}/ledger/")
    assert resp.status_code == 200
    rows = {(r["transaction_type"], r["amount"]) for r in resp.data}
    assert rows == {("allocation", "500000.00"), ("disbursement", "120000.00")}


@pytest.mark.django_db
def test_tc_fr_004(stub_iam):
    """TC-FR-004 | source RSPC-FR-107 | Faculty can view current status of own project

    Action: F1 opens the status view of an own project
    Expected: the current status of the project is displayed and matches the stored status
    """

    ongoing = _project(F1, "RSPC/FR/004-A", status="active")
    done = _project(F1, "RSPC/FR/004-B", status="closed")
    client = _as(stub_iam, F1, "faculty")
    for project in (ongoing, done):
        resp = client.get(f"{URL}/projects/{project.id}/")
        assert resp.status_code == 200
        stored = Project.objects.get(pk=project.id).status
        assert resp.data["status"] == stored == project.status


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no project history or project approval-history view (only proposal reviews and the fund ledger exist)')
def test_tc_fr_005():
    """TC-FR-005 | source RSPC-FR-108 | Faculty can view history of own project

    Action: F1 opens the history view of an own project
    Expected: the recorded history of the project is displayed
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no audit-trail/audit-log record or retrieval interface (no model, service or endpoint)')
def test_tc_fr_006():
    """TC-FR-006 | source RSPC-FR-109 | Faculty can view audit trail of own project

    Action: F1 opens the audit trail of an own project
    Expected: the audit-trail entries recorded for that project are displayed
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_007(stub_iam):
    """TC-FR-007 | source RSPC-CFR-001 unauthorized scope not exposed | Faculty cannot view another Faculty member's project information

    Action: F1 requests the project list, status, history, approval history, audit trail and financial records of F2's project
    Expected: F2's project data is not returned to F1 for any of the views (access denied or empty result)
    """

    other = _project(F2, "RSPC/FR/007", status="active")
    _head(other, "consumables", "100000.00")
    client = _as(stub_iam, F1, "faculty")
    lst = client.get(f"{URL}/projects/")
    assert lst.status_code == 200
    assert other.id not in {row["id"] for row in lst.data}
    # Status/detail, budget heads and the financial ledger of F2's project:
    # out-of-scope data is hidden behind 404 (api-conventions "403 vs 404").
    for suffix in ("", "heads/", "ledger/"):
        resp = client.get(f"{URL}/projects/{other.id}/{suffix}")
        assert resp.status_code == 404, suffix


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no audit-trail/audit-log record or retrieval interface (no model, service or endpoint)')
def test_tc_fr_008():
    """TC-FR-008 | source RSPC-FR-007 (parent RSPC-CFR-002) | RSPC Admin can maintain structured audit/compliance records

    Action: RSPC Admin creates or updates a structured audit/compliance record for that RSPC record
    Expected: The record is persisted with its content and is retrievable afterwards
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no audit-trail/audit-log record or retrieval interface (no model, service or endpoint)')
def test_tc_fr_009():
    """TC-FR-009 | source RSPC-FR-088 | RSPC maintains logs for audit, transparency and regulatory compliance

    Action: Perform the event, then an authorized user retrieves the RSPC logs
    Expected: A log entry for the event is persisted and retrievable by the authorized user; BR-RSPC-050 log content is present
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no audit-trail/audit-log record or retrieval interface (no model, service or endpoint)')
def test_tc_fr_010():
    """TC-FR-010 | source RSPC-CFR-002 roll-up | Audit logs are retrievable by authorized users and not by unauthorized roles

    Action: Both users request the audit logs
    Expected: Authorized user receives the entries; the unauthorized user is denied
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_011(stub_iam):
    """TC-FR-011 | source RSPC-FR-008 (parent RSPC-CFR-003) | HoD can review assigned project and consultancy requests

    Action: HoD opens each assigned request
    Expected: Both the research proposal and the consultancy request details are displayed to the HoD
    """

    research = _submitted(F1, "sponsored_research", "Research proposal")
    consult = _submitted(F1, "consultancy", "Consultancy request")
    client = _as(stub_iam, HOD, "Head of Department")
    for prop, kind in ((research, "sponsored_research"), (consult, "consultancy")):
        resp = client.get(f"{URL}/proposals/{prop.id}/")
        assert resp.status_code == 200
        assert resp.data["proposal_type"] == kind
        assert resp.data["title"] == prop.title
        assert resp.data["status"] == "submitted_hod"


@pytest.mark.django_db
def test_tc_fr_012(stub_iam):
    """TC-FR-012 | source RSPC-FR-009 | HoD can record a departmental recommendation (BR-RSPC-067)

    Action: HoD records a recommendation on the proposal and on the consultancy request
    Expected: Each recommendation is persisted against its request and is retrievable
    """

    research = _submitted(F1, "sponsored_research", "Research proposal")
    consult = _submitted(F1, "consultancy", "Consultancy request")
    client = _as(stub_iam, HOD, "Head of Department")
    for prop, note in ((research, "Rec research"), (consult, "Rec consultancy")):
        resp = client.post(
            f"{URL}/proposals/{prop.id}/endorse/", data={"comments": note}, format="json"
        )
        assert resp.status_code == 200
    for prop, note in ((research, "Rec research"), (consult, "Rec consultancy")):
        detail = client.get(f"{URL}/proposals/{prop.id}/")
        assert detail.status_code == 200
        assert len(detail.data["reviews"]) == 1
        review = detail.data["reviews"][0]
        assert review["comments"] == note
        assert review["reviewer_user_id"] == HOD


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no feasibility-evaluation record or interface (no model, service or endpoint)')
def test_tc_fr_013():
    """TC-FR-013 | source RSPC-FR-118 | HoD can evaluate departmental feasibility

    Action: HoD records a feasibility evaluation for an assigned request
    Expected: The feasibility evaluation is persisted against the request
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no alignment-evaluation record or interface (no model, service or endpoint)')
def test_tc_fr_014():
    """TC-FR-014 | source RSPC-FR-119 | HoD can evaluate departmental alignment

    Action: HoD records an alignment evaluation for an assigned request
    Expected: The alignment evaluation is persisted against the request
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_015(stub_iam):
    """TC-FR-015 | source RSPC-CFR-003 progression according to recommendation | Request progresses according to HoD recommendation (CW-RSPC-01 T2-T3, CW-RSPC-02 T2-T3)

    Action: HoD records a positive recommendation on the proposal and on the consultancy request
    Expected: Each request progresses to the next stage of its workflow and the state change is recorded
    """

    research = _submitted(F1, "sponsored_research", "Research proposal")
    consult = _submitted(F1, "consultancy", "Consultancy request")
    client = _as(stub_iam, HOD, "Head of Department")
    for prop in (research, consult):
        resp = client.post(f"{URL}/proposals/{prop.id}/endorse/", data={}, format="json")
        assert resp.status_code == 200
        assert resp.data["status"] == "endorsed_hod"
        prop.refresh_from_db()
        assert prop.status == "endorsed_hod"
        review = prop.reviews.get()
        assert (review.action, review.reviewer_user_id) == ("endorse", HOD)


@pytest.mark.django_db
def test_tc_fr_016(stub_iam):
    """TC-FR-016 | source RSPC-FR-010 (parent RSPC-CFR-004) | Dean-RSPC can review routed research and consultancy matters

    Action: Dean-RSPC opens each routed matter
    Expected: Both matters are displayed for review
    """

    research = _endorsed(F1, "sponsored_research", "Research proposal")
    consult = _endorsed(F1, "consultancy", "Consultancy request")
    client = _as(stub_iam, DEAN, "Dean (RSPC)")
    for prop, kind in ((research, "sponsored_research"), (consult, "consultancy")):
        resp = client.get(f"{URL}/proposals/{prop.id}/")
        assert resp.status_code == 200
        assert resp.data["proposal_type"] == kind
        assert resp.data["status"] == "endorsed_hod"


@pytest.mark.django_db
def test_tc_fr_017(stub_iam):
    """TC-FR-017 | source RSPC-FR-011 | Dean-RSPC can approve project proposals (BR-RSPC-068)

    Action: Dean-RSPC approves the proposal
    Expected: The approval is recorded and the proposal state is updated per CW-RSPC-01
    """

    prop = _endorsed(F1, "sponsored_research", "Research proposal")
    client = _as(stub_iam, DEAN, "Dean (RSPC)")
    resp = client.post(
        f"{URL}/proposals/{prop.id}/approve/", data={"comments": "Sanctioned"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "approved_dean"
    prop.refresh_from_db()
    assert prop.status == "approved_dean"
    review = prop.reviews.get(action="approve")
    assert review.reviewer_user_id == DEAN
    assert review.comments == "Sanctioned"


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no Director stage in any workflow (proposal states stop at Dean approval; Director holds only view/closure grants); no Dean forward-to-Director action exists')
def test_tc_fr_018():
    """TC-FR-018 | source RSPC-FR-012 | Dean-RSPC can forward high-value or strategic requests to Director (BR-RSPC-004)

    Action: Dean-RSPC forwards the request to the Director
    Expected: The request is routed to the Director stage and the forwarding is recorded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no staff-appointment request/records interface (no model, service or endpoint)')
def test_tc_fr_019():
    """TC-FR-019 | source RSPC-FR-120 | Dean-RSPC can review routed staff-appointment requests

    Action: Dean-RSPC opens the routed item
    Expected: The item is displayed for review
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no budget-allocation request routed to a Dean stage (budget heads are allocated directly by project managers)')
def test_tc_fr_020():
    """TC-FR-020 | source RSPC-FR-121 | Dean-RSPC can review routed budget allocations

    Action: Dean-RSPC opens the routed item
    Expected: The item is displayed for review
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no financial-request verification/escalation workflow; the disbursement-approve endpoint is a stub that records nothing')
def test_tc_fr_021():
    """TC-FR-021 | source RSPC-FR-122 | Dean-RSPC can review routed financial requests

    Action: Dean-RSPC opens the routed item
    Expected: The item is displayed for review
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no procurement-request workflow, status or approval hierarchy (no model, service or endpoint)')
def test_tc_fr_022():
    """TC-FR-022 | source RSPC-FR-123 | Dean-RSPC can review routed procurement requests

    Action: Dean-RSPC opens the routed item
    Expected: The item is displayed for review
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_023(stub_iam):
    """TC-FR-023 | source RSPC-FR-124 | Dean-RSPC can review routed project-closure records

    Action: Dean-RSPC opens the routed item
    Expected: The item is displayed for review
    """

    project = _project(F1, "RSPC/FR/023", status="active")
    extension_services.request_project_closure(
        project=project, actor_user_id=F1, remarks="Work completed"
    )
    client = _as(stub_iam, DEAN, "Dean (RSPC)")
    resp = client.get(f"{URL}/projects/{project.id}/")
    assert resp.status_code == 200
    assert resp.data["status"] == "closure_pending"


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no policy-compliance view for routed requests (no model, service or endpoint)')
def test_tc_fr_024():
    """TC-FR-024 | source RSPC-FR-125 | Dean-RSPC can review policy compliance (BR-RSPC-070)

    Action: Dean-RSPC opens the compliance view of the request
    Expected: The represented policy compliance information is displayed for the request
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC defines no Dean-RSPC value limit and no limit-based approval rule; the limit value is left open by the specification')
def test_tc_fr_025():
    """TC-FR-025 | source RSPC-FR-126 within limits | Dean-RSPC can approve eligible requests within delegated or defined limits (BR-RSPC-068)

    Action: Dean-RSPC approves the request
    Expected: Approval is accepted and recorded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC defines no Dean-RSPC value limit and no limit-based approval rule; the limit value is left open by the specification')
def test_tc_fr_026():
    """TC-FR-026 | source RSPC-FR-126 beyond limits | Dean-RSPC cannot approve requests beyond delegated or defined limits

    Action: Dean-RSPC attempts to approve the request
    Expected: Approval is rejected and the request is not finally approved at the Dean-RSPC stage
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no Director stage in any workflow (proposal states stop at Dean approval; Director holds only view/closure grants)')
def test_tc_fr_027():
    """TC-FR-027 | source RSPC-FR-013 (parent RSPC-CFR-005) | Director can approve large funding requests (BR-RSPC-005)

    Action: Director approves the request
    Expected: The approval is recorded and the request state is updated
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no Director stage in any workflow (proposal states stop at Dean approval; Director holds only view/closure grants)')
def test_tc_fr_028():
    """TC-FR-028 | source RSPC-FR-014 | Director can authorize high-value expenditures (BR-RSPC-006)

    Action: Director authorizes the expenditure
    Expected: The authorization is recorded against the request
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no Director stage in any workflow (proposal states stop at Dean approval; Director holds only view/closure grants)')
def test_tc_fr_029():
    """TC-FR-029 | source RSPC-FR-127 | Director can review significant, high-value, strategic or escalated requests (BR-RSPC-069)

    Action: Director opens the request
    Expected: The request is displayed for review
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no Director stage in any workflow (proposal states stop at Dean approval; Director holds only view/closure grants); no regulation-adherence view exists')
def test_tc_fr_030():
    """TC-FR-030 | source RSPC-FR-128 | Director can review adherence to institutional and external funding regulations (BR-RSPC-070)

    Action: Director opens the regulation adherence view
    Expected: The represented regulation adherence information is displayed
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no Director stage in any workflow (proposal states stop at Dean approval; Director holds only view/closure grants)')
def test_tc_fr_031():
    """TC-FR-031 | source RSPC-CFR-005 authorization recorded | Director-stage authorization decision is recorded with the request

    Action: Director records authorization
    Expected: Authorization outcome is persisted with the Director's identity and the request state is updated
    """
    raise NotImplementedError
