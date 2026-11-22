"""Spec tests for RSPC use cases 1-31 (strategy UC)."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import (
    Project,
    ProjectBudgetHead,
    ProjectFundTransaction,
    Proposal,
    ProposalReview,
)
from modules.rspc.registry import ROLE_GRANTS
from modules.rspc.services import finance as finance_services
from modules.rspc.services import proposal as proposal_services

FAC = "faculty"
HOD = "Head of Department"
DEAN = "Dean (RSPC)"
DIRECTOR = "Director"
ADMIN = "admin"
TODAY = datetime.date.today()


def _client(stub_iam, user_id, perms, roles=None):
    if isinstance(perms, str):
        roles, perms = (perms,), ROLE_GRANTS[perms]
    session = make_session(
        user_id=user_id, roles=roles or ("faculty",), permissions=tuple(perms),
        modules=("rspc",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


def _project(user_id, code, status="active", project_type="sponsored", title="Project"):
    return Project.objects.create(
        user_id=user_id, project_code=code, project_type=project_type, title=title,
        department="CSE", funding_agency="SERB", sanction_order_no="SO/1",
        sanction_date=TODAY, start_date=TODAY,
        end_date=TODAY + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("1000000.00"), status=status,
    )


def _proposal(user_id, status="draft", funding_agency="SERB", proposal_type="sponsored_research"):
    return Proposal.objects.create(
        user_id=user_id, title="Proposal", proposal_type=proposal_type, department="CSE",
        funding_agency=funding_agency, proposed_budget=Decimal("500000.00"), status=status,
    )


def _alloc(project):
    return finance_services.allocate_budget_head(
        project=project, head_type="consumables", allocated_amount=Decimal("1000.00"),
        actor_user_id=1,
    )


def _snapshot():
    return (
        list(Project.objects.order_by("id").values_list("id", "status", "end_date")),
        list(ProjectBudgetHead.objects.order_by("id").values_list(
            "id", "allocated_amount", "spent_amount", "committed_amount")),
        list(ProjectFundTransaction.objects.order_by("id").values_list(
            "id", "transaction_type", "amount")),
    )


@pytest.mark.django_db
def test_tc_uc_001(stub_iam):
    """TC-UC-001 / RSPC-UC-001 Main Success Scenario."""
    p1 = _project(10, "P-A", status="active")
    _project(10, "P-B", status="closed")
    _project(11, "P-C", status="active")
    _alloc(p1)
    client = _client(stub_iam, 10, FAC)
    before = _snapshot()
    resp = client.get("/api/v1/rspc/projects/")
    assert resp.status_code == 200
    assert {r["project_code"]: r["status"] for r in resp.data} == {
        "P-A": "active", "P-B": "closed"}
    detail = client.get(f"/api/v1/rspc/projects/{p1.id}/")
    assert detail.status_code == 200
    assert detail.data["status"] == "active"
    ledger = client.get(f"/api/v1/rspc/projects/{p1.id}/ledger/")
    assert ledger.status_code == 200
    assert [t["transaction_type"] for t in ledger.data] == ["allocation"]
    assert _snapshot() == before


@pytest.mark.django_db
def test_tc_uc_002(stub_iam):
    """TC-UC-002 / RSPC-UC-001 Alternative Flow A1."""
    p1 = _project(10, "P-A", status="active")
    p2 = _project(10, "P-B", status="closed")
    p3 = _project(11, "P-C", status="active")
    client = _client(stub_iam, 10, FAC)
    first = client.get(f"/api/v1/rspc/projects/{p1.id}/")
    assert first.status_code == 200 and first.data["project_code"] == "P-A"
    second = client.get(f"/api/v1/rspc/projects/{p2.id}/")
    assert second.status_code == 200 and second.data["project_code"] == "P-B"
    filtered = client.get("/api/v1/rspc/projects/?status=closed")
    assert [r["project_code"] for r in filtered.data] == ["P-B"]
    everything = client.get("/api/v1/rspc/projects/")
    assert p3.project_code not in {r["project_code"] for r in everything.data}
    assert client.get(f"/api/v1/rspc/projects/{p3.id}/").status_code == 404


@pytest.mark.django_db
def test_tc_uc_003(stub_iam):
    """TC-UC-003 / RSPC-UC-001 Exception Flow E1."""
    other = _project(11, "P-SECRET", status="active", title="Secret Title")
    client = _client(stub_iam, 10, FAC)
    before = _snapshot()
    resp = client.get(f"/api/v1/rspc/projects/{other.id}/")
    assert resp.status_code == 404
    body = resp.content.decode()
    assert "Secret Title" not in body and "P-SECRET" not in body
    assert _snapshot() == before


@pytest.mark.django_db
def test_tc_uc_004(stub_iam):
    """TC-UC-004 / RSPC-UC-001 Exception Flow E2."""
    project = _project(10, "P-A", status="active")
    client = _client(stub_iam, 10, FAC)
    before = _snapshot()
    empty = client.get(f"/api/v1/rspc/projects/{project.id}/ledger/")
    assert empty.status_code == 200
    assert list(empty.data) == []
    missing = client.get("/api/v1/rspc/projects/999999/ledger/")
    assert missing.status_code == 404
    assert _snapshot() == before


@pytest.mark.django_db
def test_tc_uc_005(stub_iam):
    """TC-UC-005 / RSPC-UC-002 Main Success Scenario."""
    client = _client(stub_iam, 10, FAC)
    payload = {
        "title": "Quantum Testbed", "proposal_type": "sponsored_research",
        "department": "CSE", "funding_agency": "SERB",
        "proposed_budget": "2500000.00", "summary": "Objectives and timeline.",
        "submission_deadline": "2027-03-31",
    }
    created = client.post("/api/v1/rspc/proposals/", data=payload, format="json")
    assert created.status_code == 201
    pid = created.data["id"]
    submitted = client.post(f"/api/v1/rspc/proposals/{pid}/submit/")
    assert submitted.status_code == 200
    assert submitted.data["status"] == "submitted_hod"
    assert Proposal.objects.get(pk=pid).status == "submitted_hod"
    hod = _client(stub_iam, 50, HOD)
    listed = hod.get("/api/v1/rspc/proposals/")
    assert pid in [r["id"] for r in listed.data]






@pytest.mark.django_db
def test_tc_uc_008(stub_iam):
    """TC-UC-008 / RSPC-UC-002 Exception Flow E1 mandatory field missing."""
    proposal = _proposal(10, status="draft", funding_agency="")
    client = _client(stub_iam, 10, FAC)
    resp = client.post(f"/api/v1/rspc/proposals/{proposal.id}/submit/")
    assert resp.status_code in (400, 422)
    assert "funding_agency" in resp.content.decode()
    proposal.refresh_from_db()
    assert proposal.status == "draft"
    assert proposal.title == "Proposal"




@pytest.mark.django_db
def test_tc_uc_010(stub_iam):
    """TC-UC-010 / RSPC-UC-002 Exception Flow E2."""
    client = _client(stub_iam, 12, ("rspc.proposal.view",), roles=("student",))
    resp = client.post(
        "/api/v1/rspc/proposals/",
        data={"title": "T", "proposal_type": "sponsored_research", "department": "CSE",
              "funding_agency": "SERB", "proposed_budget": "100.00"},
        format="json",
    )
    assert resp.status_code == 403
    assert Proposal.objects.count() == 0


@pytest.mark.django_db
def test_tc_uc_011(stub_iam):
    """TC-UC-011 / RSPC-UC-003 Main Success Scenario recommended."""
    proposal = _proposal(10, status="submitted_hod")
    hod = _client(stub_iam, 50, HOD)
    resp = hod.post(
        f"/api/v1/rspc/proposals/{proposal.id}/endorse/",
        data={"comments": "Recommended: sound plan"}, format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "endorsed_hod"
    proposal.refresh_from_db()
    assert proposal.status == "endorsed_hod"
    review = ProposalReview.objects.get(proposal=proposal)
    assert (review.action, review.comments) == ("endorse", "Recommended: sound plan")
    assert review.reviewer_user_id == 50


@pytest.mark.django_db
def test_tc_uc_012(stub_iam):
    """TC-UC-012 / RSPC-UC-003 Main Success Scenario non-recommended."""
    proposal = _proposal(10, status="submitted_hod")
    out = proposal_services.reject_proposal(
        proposal=proposal, actor_user_id=50, actor_role="hod",
        comments="Not recommended: budget unjustified",
    )
    assert out.status == "rejected"
    proposal.refresh_from_db()
    assert proposal.status == "rejected"
    assert proposal.status != "endorsed_hod"
    review = ProposalReview.objects.get(proposal=proposal)
    assert review.action == "reject"
    assert review.comments == "Not recommended: budget unjustified"




@pytest.mark.django_db
def test_tc_uc_014(stub_iam):
    """TC-UC-014 / RSPC-UC-003 Exception Flow E1."""
    proposal = _proposal(10, status="submitted_hod")
    client = _client(stub_iam, 51, ("rspc.proposal.view",), roles=("faculty",))
    resp = client.post(f"/api/v1/rspc/proposals/{proposal.id}/endorse/",
                       data={"comments": "x"}, format="json")
    assert resp.status_code == 403
    proposal.refresh_from_db()
    assert proposal.status == "submitted_hod"
    assert ProposalReview.objects.count() == 0


@pytest.mark.django_db
def test_tc_uc_015(stub_iam):
    """TC-UC-015 / RSPC-UC-003 Exception Flow E2."""
    proposal = _proposal(10, status="endorsed_hod")
    hod = _client(stub_iam, 50, HOD)
    resp = hod.post(f"/api/v1/rspc/proposals/{proposal.id}/endorse/",
                    data={"comments": "again"}, format="json")
    assert resp.status_code == 409
    proposal.refresh_from_db()
    assert proposal.status == "endorsed_hod"
    assert ProposalReview.objects.count() == 0










@pytest.mark.django_db
def test_tc_uc_020(stub_iam):
    """TC-UC-020 / RSPC-UC-005 Main Success Scenario approve."""
    proposal = _proposal(10, status="endorsed_hod")
    dean = _client(stub_iam, 100, DEAN)
    resp = dean.post(f"/api/v1/rspc/proposals/{proposal.id}/approve/",
                     data={"comments": "Approved"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "approved_dean"
    proposal.refresh_from_db()
    assert proposal.status == "approved_dean"
    review = ProposalReview.objects.get(proposal=proposal)
    assert (review.action, review.reviewer_user_id) == ("approve", 100)




@pytest.mark.django_db
def test_tc_uc_022(stub_iam):
    """TC-UC-022 / RSPC-UC-005 Main Success Scenario not approved."""
    proposal = _proposal(10, status="endorsed_hod")
    out = proposal_services.reject_proposal(
        proposal=proposal, actor_user_id=100, actor_role="dean", comments="Not approved",
    )
    assert out.status == "rejected"
    proposal.refresh_from_db()
    assert proposal.status == "rejected"
    review = ProposalReview.objects.get(proposal=proposal)
    assert (review.action, review.comments) == ("reject", "Not approved")




@pytest.mark.django_db
def test_tc_uc_024(stub_iam):
    """TC-UC-024 / RSPC-UC-005 Exception Flow E1."""
    proposal = _proposal(10, status="endorsed_hod")
    client = _client(stub_iam, 51, ("rspc.proposal.view",), roles=("faculty",))
    resp = client.post(f"/api/v1/rspc/proposals/{proposal.id}/approve/",
                       data={"comments": "x"}, format="json")
    assert resp.status_code == 403
    proposal.refresh_from_db()
    assert proposal.status == "endorsed_hod"
    assert ProposalReview.objects.count() == 0


@pytest.mark.django_db
def test_tc_uc_025(stub_iam):
    """TC-UC-025 / RSPC-UC-005 Exception Flow E2."""
    proposal = _proposal(10, status="submitted_hod")
    dean = _client(stub_iam, 100, DEAN)
    resp = dean.post(f"/api/v1/rspc/proposals/{proposal.id}/approve/",
                     data={"comments": "early"}, format="json")
    assert resp.status_code == 409
    proposal.refresh_from_db()
    assert proposal.status == "submitted_hod"
    assert ProposalReview.objects.count() == 0












