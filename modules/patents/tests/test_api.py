"""Tests for patents API endpoints (Step 4.5)."""
from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.patents.domain import permissions as p
from modules.patents.domain import state_machine as sm
from modules.patents.models import PatentApplication, PatentPolicy

pytestmark = pytest.mark.django_db


def make_client(stub_iam, user_id=101, permissions=(), modules=("patents",), roles=("student",)):
    stub_iam(
        make_session(
            user_id=user_id,
            kind="student",
            roles=roles,
            active_role=roles[0] if roles else None,
            modules=modules,
            permissions=permissions,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def test_module_gate_denies_outsider(stub_iam):
    client = make_client(stub_iam, user_id=999, modules=("other_module",), permissions=(p.P_APPLICATION_VIEW_SELF,))
    resp = client.get("/api/v1/patents/applications")
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_permission_gate_denies_unauthorized_action(stub_iam):
    client = make_client(stub_iam, user_id=101, permissions=(p.P_APPLICATION_VIEW_SELF,))
    # Try to assign director without permission
    resp = client.post("/api/v1/patents/applications/1/assign-director", {"director_id": 201})
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_unauthorized_create_fails_with_403(stub_iam):
    # R1-02: User with only view permission cannot create an application
    client = make_client(stub_iam, user_id=101, permissions=(p.P_APPLICATION_VIEW_SELF,))
    resp = client.post(
        "/api/v1/patents/applications",
        {
            "title": "Unauthorized Title",
            "abstract": "Abstract",
            "description": "Description",
            "claims": "Claims",
            "co_inventors": [],
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_create_and_list_applications(stub_iam):
    client = make_client(
        stub_iam,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_CREATE),
    )

    payload = {
        "title": "Quantum Photonics Device",
        "abstract": "Single photon generator on chip.",
        "description": "Lithography details and waveguides.",
        "claims": "1. An optical cavity...",
        "domain_category": "Physics",
        "co_inventors": [
            {"name": "Alice", "email": "alice@ex.com", "share_percentage": 100.0},
        ],
    }
    resp = client.post("/api/v1/patents/applications", payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    app_id = resp.data["id"]
    assert resp.data["title"] == "Quantum Photonics Device"

    # List applications
    resp_list = client.get("/api/v1/patents/applications")
    assert resp_list.status_code == status.HTTP_200_OK
    assert len(resp_list.data["results"]) == 1
    assert resp_list.data["results"][0]["id"] == app_id


def test_foreign_application_lookup_returns_404(stub_iam):
    # App belongs to user 101
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0301",
        title="Secret App",
        abstract="Abs",
        description="Desc",
        claims="Claims",
    )

    # User 102 tries to view it
    client = make_client(
        stub_iam,
        user_id=102,
        permissions=(p.P_APPLICATION_VIEW_SELF,),
    )
    resp = client.get(f"/api/v1/patents/applications/{app.id}")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_director_assignment_and_review(stub_iam):
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0302",
        title="Review Test App",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.SUBMITTED,
    )

    # PCC_ADMIN assigns director
    admin_client = make_client(
        stub_iam,
        user_id=401,
        roles=("pcc_admin",),
        permissions=(p.P_APPLICATION_VIEW, p.P_APPLICATION_ASSIGN_DIRECTOR),
    )
    resp = admin_client.post(
        f"/api/v1/patents/applications/{app.id}/assign-director",
        {"director_id": 201},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["status"] == sm.UNDER_REVIEW
    assert resp.data["assigned_director_id"] == 201

    # Director submits review
    dir_client = make_client(
        stub_iam,
        user_id=201,
        roles=("Director",),
        permissions=(p.P_APPLICATION_VIEW, p.P_APPLICATION_REVIEW),
    )
    rev_resp = dir_client.post(
        f"/api/v1/patents/applications/{app.id}/review-decision",
        {
            "decision": "APPROVE",
            "justification": "Novelty and non-obviousness criteria are satisfied across all claims.",
        },
        format="json",
    )
    assert rev_resp.status_code == status.HTTP_200_OK
    assert rev_resp.data["decision"] == "APPROVE"


def test_withdraw_application(stub_iam):
    PatentPolicy.objects.create(withdrawal_eligible_states=[sm.DRAFT], is_active=True)
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0303",
        title="Withdraw App",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.DRAFT,
    )

    client = make_client(
        stub_iam,
        user_id=101,
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_WITHDRAW),
    )
    resp = client.post(
        f"/api/v1/patents/applications/{app.id}/withdraw",
        {"reason": "Decided not to commercialize."},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["status"] == sm.WITHDRAWN


def test_cookie_csrf_rejection_and_acceptance(stub_iam, settings):
    # R1-10: Cookie session without X-CSRF-Token is rejected with 403 Forbidden
    stub_iam(
        make_session(
            user_id=101,
            kind="student",
            roles=("student",),
            active_role="student",
            modules=("patents",),
            permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_CREATE),
        )
    )
    client = APIClient()
    session_cookie = "mock-cookie-session-token"
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = session_cookie

    resp = client.post(
        "/api/v1/patents/applications",
        {
            "title": "Quantum CSRF Test Device",
            "abstract": "Abstract",
            "description": "Description",
            "claims": "Claims",
            "co_inventors": [],
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    from core.api import csrf
    valid_csrf = csrf.token_for(session_cookie)
    client.credentials(HTTP_X_CSRF_TOKEN=valid_csrf)
    resp2 = client.post(
        "/api/v1/patents/applications",
        {
            "title": "Quantum CSRF Test Device Valid",
            "abstract": "Abstract",
            "description": "Description",
            "claims": "Claims",
            "co_inventors": [],
        },
        format="json",
    )
    assert resp2.status_code == status.HTTP_201_CREATED

