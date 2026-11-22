"""API integration tests for RSPC endpoints using stub_iam."""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import ResearchProposal

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, user_id=101, permissions=("rspc.proposal.view",)):
    session = make_session(
        user_id=user_id,
        kind="faculty",
        modules=("rspc",),
        permissions=permissions,
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def test_unauthenticated_proposals_rejected():
    client = APIClient()
    res = client.get("/api/v1/rspc/proposals")
    assert res.status_code in (401, 403)


def test_list_proposals_authenticated(stub_iam):
    client = _auth_client(stub_iam, permissions=("rspc.proposal.view",))
    ResearchProposal.objects.create(
        title="AI Sensing Grid",
        pi_id=101,
        department="CSE",
        funding_agency="DST",
        budget=Decimal("500000.00"),
        objectives="Sensing",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
    )
    res = client.get("/api/v1/rspc/proposals")
    assert res.status_code == 200
    data = res.json()
    rows = data.get("results", data)
    assert len(rows) >= 1
    assert rows[0]["title"] == "AI Sensing Grid"


def test_create_proposal_valid(stub_iam):
    client = _auth_client(stub_iam, permissions=("rspc.proposal.view", "rspc.proposal.submit"))
    payload = {
        "title": "Quantum Photonics",
        "pi_id": 101,
        "department": "Physics",
        "funding_agency": "SERB",
        "budget": "1500000.00",
        "objectives": "Photonics experiments",
        "start_date": "2026-06-01",
        "end_date": "2028-05-31",
        "timeline_months": 24,
    }
    res = client.post("/api/v1/rspc/proposals", payload, format="json")
    assert res.status_code == 201
    assert res.json()["title"] == "Quantum Photonics"


def test_create_proposal_invalid_budget(stub_iam):
    client = _auth_client(stub_iam, permissions=("rspc.proposal.view", "rspc.proposal.submit"))
    payload = {
        "title": "Invalid Proposal",
        "pi_id": 101,
        "department": "Physics",
        "funding_agency": "SERB",
        "budget": "-500.00",
        "objectives": "Photonics experiments",
        "start_date": "2026-06-01",
        "end_date": "2028-05-31",
    }
    res = client.post("/api/v1/rspc/proposals", payload, format="json")
    assert res.status_code == 400


def test_proposal_transition_workflow(stub_iam):
    client = _auth_client(stub_iam, permissions=("rspc.proposal.view",))
    p = ResearchProposal.objects.create(
        title="Robotics Arm",
        pi_id=101,
        department="ME",
        funding_agency="DRDO",
        budget=Decimal("800000.00"),
        objectives="Arm fabrication",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
        status="DRAFT",
    )

    # Illegal transition
    res_bad = client.post(
        f"/api/v1/rspc/proposals/{p.id}/transition",
        {"status": "APPROVED_DIRECTOR"},
        format="json",
    )
    assert res_bad.status_code == 400

    # Legal transition
    res_good = client.post(
        f"/api/v1/rspc/proposals/{p.id}/transition",
        {"status": "SUBMITTED_HOD", "remarks": "Submitting to HOD"},
        format="json",
    )
    assert res_good.status_code == 200
    assert res_good.json()["status"] == "SUBMITTED_HOD"


def test_consultancy_api_lifecycle(stub_iam):
    client = _auth_client(
        stub_iam,
        permissions=("rspc.consultancy.view", "rspc.consultancy.register"),
    )
    payload = {
        "title": "Smart City Audit",
        "pi_id": 101,
        "client_name": "Municipal Corp",
        "scope_of_work": "IoT sensor review",
        "deliverables": "Final compliance audit",
        "start_date": "2026-04-01",
        "end_date": "2026-10-01",
        "total_cost": "600000.00",
        "institutional_share": "150000.00",
    }
    res = client.post("/api/v1/rspc/consultancies", payload, format="json")
    assert res.status_code == 201
    cid = res.json()["id"]

    res_get = client.get(f"/api/v1/rspc/consultancies/{cid}")
    assert res_get.status_code == 200
    assert res_get.json()["client_name"] == "Municipal Corp"
