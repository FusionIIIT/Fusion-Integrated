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


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no notification/dashboard/email "
            "interface (not implemented in this baseline)"
    )
)
def test_tc_uc_066():
    """TC-UC-066 / RSPC-UC-016 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no notification/dashboard/email "
            "interface (not implemented in this baseline)"
    )
)
def test_tc_uc_067():
    """TC-UC-067 / RSPC-UC-016 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: reports endpoint returns only counts; no historical "
            "reports, audit logs or integration tracking views exist"
    )
)
def test_tc_uc_068():
    """TC-UC-068 / RSPC-UC-017 Main Success Scenario."""


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


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no integration tracking "
            "interface (not implemented in this baseline)"
    )
)
def test_tc_uc_071():
    """TC-UC-071 / RSPC-UC-017 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no role-change event intake "
            "interface (not implemented in this baseline)"
    )
)
def test_tc_uc_072():
    """TC-UC-072 / RSPC-UC-018 Main Success Scenario."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no role-change event intake "
            "interface (not implemented in this baseline)"
    )
)
def test_tc_uc_073():
    """TC-UC-073 / RSPC-UC-018 Alternative Flow A1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no role-change event intake "
            "interface (not implemented in this baseline)"
    )
)
def test_tc_uc_074():
    """TC-UC-074 / RSPC-UC-018 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no role-change event intake "
            "interface (not implemented in this baseline)"
    )
)
def test_tc_uc_075():
    """TC-UC-075 / RSPC-UC-018 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no project update "
            "(details/milestones/progress/utilization) interface (not implemented "
            "in this baseline)"
    )
)
def test_tc_uc_076():
    """TC-UC-076 / RSPC-UC-021 Main Success Scenario."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no project update "
            "(details/milestones/progress/utilization) interface (not implemented "
            "in this baseline)"
    )
)
def test_tc_uc_077():
    """TC-UC-077 / RSPC-UC-021 Alternative Flow A1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no project update "
            "(details/milestones/progress/utilization) interface (not implemented "
            "in this baseline)"
    )
)
def test_tc_uc_078():
    """TC-UC-078 / RSPC-UC-021 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no project update "
            "(details/milestones/progress/utilization) interface (not implemented "
            "in this baseline)"
    )
)
def test_tc_uc_079():
    """TC-UC-079 / RSPC-UC-021 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no appointment selection "
            "recommendation interface (not implemented in this baseline)"
    )
)
def test_tc_uc_080():
    """TC-UC-080 / RSPC-UC-022 Main Success Scenario."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no appointment selection "
            "recommendation interface (not implemented in this baseline)"
    )
)
def test_tc_uc_081():
    """TC-UC-081 / RSPC-UC-022 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no appointment selection "
            "recommendation interface (not implemented in this baseline)"
    )
)
def test_tc_uc_082():
    """TC-UC-082 / RSPC-UC-022 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no staff appointment Dean "
            "decision interface (not implemented in this baseline)"
    )
)
def test_tc_uc_083():
    """TC-UC-083 / RSPC-UC-023 Main Success Scenario approve."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no staff appointment Dean "
            "decision interface (not implemented in this baseline)"
    )
)
def test_tc_uc_084():
    """TC-UC-084 / RSPC-UC-023 Main Success Scenario forward to Director."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no staff appointment Dean "
            "decision interface (not implemented in this baseline)"
    )
)
def test_tc_uc_085():
    """TC-UC-085 / RSPC-UC-023 Main Success Scenario not approved."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no staff appointment Dean "
            "decision interface (not implemented in this baseline)"
    )
)
def test_tc_uc_086():
    """TC-UC-086 / RSPC-UC-023 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no staff appointment Dean "
            "decision interface (not implemented in this baseline)"
    )
)
def test_tc_uc_087():
    """TC-UC-087 / RSPC-UC-023 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the fund approval endpoint is a stub that records no "
            "decision, audit log or notification"
    )
)
def test_tc_uc_088():
    """TC-UC-088 / RSPC-UC-024 Main Success Scenario approve."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no Dean-to-Director forwarding "
            "of financial requests interface (not implemented in this baseline)"
    )
)
def test_tc_uc_089():
    """TC-UC-089 / RSPC-UC-024 Main Success Scenario forward to Director."""


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


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the fund approval endpoint is a stub; no ledger-effect "
            "inspection is meaningful"
    )
)
def test_tc_uc_091():
    """TC-UC-091 / RSPC-UC-024 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_092():
    """TC-UC-092 / RSPC-UC-025 Main Success Scenario."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_093():
    """TC-UC-093 / RSPC-UC-025 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_094():
    """TC-UC-094 / RSPC-UC-025 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_095():
    """TC-UC-095 / RSPC-UC-026 Main Success Scenario approve."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_096():
    """TC-UC-096 / RSPC-UC-026 Main Success Scenario forward to Director."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_097():
    """TC-UC-097 / RSPC-UC-026 Main Success Scenario not approved."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_098():
    """TC-UC-098 / RSPC-UC-026 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_099():
    """TC-UC-099 / RSPC-UC-026 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_100():
    """TC-UC-100 / RSPC-UC-027 Main Success Scenario."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_101():
    """TC-UC-101 / RSPC-UC-027 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no procurement or closure "
            "verification interface (not implemented in this baseline)"
    )
)
def test_tc_uc_102():
    """TC-UC-102 / RSPC-UC-027 Exception Flow E2."""


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


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no Dean-to-Director closure "
            "forwarding interface (not implemented in this baseline)"
    )
)
def test_tc_uc_104():
    """TC-UC-104 / RSPC-UC-028 Main Success Scenario forward to Director."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no closure rejection interface "
            "(not implemented in this baseline)"
    )
)
def test_tc_uc_105():
    """TC-UC-105 / RSPC-UC-028 Alternative Flow A1."""


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


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no settlement or inventory "
            "interface (not implemented in this baseline)"
    )
)
def test_tc_uc_107():
    """TC-UC-107 / RSPC-UC-028 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no inter-module "
            "integration/tracking interface (not implemented in this baseline)"
    )
)
def test_tc_uc_108():
    """TC-UC-108 / RSPC-UC-029 Main Success Scenario."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no inter-module "
            "integration/tracking interface (not implemented in this baseline)"
    )
)
def test_tc_uc_109():
    """TC-UC-109 / RSPC-UC-029 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no inter-module "
            "integration/tracking interface (not implemented in this baseline)"
    )
)
def test_tc_uc_110():
    """TC-UC-110 / RSPC-UC-029 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no inter-module "
            "integration/tracking interface (not implemented in this baseline)"
    )
)
def test_tc_uc_111():
    """TC-UC-111 / RSPC-UC-030 Main Success Scenario."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no inter-module "
            "integration/tracking interface (not implemented in this baseline)"
    )
)
def test_tc_uc_112():
    """TC-UC-112 / RSPC-UC-030 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no inter-module "
            "integration/tracking interface (not implemented in this baseline)"
    )
)
def test_tc_uc_113():
    """TC-UC-113 / RSPC-UC-030 Exception Flow E2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no notification/email/reminder "
            "delivery interface (not implemented in this baseline)"
    )
)
def test_tc_uc_114():
    """TC-UC-114 / RSPC-UC-031 Main Success Scenario."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no notification/email/reminder "
            "delivery interface (not implemented in this baseline)"
    )
)
def test_tc_uc_115():
    """TC-UC-115 / RSPC-UC-031 Alternative Flow A1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no notification/email/reminder "
            "delivery interface (not implemented in this baseline)"
    )
)
def test_tc_uc_116():
    """TC-UC-116 / RSPC-UC-031 Alternative Flow A2."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no notification/email/reminder "
            "delivery interface (not implemented in this baseline)"
    )
)
def test_tc_uc_117():
    """TC-UC-117 / RSPC-UC-031 Exception Flow E1."""


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: the RSPC module exposes no notification/email/reminder "
            "delivery interface (not implemented in this baseline)"
    )
)
def test_tc_uc_118():
    """TC-UC-118 / RSPC-UC-031 Exception Flow E2."""
