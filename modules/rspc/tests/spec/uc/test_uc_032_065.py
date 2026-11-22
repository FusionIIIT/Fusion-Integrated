"""Spec tests for RSPC use cases 32-65 (strategy UC)."""

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
    Proposal,
)
from modules.rspc.registry import ROLE_GRANTS
from modules.rspc.services import finance as finance_services

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
def test_tc_uc_032(stub_iam):
    """TC-UC-032 / RSPC-UC-007 Main Success Scenario."""
    client = _client(stub_iam, 10, FAC)
    created = client.post(
        "/api/v1/rspc/proposals/",
        data={"title": "Industry Consultancy", "proposal_type": "consultancy",
              "department": "ME", "funding_agency": "Acme Pvt Ltd",
              "proposed_budget": "750000.00",
              "summary": "Scope, deliverables, timelines, financial terms."},
        format="json",
    )
    assert created.status_code == 201
    pid = created.data["id"]
    assert created.data["proposal_type"] == "consultancy"
    submitted = client.post(f"/api/v1/rspc/proposals/{pid}/submit/")
    assert submitted.status_code == 200
    assert submitted.data["status"] == "submitted_hod"
    assert Proposal.objects.get(pk=pid).status == "submitted_hod"




@pytest.mark.django_db
def test_tc_uc_034(stub_iam):
    """TC-UC-034 / RSPC-UC-007 Exception Flow E1."""
    client = _client(stub_iam, 12, ("rspc.proposal.view",), roles=("student",))
    resp = client.post(
        "/api/v1/rspc/proposals/",
        data={"title": "C", "proposal_type": "consultancy", "department": "ME",
              "funding_agency": "Acme", "proposed_budget": "100.00"},
        format="json",
    )
    assert resp.status_code == 403
    assert Proposal.objects.count() == 0


@pytest.mark.django_db
def test_tc_uc_035(stub_iam):
    """TC-UC-035 / RSPC-UC-007 Exception Flow E2."""
    client = _client(stub_iam, 10, FAC)
    resp = client.post(
        "/api/v1/rspc/proposals/",
        data={"title": "C", "proposal_type": "consultancy", "department": "ME",
              "proposed_budget": "100.00"},
        format="json",
    )
    assert resp.status_code in (400, 422)
    assert "funding_agency" in resp.content.decode()
    assert Proposal.objects.count() == 0




@pytest.mark.django_db
def test_tc_uc_037(stub_iam):
    """TC-UC-037 / RSPC-UC-008 Alternative Flow A1."""
    project = _project(10, "C-1", status="active", project_type="consultancy")
    _alloc(project)
    admin = _client(stub_iam, 1, ADMIN)
    dean = _client(stub_iam, 100, DEAN)
    for client in (admin, dean):
        detail = client.get(f"/api/v1/rspc/projects/{project.id}/")
        assert detail.status_code == 200
        assert detail.data["project_type"] == "consultancy"
        ledger = client.get(f"/api/v1/rspc/projects/{project.id}/ledger/")
        assert ledger.status_code == 200
        assert len(ledger.data) == 1


@pytest.mark.django_db
def test_tc_uc_038(stub_iam):
    """TC-UC-038 / RSPC-UC-008 Exception Flow E1."""
    project = _project(10, "C-1", status="active", project_type="consultancy")
    _alloc(project)
    client = _client(stub_iam, 11, FAC)
    assert client.get(f"/api/v1/rspc/projects/{project.id}/").status_code == 404
    assert client.get(f"/api/v1/rspc/projects/{project.id}/ledger/").status_code == 404




















@pytest.mark.django_db
def test_tc_uc_048(stub_iam):
    """TC-UC-048 / RSPC-UC-011 Exception Flow E1."""
    project = _project(10, "P-A", status="active")
    _alloc(project)
    before = _snapshot()
    client = _client(stub_iam, 10, ("rspc.project.view", "rspc.fund.view"))
    resp = client.post(
        f"/api/v1/rspc/projects/{project.id}/disburse/",
        data={"head_type": "consumables", "amount": "100.00", "reference_no": "R-1"},
        format="json",
    )
    assert resp.status_code == 403
    assert _snapshot() == before


























@pytest.mark.django_db
def test_tc_uc_061(stub_iam):
    """TC-UC-061 / RSPC-UC-015 Main Success Scenario."""
    project = _project(10, "P-A", status="active")
    client = _client(stub_iam, 10, FAC)
    resp = client.post(f"/api/v1/rspc/projects/{project.id}/closure/",
                       data={"remarks": "Work complete"}, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending"
    project.refresh_from_db()
    assert project.status == "closure_pending"
    closure = ProjectClosureRequest.objects.get(project=project)
    assert (closure.status, closure.remarks) == ("pending", "Work complete")


@pytest.mark.django_db
def test_tc_uc_062(stub_iam):
    """TC-UC-062 / RSPC-UC-015 Exception Flow E1."""
    project = _project(10, "P-A", status="active")
    client = _client(stub_iam, 10, ("rspc.project.view",))
    resp = client.post(f"/api/v1/rspc/projects/{project.id}/closure/",
                       data={"remarks": "x"}, format="json")
    assert resp.status_code == 403
    assert ProjectClosureRequest.objects.count() == 0
    project.refresh_from_db()
    assert project.status == "active"






