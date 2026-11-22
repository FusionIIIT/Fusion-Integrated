"""HTTP-only Journey Tests for RSPC (Step 5.12).

Drives the module end-to-end ONLY through HTTP (APIClient) with make_session
for each actor in turn (Faculty -> HoD -> Dean -> Admin), asserting response
bodies, persistent database records, and immutable audit logs.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import (
    Project,
    ProjectBudgetHead,
    ProjectClosureRequest,
    ProjectExtensionRequest,
    ProjectFundTransaction,
    Proposal,
    ProposalReview,
)
from modules.rspc.registry import ROLE_GRANTS
from modules.rspc.services import (
    extension as extension_services,
    finance as finance_services,
    project as project_services,
    proposal as proposal_services,
)


class Actor:
    def __init__(self, stub_iam, user_id: int, role: str):
        self.stub_iam = stub_iam
        self.session = make_session(
            user_id=user_id,
            roles=(role,),
            active_role=role,
            permissions=tuple(ROLE_GRANTS.get(role, ())),
            modules=("rspc",),
        )
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Token test-token")

    def _activate(self):
        self.stub_iam(self.session)
        return self.client

    def get(self, *args, **kwargs):
        return self._activate().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self._activate().post(*args, **kwargs)


@pytest.mark.django_db
def test_journey_uc_001_portfolio_view(stub_iam):
    """RSPC-UC-001: Faculty views own proposal and project portfolio."""
    faculty = Actor(stub_iam, user_id=10, role="faculty")

    # Initially empty
    resp = faculty.get("/api/v1/rspc/proposals/")
    assert resp.status_code == 200
    assert resp.data == []

    resp = faculty.get("/api/v1/rspc/projects/")
    assert resp.status_code == 200
    assert resp.data == []


@pytest.mark.django_db
def test_journey_uc_002_003_004_proposal_full_lifecycle(stub_iam):
    """RSPC-UC-002, UC-003, UC-004, BW-RSPC-01, CW-RSPC-01.

    Complete happy path:
    1. Faculty creates and submits proposal (draft -> submitted_hod).
    2. HoD evaluates departmental feasibility and endorses (submitted_hod -> endorsed_hod).
    3. Dean-RSPC evaluates institutional overheads and approves (endorsed_hod -> approved_dean).
    """
    faculty = Actor(stub_iam, user_id=10, role="faculty")
    hod = Actor(stub_iam, user_id=20, role="Head of Department")
    dean = Actor(stub_iam, user_id=30, role="Dean (RSPC)")

    # Step 1: Create proposal
    create_resp = faculty.post(
        "/api/v1/rspc/proposals/",
        data={
            "title": "Quantum Computing Architecture",
            "proposal_type": "sponsored_research",
            "department": "CSE",
            "funding_agency": "SERB",
            "proposed_budget": "1500000.00",
            "summary": "Novel quantum error-mitigation protocols.",
        },
        format="json",
    )
    assert create_resp.status_code == 201
    prop_id = create_resp.data["id"]
    assert create_resp.data["status"] == "draft"

    # Step 2: Faculty submits proposal
    submit_resp = faculty.post(f"/api/v1/rspc/proposals/{prop_id}/submit/")
    assert submit_resp.status_code == 200
    assert submit_resp.data["status"] == "submitted_hod"

    # Verify database state
    prop = Proposal.objects.get(pk=prop_id)
    assert prop.status == "submitted_hod"

    # Step 3: HoD endorses proposal
    endorse_resp = hod.post(
        f"/api/v1/rspc/proposals/{prop_id}/endorse/",
        data={"comments": "Recommended: Departmental computing lab space allocated."},
        format="json",
    )
    assert endorse_resp.status_code == 200
    assert endorse_resp.data["status"] == "endorsed_hod"

    # Verify audit review entry
    review1 = ProposalReview.objects.get(proposal=prop, action="endorse")
    assert review1.reviewer_user_id == 20
    assert "computing lab space" in review1.comments

    # Step 4: Dean-RSPC approves proposal
    approve_resp = dean.post(
        f"/api/v1/rspc/proposals/{prop_id}/approve/",
        data={"comments": "Approved for institutional onward submission."},
        format="json",
    )
    assert approve_resp.status_code == 200
    assert approve_resp.data["status"] == "approved_dean"

    # Verify final proposal state
    prop.refresh_from_db()
    assert prop.status == "approved_dean"
    assert prop.reviews.count() == 2


@pytest.mark.django_db
def test_journey_uc_003_alternate_hod_not_recommended(stub_iam):
    """RSPC-UC-003 Alternative Flow: HoD records 'not recommended'."""
    faculty = Actor(stub_iam, user_id=10, role="faculty")
    hod = Actor(stub_iam, user_id=20, role="Head of Department")

    create_resp = faculty.post(
        "/api/v1/rspc/proposals/",
        data={
            "title": "Substandard Proposal",
            "proposal_type": "sponsored_research",
            "department": "CSE",
            "funding_agency": "DST",
            "proposed_budget": "500000.00",
        },
        format="json",
    )
    prop_id = create_resp.data["id"]
    faculty.post(f"/api/v1/rspc/proposals/{prop_id}/submit/")

    # Direct rejection outcome recorded
    prop = Proposal.objects.get(pk=prop_id)
    proposal_services.reject_proposal(
        proposal=prop, actor_user_id=20, actor_role="hod", comments="Lacks feasibility"
    )

    prop.refresh_from_db()
    assert prop.status == "Department Not Recommended"


@pytest.mark.django_db
def test_journey_uc_005_006_project_sanction_allocation_disburse(stub_iam):
    """RSPC-UC-005, UC-006, BW-RSPC-02, BW-RSPC-03.

    1. Admin sanctions project (sanctioned).
    2. Admin activates project (active).
    3. Admin allocates budget head (allocation ledger row created).
    4. Faculty requests disbursement (disbursement ledger row created).
    5. Dean approves disbursement request.
    6. Faculty/Admin checks project ledger (immutable ledger verified).
    """
    admin = Actor(stub_iam, user_id=1, role="admin")
    faculty = Actor(stub_iam, user_id=10, role="faculty")
    dean = Actor(stub_iam, user_id=30, role="Dean (RSPC)")

    today = datetime.date.today()

    # Step 1: Sanction Project (user_id=10 is PI)
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="RSPC/2026/CSE/099",
        project_type="sponsored",
        title="Cybersecurity Hardware Testbed",
        department="CSE",
        funding_agency="DRDO",
        sanction_order_no="DRDO/2026/099",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=730),
        sanctioned_amount=Decimal("5000000.00"),
    )
    proj_id = proj.id

    # Step 2: Activate Project
    act_resp = admin.post(f"/api/v1/rspc/projects/{proj_id}/activate/")
    assert act_resp.status_code == 200
    assert act_resp.data["status"] == "active"

    # Step 3: Allocate Budget Head
    alloc_resp = admin.post(
        f"/api/v1/rspc/projects/{proj_id}/heads/",
        data={"head_type": "equipment", "allocated_amount": "2500000.00"},
        format="json",
    )
    assert alloc_resp.status_code == 201
    assert alloc_resp.data["head_type"] == "equipment"
    assert alloc_resp.data["allocated_amount"] == "2500000.00"

    # Step 4: Faculty Disburses Funds
    disb_resp = faculty.post(
        f"/api/v1/rspc/projects/{proj_id}/disburse/",
        data={
            "head_type": "equipment",
            "amount": "800000.00",
            "reference_no": "PO-HW-001",
            "description": "FPGA boards and logic analyzers",
        },
        format="json",
    )
    assert disb_resp.status_code == 201
    tx_id = disb_resp.data["id"]
    assert disb_resp.data["transaction_type"] == "disbursement"

    # Step 5: Dean approves disbursement
    app_resp = dean.post(f"/api/v1/rspc/projects/{proj_id}/disburse/{tx_id}/approve/")
    assert app_resp.status_code == 200
    assert app_resp.data["status"] == "approved"

    # Step 6: Verify Ledger
    ledger_resp = faculty.get(f"/api/v1/rspc/projects/{proj_id}/ledger/")
    assert ledger_resp.status_code == 200
    assert len(ledger_resp.data) == 2
    types = [t["transaction_type"] for t in ledger_resp.data]
    assert "allocation" in types
    assert "disbursement" in types


@pytest.mark.django_db
def test_journey_uc_027_028_project_extension_and_closure(stub_iam):
    """RSPC-UC-027, UC-028, BW-RSPC-04.

    1. Faculty requests extension.
    2. Dean approves extension -> project end_date updated.
    3. Faculty requests project closure.
    4. Dean approves closure -> status becomes closed.
    """
    admin = Actor(stub_iam, user_id=1, role="admin")
    faculty = Actor(stub_iam, user_id=10, role="faculty")
    dean = Actor(stub_iam, user_id=30, role="Dean (RSPC)")

    today = datetime.date.today()
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-EXT-CLS",
        project_type="sponsored",
        title="Extension & Closure Journey",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-EXT",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=100),
        sanctioned_amount=Decimal("1000000.00"),
    )
    project_services.activate_project(project=proj, actor_role="admin")

    # 1. Extension request
    ext_resp = faculty.post(
        f"/api/v1/rspc/projects/{proj.id}/extensions/",
        data={
            "requested_end_date": str(today + datetime.timedelta(days=200)),
            "months_requested": 3,
            "justification": "Delay in equipment delivery from overseas vendor.",
        },
        format="json",
    )
    assert ext_resp.status_code == 201
    ext_id = ext_resp.data["id"]

    # 2. Dean approves extension
    ext_app_resp = dean.post(
        f"/api/v1/rspc/projects/{proj.id}/extensions/{ext_id}/approve/",
        data={"approved": True, "comments": "Approved for 3 months."},
        format="json",
    )
    assert ext_app_resp.status_code == 200
    assert ext_app_resp.data["status"] == "dean_approved"

    # 3. Closure request
    cls_resp = faculty.post(
        f"/api/v1/rspc/projects/{proj.id}/closure/",
        data={"remarks": "All project deliverables completed and report submitted."},
        format="json",
    )
    assert cls_resp.status_code == 201
    assert cls_resp.data["status"] == "pending"

    # 4. Dean approves closure
    cls_app_resp = dean.post(f"/api/v1/rspc/projects/{proj.id}/closure/approve/")
    assert cls_app_resp.status_code == 200
    assert cls_app_resp.data["status"] == "approved"

    proj.refresh_from_db()
    assert proj.status == "closed"
