"""API endpoint tests for RSPC (Testing HTTP layer, permissions, scoping)."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.services import (
    project as project_services,
)
from modules.rspc.services import (
    proposal as proposal_services,
)


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("rspc",))
    session = make_session(modules=modules, **kw)
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


@pytest.mark.django_db
def test_proposal_api_create_and_list(stub_iam):
    client = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.proposal.view", "rspc.proposal.create"),
    )

    payload = {
        "title": "Quantum Cryptography Testbed",
        "proposal_type": "sponsored_research",
        "department": "CSE",
        "funding_agency": "SERB",
        "proposed_budget": "2500000.00",
        "summary": "Secure key exchange protocol.",
    }
    resp = client.post("/api/v1/rspc/proposals/", data=payload, format="json")
    assert resp.status_code == 201
    prop_id = resp.data["id"]
    assert resp.data["status"] == "draft"

    # List proposals (PI sees own)
    list_resp = client.get("/api/v1/rspc/proposals/")
    assert list_resp.status_code == 200
    assert len(list_resp.data) == 1
    assert list_resp.data[0]["id"] == prop_id


@pytest.mark.django_db
def test_scoping_isolation_returns_404_not_403(stub_iam):
    """Step 2.5: Items out of scope return 404 rather than 403."""
    prop = proposal_services.create_proposal(
        user_id=10,
        title="PI-1 Confidential Research",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="ISRO",
        proposed_budget=Decimal("4000000.00"),
    )

    # PI-1 can view it
    client_pi1 = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.proposal.view",),
    )
    r1 = client_pi1.get(f"/api/v1/rspc/proposals/{prop.id}/")
    assert r1.status_code == 200

    # PI-2 attempting to view PI-1's proposal gets 404 (NOT 403)
    client_pi2 = _client(
        stub_iam,
        user_id=20,
        roles=("faculty",),
        permissions=("rspc.proposal.view",),
    )
    r2 = client_pi2.get(f"/api/v1/rspc/proposals/{prop.id}/")
    assert r2.status_code == 404


@pytest.mark.django_db
def test_endorse_and_approve_api_workflow(stub_iam):
    prop = proposal_services.create_proposal(
        user_id=10,
        title="Thermal Fluid Dynamics",
        proposal_type="sponsored_research",
        department="ME",
        funding_agency="DST",
        proposed_budget=Decimal("1500000.00"),
    )

    # Submit as PI
    client_pi = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.proposal.create", "rspc.proposal.view"),
    )
    sub_resp = client_pi.post(f"/api/v1/rspc/proposals/{prop.id}/submit/")
    assert sub_resp.status_code == 200
    assert sub_resp.data["status"] == "submitted_hod"

    # Endorse by HoD
    client_hod = _client(
        stub_iam,
        user_id=50,
        roles=("Head of Department",),
        permissions=("rspc.proposal.endorse", "rspc.proposal.view"),
    )
    end_resp = client_hod.post(
        f"/api/v1/rspc/proposals/{prop.id}/endorse/",
        data={"comments": "Recommended"},
        format="json",
    )
    assert end_resp.status_code == 200
    assert end_resp.data["status"] == "endorsed_hod"

    # Approve by Dean
    client_dean = _client(
        stub_iam,
        user_id=100,
        roles=("Dean (RSPC)",),
        permissions=("rspc.proposal.approve", "rspc.proposal.view"),
    )
    app_resp = client_dean.post(
        f"/api/v1/rspc/proposals/{prop.id}/approve/",
        data={"comments": "Sanction approved"},
        format="json",
    )
    assert app_resp.status_code == 200
    assert app_resp.data["status"] == "approved_dean"


@pytest.mark.django_db
def test_ledger_disbursement_api(stub_iam):
    today = datetime.date.today()
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="RSPC/2026/EE/099",
        project_type="sponsored",
        title="Smart Grid Resilience",
        department="EE",
        funding_agency="PowerGrid",
        sanction_order_no="PG/2026/01",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("3000000.00"),
    )

    client_admin = _client(
        stub_iam,
        user_id=1,
        roles=("admin",),
        permissions=("rspc.project.view", "rspc.project.manage", "rspc.fund.view"),
    )

    # Admin allocates budget
    alloc_resp = client_admin.post(
        f"/api/v1/rspc/projects/{proj.id}/heads/",
        data={"head_type": "consumables", "allocated_amount": "500000.00"},
        format="json",
    )
    assert alloc_resp.status_code == 201

    # PI requests disbursement
    client_pi = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.project.view", "rspc.fund.request", "rspc.fund.view"),
    )
    disb_resp = client_pi.post(
        f"/api/v1/rspc/projects/{proj.id}/disburse/",
        data={
            "head_type": "consumables",
            "amount": "120000.00",
            "reference_no": "INV-2026-001",
            "description": "Lab raw material",
        },
        format="json",
    )
    assert disb_resp.status_code == 201
    assert disb_resp.data["amount"] == "120000.00"

    # Ledger audit
    ledger_resp = client_pi.get(f"/api/v1/rspc/projects/{proj.id}/ledger/")
    assert ledger_resp.status_code == 200
    assert len(ledger_resp.data) >= 2  # 1 allocation + 1 disbursement
