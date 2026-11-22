"""Spec tests for strategy FR, module rspc: CFR-006 to CFR-011 (proposals, reviews, consultancy).

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
    ProposalReview,
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
def test_tc_fr_032(stub_iam):
    """TC-FR-032 | source RSPC-FR-015 (parent RSPC-CFR-006) | Faculty can submit a research project proposal (BR-RSPC-013)

    Action: Faculty submits a proposal with all mandatory fields filled
    Expected: The proposal is created and submitted (CW-RSPC-01 T1) and is retrievable
    """

    client = _as(stub_iam, F1, "faculty")
    payload = {
        "title": "Quantum Sensing Testbed",
        "proposal_type": "sponsored_research",
        "department": "CSE",
        "funding_agency": "SERB",
        "proposed_budget": "2500000.00",
        "summary": "Objectives and scope.",
    }
    created = client.post(f"{URL}/proposals/", data=payload, format="json")
    assert created.status_code == 201
    pid = created.data["id"]
    submitted = client.post(f"{URL}/proposals/{pid}/submit/")
    assert submitted.status_code == 200
    assert submitted.data["status"] == "submitted_hod"
    detail = client.get(f"{URL}/proposals/{pid}/")
    assert detail.status_code == 200
    assert detail.data["status"] == "submitted_hod"
    assert detail.data["title"] == "Quantum Sensing Testbed"


@pytest.mark.skip(reason="NOT_AUTOMATED: Proposal has no objectives field (only 'summary'); mapping it would reinterpret the case")
def test_tc_fr_033():
    """TC-FR-033 | source RSPC-FR-016 | Proposal objectives is captured at submission

    Action: Faculty enters objectives text and submits the proposal
    Expected: The entered objectives is persisted on the submitted proposal record
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: Proposal has no start/end date fields (only an optional submission_deadline)')
def test_tc_fr_034():
    """TC-FR-034 | source RSPC-FR-017 | Proposal timeline is captured at submission

    Action: Faculty enters start and end dates and submits the proposal
    Expected: The entered timeline is persisted on the submitted proposal record
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_035(stub_iam):
    """TC-FR-035 | source RSPC-FR-018 | Proposal budget is captured at submission

    Action: Faculty enters budget amount and submits the proposal
    Expected: The entered budget is persisted on the submitted proposal record
    """

    client = _as(stub_iam, F1, "faculty")
    created = client.post(
        f"{URL}/proposals/", data=_payload(proposed_budget="1234567.50"), format="json"
    )
    assert created.status_code == 201
    pid = created.data["id"]
    assert client.post(f"{URL}/proposals/{pid}/submit/").status_code == 200
    assert Proposal.objects.get(pk=pid).proposed_budget == Decimal("1234567.50")
    detail = client.get(f"{URL}/proposals/{pid}/")
    assert detail.data["proposed_budget"] == "1234567.50"


@pytest.mark.django_db
def test_tc_fr_036(stub_iam):
    """TC-FR-036 | source RSPC-FR-019 | Proposal funding source is captured at submission

    Action: Faculty enters funding source and submits the proposal
    Expected: The entered funding source is persisted on the submitted proposal record
    """

    client = _as(stub_iam, F1, "faculty")
    created = client.post(
        f"{URL}/proposals/", data=_payload(funding_agency="ISRO"), format="json"
    )
    assert created.status_code == 201
    pid = created.data["id"]
    assert client.post(f"{URL}/proposals/{pid}/submit/").status_code == 200
    assert Proposal.objects.get(pk=pid).funding_agency == "ISRO"
    assert client.get(f"{URL}/proposals/{pid}/").data["funding_agency"] == "ISRO"


@pytest.mark.skip(reason='NOT_AUTOMATED: Proposal has no resource-requirements field')
def test_tc_fr_037():
    """TC-FR-037 | source RSPC-FR-020 | Proposal resource requirements is captured at submission

    Action: Faculty enters resource requirements and submits the proposal
    Expected: The entered resource requirements is persisted on the submitted proposal record
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no Director stage in any workflow (proposal states stop at Dean approval; Director holds only view/closure grants); no RSPC Admin stage in the proposal state machine (draft, submitted_hod, endorsed_hod, approved_dean)')
def test_tc_fr_038():
    """TC-FR-038 | source RSPC-FR-021 (parent RSPC-CFR-007) | Proposal is routed Faculty-HoD-RSPC Admin-Dean-RSPC-Director (BR-RSPC-012)

    Action: Each actor in turn approves/forwards the proposal
    Expected: The proposal moves in order Faculty, HoD, RSPC Admin, Dean-RSPC, Director and each hand-off state is recorded
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_039(stub_iam):
    """TC-FR-039 | source RSPC-FR-021 Director not applicable | Director stage is used only when applicable

    Action: Proposal is approved at Dean-RSPC
    Expected: The proposal does not require a Director stage and no Director task is created
    """

    prop = _endorsed(F1, "sponsored_research", "Research proposal")
    client = _as(stub_iam, DEAN, "Dean (RSPC)")
    resp = client.post(f"{URL}/proposals/{prop.id}/approve/", data={}, format="json")
    assert resp.status_code == 200
    prop.refresh_from_db()
    # Approved at Dean-RSPC is final: no Director stage/status, no Director review.
    assert prop.status == "approved_dean"
    assert {r.reviewer_role for r in prop.reviews.all()} == {"Head of Department", "Dean (RSPC)"}
    assert not any("director" in s.lower() for s, _ in Proposal.STATUS_CHOICES)


@pytest.mark.django_db
def test_tc_fr_040(stub_iam):
    """TC-FR-040 | source RSPC-FR-022 | Mandatory field validation on research proposals (BR-RSPC-013)

    Action: Submit the proposal with a mandatory field left empty
    Expected: Submission is rejected with a validation error identifying the missing field and the proposal does not advance
    """

    client = _as(stub_iam, F1, "faculty")
    payload = _payload()
    del payload["title"]
    resp = client.post(f"{URL}/proposals/", data=payload, format="json")
    # api-conventions: well-formed but semantically invalid input -> 422.
    assert resp.status_code == 422
    fields = {d["field"] for d in resp.data["error"]["details"]}
    assert "title" in fields
    assert Proposal.objects.count() == 0


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no configurable system-validation policy mechanism for proposals')
def test_tc_fr_041():
    """TC-FR-041 | source RSPC-FR-023 policy represented | Policy validation enforced when represented as system validation (BR-RSPC-014)

    Action: Submit a proposal that violates the policy
    Expected: Submission is rejected/blocked according to the validation and the proposal does not advance
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_042(stub_iam):
    """TC-FR-042 | source RSPC-FR-023 policy not represented | Policy not represented as system validation is not enforced by RSPC

    Action: Submit a proposal otherwise valid
    Expected: No system validation error is raised for that policy and the proposal advances
    """

    client = _as(stub_iam, F1, "faculty")
    created = client.post(f"{URL}/proposals/", data=_payload(), format="json")
    assert created.status_code == 201
    resp = client.post(f"{URL}/proposals/{created.data['id']}/submit/")
    assert resp.status_code == 200
    assert resp.data["status"] == "submitted_hod"


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no Director stage in any workflow (proposal states stop at Dean approval; Director holds only view/closure grants); no RSPC Admin review stage, so decisions of all four reviewers cannot be recorded')
def test_tc_fr_043():
    """TC-FR-043 | source RSPC-FR-024 (parent RSPC-CFR-008) | Proposal approval decisions recorded with timestamps (BR-RSPC-015)

    Action: Each reviewer records a decision
    Expected: Each decision is stored with a timestamp and is retrievable
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_044(stub_iam):
    """TC-FR-044 | source RSPC-FR-025 | Proposal approval decisions recorded with remarks (BR-RSPC-016)

    Action: A reviewer records a decision with remarks
    Expected: The decision is stored with the entered remarks and is retrievable
    """

    prop = _submitted(F1, "sponsored_research", "Research proposal")
    client = _as(stub_iam, HOD, "Head of Department")
    remark = "Budget justified; equipment quote attached."
    resp = client.post(
        f"{URL}/proposals/{prop.id}/endorse/", data={"comments": remark}, format="json"
    )
    assert resp.status_code == 200
    detail = client.get(f"{URL}/proposals/{prop.id}/")
    assert [r["comments"] for r in detail.data["reviews"]] == [remark]
    assert ProposalReview.objects.get(proposal=prop).comments == remark


@pytest.mark.django_db
def test_tc_fr_045(stub_iam):
    """TC-FR-045 | source RSPC-FR-027 (parent RSPC-CFR-009) | Faculty can register a consultancy project

    Action: Faculty submits a consultancy registration
    Expected: The registration is created (CW-RSPC-02 T1) and retrievable
    """

    client = _as(stub_iam, F1, "faculty")
    created = client.post(
        f"{URL}/proposals/", data=_payload(proposal_type="consultancy"), format="json"
    )
    assert created.status_code == 201
    pid = created.data["id"]
    resp = client.post(f"{URL}/proposals/{pid}/submit/")
    assert resp.status_code == 200
    detail = client.get(f"{URL}/proposals/{pid}/")
    assert detail.status_code == 200
    assert detail.data["proposal_type"] == "consultancy"
    assert detail.data["status"] == "submitted_hod"


@pytest.mark.skip(reason='NOT_AUTOMATED: Consultancy registration (a Proposal of type consultancy) has no client-details field')
def test_tc_fr_046():
    """TC-FR-046 | source RSPC-FR-028 | Consultancy client details captured at registration

    Action: Faculty enters client details and registers
    Expected: The entered client details is persisted on the consultancy record
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: Consultancy registration has no scope field')
def test_tc_fr_047():
    """TC-FR-047 | source RSPC-FR-029 | Consultancy scope captured at registration

    Action: Faculty enters scope and registers
    Expected: The entered scope is persisted on the consultancy record
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: Consultancy registration has no deliverables field')
def test_tc_fr_048():
    """TC-FR-048 | source RSPC-FR-030 | Consultancy deliverables captured at registration

    Action: Faculty enters deliverables and registers
    Expected: The entered deliverables is persisted on the consultancy record
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: Consultancy registration has no timeline fields')
def test_tc_fr_049():
    """TC-FR-049 | source RSPC-FR-031 | Consultancy timeline captured at registration

    Action: Faculty enters timeline and registers
    Expected: The entered timeline is persisted on the consultancy record
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: Consultancy registration has no financial-terms field distinct from proposed_budget; mapping would reinterpret the case')
def test_tc_fr_050():
    """TC-FR-050 | source RSPC-FR-032 | Consultancy financial terms captured at registration

    Action: Faculty enters financial terms and registers
    Expected: The entered financial terms is persisted on the consultancy record
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_051(stub_iam):
    """TC-FR-051 | source RSPC-FR-033 (parent RSPC-CFR-010) | Consultancy registration is routed per institutional approval policy (BR-RSPC-022)

    Action: Registration is submitted and approvers act in turn
    Expected: The registration follows the represented approval path only in order and each hand-off is recorded
    """

    prop = _submitted(F1, "consultancy", "Consultancy request")
    hod = _as(stub_iam, HOD, "Head of Department")
    r1 = hod.post(f"{URL}/proposals/{prop.id}/endorse/", data={}, format="json")
    assert (r1.status_code, r1.data["status"]) == (200, "endorsed_hod")
    dean = _as(stub_iam, DEAN, "Dean (RSPC)")
    r2 = dean.post(f"{URL}/proposals/{prop.id}/approve/", data={}, format="json")
    assert (r2.status_code, r2.data["status"]) == (200, "approved_dean")
    reviews = list(prop.reviews.order_by("created_at", "id"))
    assert [(r.action, r.reviewer_user_id) for r in reviews] == [
        ("endorse", HOD),
        ("approve", DEAN),
    ]


