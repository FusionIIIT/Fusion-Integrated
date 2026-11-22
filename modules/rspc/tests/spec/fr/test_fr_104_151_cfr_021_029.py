"""Spec tests for strategy FR, module rspc: CFR-021 to CFR-029 (notifications, integration, roles, scope, updates, admin).

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
    Proposal,
)
from modules.rspc.registry import ROLE_GRANTS
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
def test_tc_fr_123(stub_iam):
    """TC-FR-123 | source RSPC-FR-086 (parent RSPC-CFR-023) | RBAC enforced for project data (BR-RSPC-048)

    Action: Each requests project data
    Expected: Permitted role gets data; others denied
    """

    project = _project(F1, "RSPC/FR/123", status="active")
    owner = _as(stub_iam, F1, "faculty")
    assert owner.get(f"{URL}/projects/{project.id}/").status_code == 200
    other = _as(stub_iam, F2, "faculty")
    assert other.get(f"{URL}/projects/{project.id}/").status_code == 404
    session = make_session(
        user_id=F1, permissions=ROLE_GRANTS["faculty"], modules=("placement_cell",),
        kind="faculty", roles=("faculty",), active_role="faculty",
    )
    no_grant = _client_for(stub_iam, session)
    assert no_grant.get(f"{URL}/projects/{project.id}/").status_code == 403


@pytest.mark.django_db
def test_tc_fr_124(stub_iam):
    """TC-FR-124 | source RSPC-FR-087 | Users restricted to actions permitted by RSPC roles (BR-RSPC-049)

    Action: Attempt an action reserved for Dean-RSPC
    Expected: Action denied
    """

    prop = _endorsed(F1, "sponsored_research", "Research proposal")
    client = _as(stub_iam, F2, "faculty")
    resp = client.post(f"{URL}/proposals/{prop.id}/approve/", data={}, format="json")
    assert resp.status_code == 403
    prop.refresh_from_db()
    assert prop.status == "endorsed_hod"
    assert prop.reviews.filter(action="approve").count() == 0


@pytest.mark.django_db
def test_tc_fr_125(stub_iam):
    """TC-FR-125 | source RSPC-FR-101 | RSPC does not own authentication or RBAC administration (BR-RSPC-063)

    Action: Look for RSPC functions for authentication or role administration
    Expected: None exist beyond RSPC role/action restrictions
    """

    from modules.rspc.api import urls as rspc_urls

    routes = [str(p.pattern).lower() for p in rspc_urls.urlpatterns]
    forbidden = ("login", "logout", "password", "token", "session", "signin", "role", "auth")
    offending = [r for r in routes if any(word in r for word in forbidden)]
    assert offending == []
    assert routes  # the module does expose its own (non-auth) endpoints






@pytest.mark.django_db
def test_tc_fr_128(stub_iam):
    """TC-FR-128 | source RSPC-FR-093 | Role changes effective immediately (BR-RSPC-055)

    Action: Reassign role, U immediately retries actions
    Expected: New role permissions apply at once; old ones denied
    """

    prop = _endorsed(F2, "sponsored_research", "Research proposal", hod_id=HOD)
    user = 10
    # Before reassignment: the user is Faculty (may create, may not approve).
    old = _as(stub_iam, user, "faculty")
    assert old.post(f"{URL}/proposals/", data=_payload(), format="json").status_code == 201
    assert old.post(f"{URL}/proposals/{prop.id}/approve/", data={}, format="json").status_code == 403
    # Reassigned to Dean (RSPC): the very next requests use the new role.
    new = _as(stub_iam, user, "Dean (RSPC)")
    created = new.post(f"{URL}/proposals/", data=_payload(), format="json")
    assert created.status_code == 403
    assert Proposal.objects.filter(user_id=user).count() == 1
    approved = new.post(f"{URL}/proposals/{prop.id}/approve/", data={}, format="json")
    assert approved.status_code == 200
    assert approved.data["status"] == "approved_dean"














































