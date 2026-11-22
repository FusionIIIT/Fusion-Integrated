"""Spec tests TC-BR-041 .. TC-BR-060 (closure, scope, authorization, role assignment)."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import Project, ProjectFundTransaction, Proposal, ProposalReview
from modules.rspc.registry import ROLE_GRANTS
from modules.rspc.services import finance as finance_services

NO_INTEGRATION = (
    "NOT_AUTOMATED: the implementation has no external-integration configuration or "
    "integration intake interface, and no cross-system event feed to observe"
)
NO_EXTERNAL_EXEC = (
    "NOT_AUTOMATED: the implementation has no appointment/stipend, settlement, procurement "
    "or notification interface; the absence of external HR, bank, vendor or mail "
    "execution cannot be observed through any available interface"
)


def _client(stub_iam, user_id, role, **extra):
    session = make_session(
        user_id=user_id,
        kind="faculty",
        roles=(role,) if role else (),
        active_role=role or "student",
        permissions=ROLE_GRANTS.get(role, ()),
        modules=("rspc",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token", **extra)
    return client


def _project(user_id=10, status="active", code="RSPC/BR/041"):
    today = datetime.date.today()
    return Project.objects.create(
        user_id=user_id,
        project_code=code,
        project_type="sponsored",
        title="Sanctioned Research Project",
        department="CSE",
        funding_agency="SERB",
        sanction_order_no="SO/2026/1",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("100000.00"),
        status=status,
    )


def _proposal(status="draft", user_id=10):
    return Proposal.objects.create(
        user_id=user_id,
        title="Thermal Fluid Dynamics",
        proposal_type="sponsored_research",
        department="ME",
        funding_agency="DST",
        proposed_budget=Decimal("1500000.00"),
        status=status,
    )


def _proposal_payload():
    return {
        "title": "Quantum Cryptography Testbed",
        "proposal_type": "sponsored_research",
        "department": "CSE",
        "funding_agency": "SERB",
        "proposed_budget": "2500000.00",
    }


@pytest.mark.django_db
def test_tc_br_041_pending_closure_does_not_archive_project(stub_iam):
    """TC-BR-041 / BR-RSPC-043 closure not approved (closure requested, still pending)."""
    project = _project()

    resp = _client(stub_iam, 10, "faculty").post(
        f"/api/v1/rspc/projects/{project.id}/closure/", data={"remarks": "Done"}, format="json"
    )

    assert resp.status_code == 201
    project.refresh_from_db()
    assert project.status != "closed"
    assert project.closure_record.status == "pending"
    assert project.closure_record.closed_at is None


@pytest.mark.django_db
def test_tc_br_042_closure_performs_only_rspc_archival(stub_iam):
    """TC-BR-042 / BR-RSPC-043 no external operations.

    Closure approval changes only the project/closure records; budget heads and the fund
    ledger (no settlement, refund or inventory entry) are untouched.
    """
    project = _project()
    head = finance_services.allocate_budget_head(
        project=project,
        head_type="equipment",
        allocated_amount=Decimal("50000.00"),
        actor_user_id=100,
    )
    _client(stub_iam, 10, "faculty").post(f"/api/v1/rspc/projects/{project.id}/closure/")

    ledger_before = list(ProjectFundTransaction.objects.values_list("id", "transaction_type"))

    resp = _client(stub_iam, 100, "Dean (RSPC)").post(
        f"/api/v1/rspc/projects/{project.id}/closure/approve/"
    )

    assert resp.status_code == 200
    project.refresh_from_db()
    assert project.status == "closed"
    assert list(ProjectFundTransaction.objects.values_list("id", "transaction_type")) == (
        ledger_before
    )
    head.refresh_from_db()
    assert (head.allocated_amount, head.spent_amount, head.committed_amount) == (
        Decimal("50000.00"),
        Decimal("0.00"),
        Decimal("0.00"),
    )


@pytest.mark.skip(reason=NO_INTEGRATION)
def test_tc_br_043_configured_integration_information_processed():
    """TC-BR-043 / BR-RSPC-045 configured integration."""


@pytest.mark.skip(reason=NO_INTEGRATION)
def test_tc_br_044_unconfigured_integration_information_not_processed():
    """TC-BR-044 / BR-RSPC-045 unconfigured integration."""


@pytest.mark.django_db
def test_tc_br_045_in_scope_project_data_displayed(stub_iam):
    """TC-BR-045 / BR-RSPC-048 in-scope data."""
    project = _project(user_id=10)

    resp = _client(stub_iam, 10, "faculty").get(f"/api/v1/rspc/projects/{project.id}/")

    assert resp.status_code == 200
    assert resp.data["id"] == project.id


@pytest.mark.django_db
def test_tc_br_046_out_of_scope_project_data_not_available(stub_iam):
    """TC-BR-046 / BR-RSPC-048 out-of-scope data.

    Out-of-visibility records return 404, never 403 (api-conventions, Status codes).
    """
    project = _project(user_id=10)

    resp = _client(stub_iam, 20, "faculty").get(f"/api/v1/rspc/projects/{project.id}/")

    assert resp.status_code == 404
    assert "RSPC/BR/041" not in str(resp.content)


@pytest.mark.django_db
def test_tc_br_047_permitted_action_succeeds(stub_iam):
    """TC-BR-047 / BR-RSPC-049 permitted action (faculty submits own proposal)."""
    prop = _proposal(status="draft", user_id=10)

    resp = _client(stub_iam, 10, "faculty").post(f"/api/v1/rspc/proposals/{prop.id}/submit/")

    assert resp.status_code == 200
    prop.refresh_from_db()
    assert prop.status == "submitted_hod"


@pytest.mark.django_db
def test_tc_br_048_unauthorized_action_blocked_state_unchanged(stub_iam):
    """TC-BR-048 / BR-RSPC-049 unauthorized action (Faculty approving as Dean-RSPC)."""
    prop = _proposal(status="endorsed_hod", user_id=10)

    resp = _client(stub_iam, 11, "faculty").post(
        f"/api/v1/rspc/proposals/{prop.id}/approve/", data={"comments": "ok"}, format="json"
    )

    assert resp.status_code == 403
    prop.refresh_from_db()
    assert prop.status == "endorsed_hod"
    assert prop.reviews.count() == 0


@pytest.mark.django_db
def test_tc_br_049_auditable_event_logged(stub_iam):
    """TC-BR-049 / BR-RSPC-050 auditable event logged (decision recorded)."""
    prop = _proposal(status="submitted_hod", user_id=10)

    resp = _client(stub_iam, 50, "Head of Department").post(
        f"/api/v1/rspc/proposals/{prop.id}/endorse/", data={"comments": "ok"}, format="json"
    )

    assert resp.status_code == 200
    review = ProposalReview.objects.get(proposal=prop)
    assert review.action == "endorse"
    assert review.reviewer_user_id == 50
    assert review.created_at is not None


@pytest.mark.skip(reason=NO_INTEGRATION)
def test_tc_br_050_non_rspc_event_creates_no_audit_entry():
    """TC-BR-050 / BR-RSPC-050 non-RSPC info excluded."""


@pytest.mark.django_db
def test_tc_br_051_authorized_mechanism_role_assignment_applied(stub_iam):
    """TC-BR-051 / BR-RSPC-053 authorized mechanism.

    The authorized mechanism is the Fusion identity session; RSPC applies the role it supplies.
    """
    before = _client(stub_iam, 10, None).get("/api/v1/rspc/proposals/")
    assert before.status_code == 403

    after = _client(stub_iam, 10, "faculty").get("/api/v1/rspc/proposals/")

    assert after.status_code == 200


@pytest.mark.django_db
def test_tc_br_052_role_assignment_outside_authorized_mechanism_not_applied(stub_iam):
    """TC-BR-052 / BR-RSPC-053 unauthorized source.

    A role claimed in request headers and body, not by the identity session, is ignored.
    """
    client = _client(
        stub_iam, 10, None, HTTP_X_ACTIVE_ROLE="faculty", HTTP_X_ROLES="faculty"
    )

    resp = client.post(
        "/api/v1/rspc/proposals/",
        data={**_proposal_payload(), "roles": ["faculty"], "active_role": "faculty"},
        format="json",
    )

    assert resp.status_code == 403
    assert Proposal.objects.count() == 0


@pytest.mark.django_db
def test_tc_br_053_authorized_reassignment_applied(stub_iam):
    """TC-BR-053 / BR-RSPC-054 authorized mechanism (role A faculty -> role B Dean-RSPC)."""
    prop = _proposal(status="endorsed_hod", user_id=10)
    url = f"/api/v1/rspc/proposals/{prop.id}/approve/"
    assert _client(stub_iam, 100, "faculty").post(url).status_code == 403

    resp = _client(stub_iam, 100, "Dean (RSPC)").post(url, data={"comments": "ok"}, format="json")

    assert resp.status_code == 200
    prop.refresh_from_db()
    assert prop.status == "approved_dean"


@pytest.mark.django_db
def test_tc_br_054_reassignment_outside_authorized_mechanism_not_applied(stub_iam):
    """TC-BR-054 / BR-RSPC-054 unauthorized source (faculty claims Dean-RSPC in the request)."""
    prop = _proposal(status="endorsed_hod", user_id=10)
    client = _client(
        stub_iam,
        100,
        "faculty",
        HTTP_X_ACTIVE_ROLE="Dean (RSPC)",
        HTTP_X_ROLES="Dean (RSPC)",
    )

    resp = client.post(
        f"/api/v1/rspc/proposals/{prop.id}/approve/",
        data={"comments": "ok", "roles": ["Dean (RSPC)"], "active_role": "Dean (RSPC)"},
        format="json",
    )

    assert resp.status_code == 403
    prop.refresh_from_db()
    assert prop.status == "endorsed_hod"
    assert prop.reviews.count() == 0


@pytest.mark.django_db
def test_tc_br_055_new_role_effective_immediately(stub_iam):
    """TC-BR-055 / BR-RSPC-055 immediate effect on assignment."""
    assert _client(stub_iam, 10, None).post(
        "/api/v1/rspc/proposals/", data=_proposal_payload(), format="json"
    ).status_code == 403

    resp = _client(stub_iam, 10, "faculty").post(
        "/api/v1/rspc/proposals/", data=_proposal_payload(), format="json"
    )

    assert resp.status_code == 201
    assert Proposal.objects.filter(user_id=10).count() == 1


@pytest.mark.django_db
def test_tc_br_056_reassignment_effective_immediately(stub_iam):
    """TC-BR-056 / BR-RSPC-055 immediate effect on reassignment.

    Role A (faculty) -> role B (Dean-RSPC). Creating a proposal is faculty-only; approving is
    Dean-only.
    """
    prop = _proposal(status="endorsed_hod", user_id=10)
    faculty_ok = _client(stub_iam, 100, "faculty").post(
        "/api/v1/rspc/proposals/", data=_proposal_payload(), format="json"
    )
    assert faculty_ok.status_code == 201

    dean = _client(stub_iam, 100, "Dean (RSPC)")
    role_a_only = dean.post(
        "/api/v1/rspc/proposals/", data=_proposal_payload(), format="json"
    )
    role_b = dean.post(
        f"/api/v1/rspc/proposals/{prop.id}/approve/", data={"comments": "ok"}, format="json"
    )

    assert role_a_only.status_code == 403
    assert Proposal.objects.filter(user_id=100).count() == 1
    assert role_b.status_code == 200


@pytest.mark.skip(reason=NO_EXTERNAL_EXEC)
def test_tc_br_057_no_hr_payroll_execution():
    """TC-BR-057 / BR-RSPC-058 no HR/payroll execution."""


@pytest.mark.skip(reason=NO_EXTERNAL_EXEC)
def test_tc_br_058_no_accounting_bank_execution():
    """TC-BR-058 / BR-RSPC-059 no accounting/bank execution."""


@pytest.mark.skip(reason=NO_EXTERNAL_EXEC)
def test_tc_br_059_no_procurement_inventory_execution():
    """TC-BR-059 / BR-RSPC-060 no procurement/inventory execution."""


@pytest.mark.skip(reason=NO_EXTERNAL_EXEC)
def test_tc_br_060_notification_triggered_on_rspc_event():
    """TC-BR-060 / BR-RSPC-061 notification triggered."""
