"""Spec tests TC-BR-061 .. TC-BR-078 (external boundaries, role enforcement, stage decisions)."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import Project, ProjectFundTransaction, Proposal, ProposalReview
from modules.rspc.registry import ROLE_GRANTS
from modules.rspc.services import proposal as proposal_services

NO_NOTIFICATION = (
    "NOT_AUTOMATED: the implementation has no notification event or delivery interface "
    "(no notification record is created and no email channel is called)"
)
NO_AGENCY = (
    "NOT_AUTOMATED: the implementation has no external-agency submission or disbursement "
    "status model or intake interface"
)
NO_UPDATE = (
    "NOT_AUTOMATED: the implementation has no endpoint to update project details, "
    "milestones, progress or utilization (project API is create, read, activate only)"
)
NO_ADMIN_STAGE = (
    "NOT_AUTOMATED: the implementation has no RSPC Admin verification/forwarding stage "
    "and no eligibility outcome"
)
NO_DIRECTOR_STAGE = (
    "NOT_AUTOMATED: the implementation has no Director routing condition, Director stage "
    "or Dean-RSPC authority limit"
)
NO_POLICY_CONFIG = (
    "NOT_AUTOMATED: the implementation has no configurable policy or threshold, represented "
    "or unrepresented; rules are fixed in code"
)


def _client(stub_iam, user_id, role):
    session = make_session(
        user_id=user_id,
        kind="faculty",
        roles=(role,),
        active_role=role,
        permissions=ROLE_GRANTS[role],
        modules=("rspc",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


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


@pytest.mark.skip(reason=NO_NOTIFICATION)
def test_tc_br_061_email_delivery_failure_leaves_event_intact():
    """TC-BR-061 / BR-RSPC-061 delivery failure."""


@pytest.mark.skip(reason=NO_AGENCY)
def test_tc_br_062_external_agency_information_stored_not_executed():
    """TC-BR-062 / BR-RSPC-062 external agency info."""


@pytest.mark.django_db
def test_tc_br_063_no_agency_execution_capability(stub_iam):
    """TC-BR-063 / BR-RSPC-062 unrepresented info.

    No agency decision, submission or disbursement endpoint exists; attempts execute nothing.
    """
    dean = _client(stub_iam, 100, "Dean (RSPC)")

    statuses = [
        dean.post(f"/api/v1/rspc/agency/{action}/", data={}, format="json").status_code
        for action in ("decision", "submission", "disbursement")
    ]

    assert statuses == [404, 404, 404]
    assert Proposal.objects.count() == 0
    assert Project.objects.count() == 0
    assert ProjectFundTransaction.objects.count() == 0


@pytest.mark.django_db
def test_tc_br_064_no_platform_administration_in_rspc(stub_iam):
    """TC-BR-064 / BR-RSPC-063 no platform admin.

    RSPC exposes no user-account or platform-wide role creation.
    """
    admin = _client(stub_iam, 1, "admin")

    body = {"username": "new", "role": "admin"}
    statuses = [
        admin.post(f"/api/v1/rspc/{path}/", data=body, format="json").status_code
        for path in ("users", "accounts", "roles")
    ]

    assert statuses == [404, 404, 404]


@pytest.mark.django_db
def test_tc_br_065_restrictions_applied_per_supplied_role(stub_iam):
    """TC-BR-065 / BR-RSPC-063 enforces supplied role info."""
    prop = _proposal(status="submitted_hod", user_id=10)
    url = f"/api/v1/rspc/proposals/{prop.id}/endorse/"

    as_faculty = _client(stub_iam, 11, "faculty").post(url, data={}, format="json")
    prop.refresh_from_db()
    assert as_faculty.status_code == 403
    assert prop.status == "submitted_hod"

    as_hod = _client(stub_iam, 50, "Head of Department").post(url, data={}, format="json")

    assert as_hod.status_code == 200
    prop.refresh_from_db()
    assert prop.status == "endorsed_hod"


@pytest.mark.skip(reason=NO_UPDATE)
def test_tc_br_066_update_permitted_by_lifecycle_state():
    """TC-BR-066 / BR-RSPC-065 update permitted by lifecycle."""


@pytest.mark.skip(reason=NO_UPDATE)
def test_tc_br_067_update_not_permitted_for_closed_project():
    """TC-BR-067 / BR-RSPC-065 update not permitted."""


@pytest.mark.skip(reason=NO_ADMIN_STAGE)
def test_tc_br_068_rspc_admin_forwards_eligible_outcome():
    """TC-BR-068 / BR-RSPC-066 eligible outcome."""


@pytest.mark.skip(reason=NO_ADMIN_STAGE)
def test_tc_br_069_rspc_admin_cannot_forward_ineligible_outcome():
    """TC-BR-069 / BR-RSPC-066 ineligible outcome."""


@pytest.mark.django_db
def test_tc_br_070_hod_recommended_advances_request(stub_iam):
    """TC-BR-070 / BR-RSPC-067 recommended."""
    prop = _proposal(status="submitted_hod")

    resp = _client(stub_iam, 50, "Head of Department").post(
        f"/api/v1/rspc/proposals/{prop.id}/endorse/", data={"comments": "Recommended"},
        format="json",
    )

    assert resp.status_code == 200
    prop.refresh_from_db()
    assert prop.status == "endorsed_hod"


@pytest.mark.django_db
def test_tc_br_071_hod_not_recommended_recorded_not_forwarded():
    """TC-BR-071 / BR-RSPC-067 not recommended.

    The HoD not-recommended decision is the reject event, which is service-only (no endpoint).
    """
    prop = _proposal(status="submitted_hod")

    proposal_services.reject_proposal(
        proposal=prop, actor_user_id=50, actor_role="hod", comments="Not recommended"
    )

    prop.refresh_from_db()
    assert prop.status == "rejected"
    assert prop.status != "endorsed_hod"
    review = ProposalReview.objects.get(proposal=prop)
    assert review.action == "reject"
    assert review.comments == "Not recommended"


@pytest.mark.django_db
def test_tc_br_072_dean_approves_request_within_authority(stub_iam):
    """TC-BR-072 / BR-RSPC-068 within authority."""
    prop = _proposal(status="endorsed_hod")

    resp = _client(stub_iam, 100, "Dean (RSPC)").post(
        f"/api/v1/rspc/proposals/{prop.id}/approve/", data={"comments": "ok"}, format="json"
    )

    assert resp.status_code == 200
    prop.refresh_from_db()
    assert prop.status == "approved_dean"
    assert ProposalReview.objects.filter(proposal=prop, action="approve").count() == 1


@pytest.mark.skip(reason=NO_DIRECTOR_STAGE)
def test_tc_br_073_dean_approval_outside_authority_not_recorded():
    """TC-BR-073 / BR-RSPC-068 outside authority."""


@pytest.mark.django_db
def test_tc_br_074_dean_approval_of_ineligible_request_not_recorded(stub_iam):
    """TC-BR-074 / BR-RSPC-068 ineligible request.

    A rejected proposal is not eligible for approval. Conflicting state carries 409.
    """
    prop = _proposal(status="rejected")

    resp = _client(stub_iam, 100, "Dean (RSPC)").post(
        f"/api/v1/rspc/proposals/{prop.id}/approve/", data={"comments": "ok"}, format="json"
    )

    assert resp.status_code == 409
    prop.refresh_from_db()
    assert prop.status == "rejected"
    assert prop.reviews.count() == 0


@pytest.mark.skip(reason=NO_DIRECTOR_STAGE)
def test_tc_br_075_director_routing_condition_met_enters_director_stage():
    """TC-BR-075 / BR-RSPC-069 condition met."""


@pytest.mark.skip(reason=NO_DIRECTOR_STAGE)
def test_tc_br_076_director_routing_condition_not_met_no_director_stage():
    """TC-BR-076 / BR-RSPC-069 condition not met."""


@pytest.mark.skip(reason=NO_POLICY_CONFIG)
def test_tc_br_077_represented_policy_applied():
    """TC-BR-077 / BR-RSPC-070 represented policy applied."""


@pytest.mark.skip(reason=NO_POLICY_CONFIG)
def test_tc_br_078_unrepresented_policy_not_applied():
    """TC-BR-078 / BR-RSPC-070 unrepresented policy."""
