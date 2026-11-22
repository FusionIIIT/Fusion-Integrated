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






