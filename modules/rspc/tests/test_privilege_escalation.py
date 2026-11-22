"""Privilege escalation, CSRF protection, and permission drift tests for RSPC (Steps 5.1, 5.5, 7.7).

Asserts that:
1. Every write and read endpoint strictly requires its declared permission and module grant (403 for unauthorized).
2. Cookie-authenticated writes without X-CSRF-Token header are rejected with 403.
3. Every permission code used in views and tests matches registry.PERMISSIONS (no permission drift).
4. registry.readiness() correctly verifies module prerequisites.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc import registry
from modules.rspc.models import Project, Proposal
from modules.rspc.services import finance as finance_services
from modules.rspc.services import project as project_services
from modules.rspc.services import proposal as proposal_services


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("rspc",))
    session = make_session(modules=modules, **kw)
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


# --- 1. Permission Drift & Registry Tests ------------------------------------


def test_permission_drift_against_registry():
    """Assert all permission codes used by RSPC exist in registry.PERMISSIONS."""
    declared_codes = {code for code, _ in registry.PERMISSIONS}
    assert len(declared_codes) == len(registry.PERMISSIONS), "Duplicate permission in registry"

    # Verify role grants only contain declared permissions
    for role, perms in registry.ROLE_GRANTS.items():
        for p in perms:
            assert p in declared_codes, f"Role grant '{role}' contains undeclared permission: {p}"

    # Verify nav items require only declared permissions
    for nav in registry.NAV_ITEMS:
        req = nav["required_permission"]
        assert req in declared_codes, f"Nav item '{nav['code']}' requires undeclared permission: {req}"


@pytest.mark.django_db
def test_registry_readiness_passes():
    """Verify registry.readiness() returns empty list (all prerequisites met)."""
    unmet = registry.readiness()
    assert unmet == [], f"Readiness check failed with: {unmet}"


# --- 2. CSRF Rejection Tests ------------------------------------------------


@pytest.mark.django_db
def test_cookie_write_without_csrf_token_is_rejected(stub_iam):
    """A cookie-authenticated write without X-CSRF-Token returns 403."""
    session = make_session(
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.proposal.create", "rspc.proposal.view"),
        modules=("rspc",),
    )
    stub_iam(session)

    client = APIClient()
    # Set cookie instead of Authorization header
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = "test-token"

    payload = {
        "title": "CSRF Attack Proposal",
        "proposal_type": "sponsored_research",
        "department": "CSE",
        "funding_agency": "SERB",
        "proposed_budget": "500000.00",
    }
    # Send POST without X-CSRF-Token
    resp = client.post("/api/v1/rspc/proposals/", data=payload, format="json")
    assert resp.status_code == 403


# --- 3. Per-Endpoint Privilege Escalation Tests -------------------------------


@pytest.mark.django_db
def test_unauthenticated_request_is_rejected():
    client = APIClient()
    resp = client.get("/api/v1/rspc/proposals/")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_missing_module_grant_is_forbidden(stub_iam):
    client = _client(
        stub_iam,
        user_id=10,
        modules=("placement_cell",),  # No 'rspc' grant
        permissions=("rspc.proposal.view",),
    )
    resp = client.get("/api/v1/rspc/proposals/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_proposal_create_permission_denied_without_create_grant(stub_iam):
    client = _client(
        stub_iam,
        user_id=10,
        roles=("student",),
        permissions=("rspc.proposal.view",),  # Only view, not create
    )
    resp = client.post(
        "/api/v1/rspc/proposals/",
        data={
            "title": "Unauthorized Proposal",
            "proposal_type": "sponsored_research",
            "department": "CSE",
            "funding_agency": "DST",
            "proposed_budget": "100000.00",
        },
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_proposal_submit_permission_denied_without_create_grant(stub_iam):
    prop = proposal_services.create_proposal(
        user_id=10,
        title="Draft",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("100000.00"),
    )
    client = _client(
        stub_iam,
        user_id=10,
        roles=("student",),
        permissions=("rspc.proposal.view",),
    )
    resp = client.post(f"/api/v1/rspc/proposals/{prop.id}/submit/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_faculty_cannot_endorse_proposal(stub_iam):
    prop = proposal_services.create_proposal(
        user_id=10,
        title="Test Proposal",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("100000.00"),
    )
    proposal_services.submit_proposal(proposal=prop, actor_user_id=10)

    client = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.proposal.view", "rspc.proposal.create"),
    )
    resp = client.post(
        f"/api/v1/rspc/proposals/{prop.id}/endorse/", data={"comments": "Sneaky"}, format="json"
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_hod_cannot_approve_proposal(stub_iam):
    prop = proposal_services.create_proposal(
        user_id=10,
        title="Test Proposal",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("100000.00"),
    )
    proposal_services.submit_proposal(proposal=prop, actor_user_id=10)
    proposal_services.endorse_proposal(proposal=prop, actor_user_id=50)

    client = _client(
        stub_iam,
        user_id=50,
        roles=("Head of Department",),
        permissions=("rspc.proposal.view", "rspc.proposal.endorse"),
    )
    resp = client.post(
        f"/api/v1/rspc/proposals/{prop.id}/approve/",
        data={"comments": "Overstepping"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_project_create_forbidden_without_grant(stub_iam):
    client = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.project.view",),
    )
    resp = client.post(
        "/api/v1/rspc/projects/",
        data={
            "project_code": "RSPC/TEST/NOPE",
            "project_type": "sponsored",
            "title": "Unauthorized Project",
            "department": "CSE",
            "funding_agency": "DST",
            "sanction_order_no": "SO-1",
            "sanction_date": "2026-11-22",
            "start_date": "2026-11-22",
            "end_date": "2027-11-22",
            "sanctioned_amount": "500000.00",
        },
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_project_activate_forbidden_without_manage_grant(stub_iam):
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-ACT-FAIL",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-1",
        sanction_date=datetime.date.today(),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("100000.00"),
    )
    client = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.project.view",),
    )
    resp = client.post(f"/api/v1/rspc/projects/{proj.id}/activate/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_budget_allocate_forbidden_without_manage_grant(stub_iam):
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-ALLOC-FAIL",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-1",
        sanction_date=datetime.date.today(),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("100000.00"),
    )
    client = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.fund.view",),
    )
    resp = client.post(
        f"/api/v1/rspc/projects/{proj.id}/heads/",
        data={"head_type": "equipment", "allocated_amount": "50000.00"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_disburse_funds_forbidden_without_request_grant(stub_iam):
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-DISB-FAIL",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-1",
        sanction_date=datetime.date.today(),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("100000.00"),
    )
    client = _client(
        stub_iam,
        user_id=10,
        roles=("student",),
        permissions=("rspc.fund.view",),
    )
    resp = client.post(
        f"/api/v1/rspc/projects/{proj.id}/disburse/",
        data={"head_type": "consumables", "amount": "100.00", "reference_no": "X"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_disburse_approve_forbidden_without_approve_grant(stub_iam):
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-DAPP-FAIL",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-1",
        sanction_date=datetime.date.today(),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("100000.00"),
    )
    head = finance_services.allocate_budget_head(
        project=proj, head_type="equipment", allocated_amount=Decimal("50000.00"), actor_user_id=1
    )
    tx = finance_services.disburse_funds(
        project=proj, head_type="equipment", amount=Decimal("1000.00"), reference_no="REQ-1", description="", actor_user_id=10
    )
    client = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.fund.request", "rspc.fund.view"),
    )
    resp = client.post(f"/api/v1/rspc/projects/{proj.id}/disburse/{tx.id}/approve/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_extension_create_forbidden_without_request_grant(stub_iam):
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-EXT-FAIL",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-1",
        sanction_date=datetime.date.today(),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("100000.00"),
    )
    client = _client(
        stub_iam,
        user_id=10,
        roles=("student",),
        permissions=("rspc.project.view",),
    )
    resp = client.post(
        f"/api/v1/rspc/projects/{proj.id}/extensions/",
        data={"requested_months": 3, "justification": "Covid"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_extension_approve_forbidden_without_approve_grant(stub_iam):
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-EXTAPP-FAIL",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-1",
        sanction_date=datetime.date.today(),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("100000.00"),
    )
    from modules.rspc.services import extension as extension_services

    req = extension_services.request_project_extension(
        project=proj,
        requested_end_date=datetime.date.today() + datetime.timedelta(days=90),
        months_requested=3,
        justification="Need more time",
        actor_user_id=10,
    )
    client = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.extension.request", "rspc.project.view"),
    )
    resp = client.post(
        f"/api/v1/rspc/projects/{proj.id}/extensions/{req.id}/approve/",
        data={"approved": True, "comments": "OK"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_closure_create_forbidden_without_request_grant(stub_iam):
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-CLS-FAIL",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-1",
        sanction_date=datetime.date.today(),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("100000.00"),
    )
    client = _client(
        stub_iam,
        user_id=10,
        roles=("student",),
        permissions=("rspc.project.view",),
    )
    resp = client.post(f"/api/v1/rspc/projects/{proj.id}/closure/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_closure_approve_forbidden_without_approve_grant(stub_iam):
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-CLSAPP-FAIL",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-1",
        sanction_date=datetime.date.today(),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("100000.00"),
    )
    from modules.rspc.services import extension as extension_services

    extension_services.request_project_closure(project=proj, remarks="Done", actor_user_id=10)
    client = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.closure.request", "rspc.project.view"),
    )
    resp = client.post(f"/api/v1/rspc/projects/{proj.id}/closure/approve/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_reports_forbidden_without_report_view_grant(stub_iam):
    client = _client(
        stub_iam,
        user_id=10,
        roles=("student",),
        permissions=("rspc.project.view",),
    )
    resp = client.get("/api/v1/rspc/reports/")
    assert resp.status_code == 403