@pytest.mark.django_db
def test_tc_fr_052(stub_iam):
    """TC-FR-052 | source RSPC-CFR-010 path not bypassed | Consultancy cannot skip the represented approval path

    Action: An actor attempts to approve at a later stage out of order
    Expected: The action is rejected and the record stays at its current stage
    """

    prop = _submitted(F1, "consultancy", "Consultancy request")
    client = _as(stub_iam, DEAN, "Dean (RSPC)")
    resp = client.post(f"{URL}/proposals/{prop.id}/approve/", data={}, format="json")
    # api-conventions: an illegal state-machine transition is a 409.
    assert resp.status_code == 409
    prop.refresh_from_db()
    assert prop.status == "submitted_hod"
    assert prop.reviews.count() == 0


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no consultancy-payment record or view (the ledger models project fund allocation/disbursement/reversal only)')
def test_tc_fr_053():
    """TC-FR-053 | source RSPC-FR-034 (parent RSPC-CFR-011) | RSPC tracks consultancy payments

    Action: Record and then view consultancy payments
    Expected: Consultancy payments are stored as project records and displayed
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no consultancy-deliverable record or view')
def test_tc_fr_054():
    """TC-FR-054 | source RSPC-FR-035 | RSPC tracks consultancy deliverables

    Action: Record and then view consultancy deliverables
    Expected: Consultancy deliverables are stored as project records and displayed
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no consultancy-settlement record or view')
def test_tc_fr_055():
    """TC-FR-055 | source RSPC-FR-036 | RSPC tracks consultancy settlements

    Action: Record and then view consultancy settlements
    Expected: Consultancy settlements are stored as project records and displayed
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_056(stub_iam):
    """TC-FR-056 | source RSPC-FR-037 | Consultancy financial history maintained for authorized users

    Action: Authorized user opens the financial history
    Expected: Complete financial history is displayed
    """

    project = _project(F1, "RSPC/FR/056", status="active", kind="consultancy")
    _head(project, "consumables", "300000.00")
    tx = finance_services.disburse_funds(
        project=project, head_type="consumables", amount=Decimal("50000.00"),
        reference_no="INV-FR-056", description="Consumables", actor_user_id=F1,
    )
    finance_services.record_reversal_transaction(
        original_transaction_id=tx.id, reversal_amount=Decimal("5000.00"),
        reason="Supplier credit note", actor_user_id=1,
    )
    client = _as(stub_iam, F1, "faculty")
    resp = client.get(f"{URL}/projects/{project.id}/ledger/")
    assert resp.status_code == 200
    rows = {(r["transaction_type"], r["amount"]) for r in resp.data}
    assert rows == {
        ("allocation", "300000.00"),
        ("disbursement", "50000.00"),
        ("reversal", "5000.00"),
    }


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no project history or project approval-history view (only proposal reviews and the fund ledger exist)')
def test_tc_fr_057():
    """TC-FR-057 | source RSPC-FR-038 | Consultancy approval history maintained for authorized users

    Action: Authorized user opens the approval history
    Expected: Complete approval history is displayed
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_058(stub_iam):
    """TC-FR-058 | source RSPC-CFR-011 unauthorized | Consultancy history not available to unauthorized users

    Action: Unauthorized user requests the histories
    Expected: Access is denied
    """

    project = _project(F1, "RSPC/FR/058", status="active", kind="consultancy")
    _head(project, "consumables", "300000.00")
    # A user holding no fund-viewing authority at all.
    session = make_session(
        user_id=77, permissions=(), modules=("rspc",), kind="faculty",
        roles=("faculty",), active_role="faculty",
    )
    client = _client_for(stub_iam, session)
    resp = client.get(f"{URL}/projects/{project.id}/ledger/")
    assert resp.status_code == 403
    # A faculty member with the role but no stake in the project.
    outsider = _as(stub_iam, F2, "faculty")
    assert outsider.get(f"{URL}/projects/{project.id}/ledger/").status_code == 404
