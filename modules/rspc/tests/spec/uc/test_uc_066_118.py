"""Spec tests for RSPC use cases 66-118 (strategy UC)."""

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
def test_tc_uc_069(stub_iam):
    """TC-UC-069 / RSPC-UC-017 Alternative Flow A1."""
    _project(10, "P-10", status="active")
    _project(11, "P-11", status="active")
    faculty = _client(stub_iam, 10, FAC)
    assert [r["project_code"] for r in
            faculty.get("/api/v1/rspc/projects/").data] == ["P-10"]
    assert faculty.get("/api/v1/rspc/reports/").status_code == 403
    for uid, perms, role in ((100, DEAN, "Dean (RSPC)"), (101, DIRECTOR, "Director")):
        client = _client(stub_iam, uid, perms, roles=(role,))
        listed = client.get("/api/v1/rspc/projects/")
        assert {r["project_code"] for r in listed.data} == {"P-10", "P-11"}
        report = client.get("/api/v1/rspc/reports/")
        assert report.status_code == 200
        assert report.data["total_projects"] == 2


@pytest.mark.django_db
def test_tc_uc_070(stub_iam):
    """TC-UC-070 / RSPC-UC-017 Exception Flow E1."""
    _project(10, "P-10", status="active")
    client = _client(stub_iam, 10, FAC)
    resp = client.get("/api/v1/rspc/reports/")
    assert resp.status_code == 403
    assert "total_projects" not in resp.content.decode()








































@pytest.mark.django_db
def test_tc_uc_090(stub_iam):
    """TC-UC-090 / RSPC-UC-024 Exception Flow E1."""
    project = _project(10, "P-A", status="active")
    head = _alloc(project)
    tx = ProjectFundTransaction.objects.get(budget_head=head)
    before = _snapshot()
    client = _client(stub_iam, 10, FAC)
    resp = client.post(f"/api/v1/rspc/projects/{project.id}/disburse/{tx.id}/approve/")
    assert resp.status_code == 403
    assert _snapshot() == before


























@pytest.mark.django_db
def test_tc_uc_103(stub_iam):
    """TC-UC-103 / RSPC-UC-028 Main Success Scenario approve and archive."""
    project = _project(10, "P-A", status="closure_pending")
    ProjectClosureRequest.objects.create(project=project, status="pending")
    dean = _client(stub_iam, 100, DEAN)
    resp = dean.post(f"/api/v1/rspc/projects/{project.id}/closure/approve/")
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"
    project.refresh_from_db()
    assert project.status == "closed"
    closure = ProjectClosureRequest.objects.get(project=project)
    assert closure.status == "approved"
    assert closure.closed_at is not None
    assert closure.closed_by_user_id == 100






@pytest.mark.django_db
def test_tc_uc_106(stub_iam):
    """TC-UC-106 / RSPC-UC-028 Exception Flow E1."""
    project = _project(10, "P-A", status="closure_pending")
    ProjectClosureRequest.objects.create(project=project, status="pending")
    client = _client(stub_iam, 10, FAC)
    resp = client.post(f"/api/v1/rspc/projects/{project.id}/closure/approve/")
    assert resp.status_code == 403
    project.refresh_from_db()
    assert project.status == "closure_pending"
    assert ProjectClosureRequest.objects.get(project=project).status == "pending"
























