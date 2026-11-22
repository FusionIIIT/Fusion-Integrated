"""Spec tests TC-BR-001 .. TC-BR-020 (routing, submission validation, decision records)."""

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import Proposal, ProposalReview
from modules.rspc.registry import ROLE_GRANTS
from modules.rspc.services import proposal as proposal_services

NO_DIRECTOR_STAGE = (
    "NOT_AUTOMATED: the implementation has no Director review stage, no RSPC Admin review "
    "stage and no Director action endpoint (proposal path is draft -> submitted_hod -> "
    "endorsed_hod -> approved_dean only), so this behaviour cannot be exercised"
)
NO_APPOINTMENT = (
    "NOT_AUTOMATED: the implementation has no appointment-request or consultancy-record "
    "routing interface with a Director stage"
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


def _proposal(status="draft", user_id=10, proposal_type="sponsored_research", **kw):
    fields = {
        "user_id": user_id,
        "title": "Thermal Fluid Dynamics",
        "proposal_type": proposal_type,
        "department": "ME",
        "funding_agency": "DST",
        "proposed_budget": Decimal("1500000.00"),
        "status": status,
        "summary": "Objectives, timelines and resources.",
    }
    fields.update(kw)
    return Proposal.objects.create(**fields)


def _url(prop, action):
    return f"/api/v1/rspc/proposals/{prop.id}/{action}/"




@pytest.mark.django_db
def test_tc_br_002_dean_handles_request_without_director_stage(stub_iam):
    """TC-BR-002 / BR-RSPC-004 condition-false (Director not required)."""
    prop = _proposal(status="endorsed_hod")
    dean = _client(stub_iam, 100, "Dean (RSPC)")

    resp = dean.post(_url(prop, "approve"), data={"comments": "Done"}, format="json")

    assert resp.status_code == 200
    prop.refresh_from_db()
    assert prop.status == "approved_dean"
    roles = set(prop.reviews.values_list("reviewer_role", flat=True))
    assert roles == {"Dean (RSPC)"}
    assert all("director" not in s.lower() for s, _ in Proposal.STATUS_CHOICES)














@pytest.mark.django_db
def test_tc_br_009_stage_order_enforced(stub_iam):
    """TC-BR-009 / BR-RSPC-012 stage order enforced.

    A conflicting-state refusal carries 409 (api-conventions, Status codes).
    """
    prop = _proposal(status="submitted_hod")
    dean = _client(stub_iam, 100, "Dean (RSPC)")

    resp = dean.post(_url(prop, "approve"), data={"comments": "skip ahead"}, format="json")

    assert resp.status_code == 409
    prop.refresh_from_db()
    assert prop.status == "submitted_hod"
    assert prop.reviews.count() == 0


@pytest.mark.django_db
def test_tc_br_010_incomplete_proposal_rejected_on_submit(stub_iam):
    """TC-BR-010 / BR-RSPC-013 condition-false (incomplete).

    Mandatory field (funding agency) is empty. Validation refusal carries 422.
    """
    prop = _proposal(status="draft", funding_agency="")
    faculty = _client(stub_iam, 10, "faculty")

    resp = faculty.post(_url(prop, "submit"))

    assert resp.status_code == 422
    prop.refresh_from_db()
    assert prop.status == "draft"


@pytest.mark.django_db
def test_tc_br_011_complete_proposal_advances_on_submit(stub_iam):
    """TC-BR-011 / BR-RSPC-013 condition-true (complete)."""
    prop = _proposal(
        status="draft",
        overhead_amount=Decimal("100000.00"),
        submission_deadline=datetime.date.today() + datetime.timedelta(days=30),
    )
    faculty = _client(stub_iam, 10, "faculty")

    resp = faculty.post(_url(prop, "submit"))

    assert resp.status_code == 200
    assert resp.data["status"] == "submitted_hod"
    prop.refresh_from_db()
    assert prop.status == "submitted_hod"


@pytest.mark.django_db
def test_tc_br_012_represented_validation_fails(stub_iam):
    """TC-BR-012 / BR-RSPC-014 represented validation fails.

    The represented validation is the positive-budget rule on a proposal.
    Validation refusal carries 422; nothing is created, so nothing can advance.
    """
    faculty = _client(stub_iam, 10, "faculty")
    payload = {
        "title": "Zero budget proposal",
        "proposal_type": "sponsored_research",
        "department": "CSE",
        "funding_agency": "SERB",
        "proposed_budget": "0.00",
    }

    resp = faculty.post("/api/v1/rspc/proposals/", data=payload, format="json")

    assert resp.status_code == 422
    assert Proposal.objects.count() == 0


@pytest.mark.django_db
def test_tc_br_013_represented_validation_passes(stub_iam):
    """TC-BR-013 / BR-RSPC-014 represented validation passes."""
    faculty = _client(stub_iam, 10, "faculty")
    payload = {
        "title": "Compliant proposal",
        "proposal_type": "sponsored_research",
        "department": "CSE",
        "funding_agency": "SERB",
        "proposed_budget": "250000.00",
    }

    created = faculty.post("/api/v1/rspc/proposals/", data=payload, format="json")
    assert created.status_code == 201
    resp = faculty.post(_url(Proposal(id=created.data["id"]), "submit"))

    assert resp.status_code == 200
    assert Proposal.objects.get(pk=created.data["id"]).status == "submitted_hod"


@pytest.mark.django_db
def test_tc_br_014_no_represented_validation_no_policy_rejection(stub_iam):
    """TC-BR-014 / BR-RSPC-014 no represented validation.

    No optional policy field (overhead, deadline) is set; the proposal is otherwise complete.
    """
    prop = _proposal(status="draft", overhead_amount=Decimal("0.00"), submission_deadline=None)
    faculty = _client(stub_iam, 10, "faculty")

    resp = faculty.post(_url(prop, "submit"))

    assert resp.status_code == 200
    prop.refresh_from_db()
    assert prop.status == "submitted_hod"


@pytest.mark.django_db
def test_tc_br_015_decision_records_carry_timestamp():
    """TC-BR-015 / BR-RSPC-015 timestamp recorded (approve, then reject on another proposal)."""
    approve_target = _proposal(status="endorsed_hod", user_id=10)
    reject_target = _proposal(status="submitted_hod", user_id=11)
    before = timezone.now()

    proposal_services.approve_proposal(proposal=approve_target, actor_user_id=100)
    proposal_services.reject_proposal(
        proposal=reject_target, actor_user_id=50, actor_role="hod", comments="No"
    )

    after = timezone.now()
    for prop, action in ((approve_target, "approve"), (reject_target, "reject")):
        review = ProposalReview.objects.get(proposal=prop)
        assert review.action == action
        assert review.created_at is not None
        assert before <= review.created_at <= after


@pytest.mark.django_db
def test_tc_br_016_decision_remarks_recorded(stub_iam):
    """TC-BR-016 / BR-RSPC-016 remarks recorded."""
    prop = _proposal(status="submitted_hod")
    hod = _client(stub_iam, 50, "Head of Department")
    remarks = "Methodology sound; budget justified."

    resp = hod.post(_url(prop, "endorse"), data={"comments": remarks}, format="json")

    assert resp.status_code == 200
    review = ProposalReview.objects.get(proposal=prop)
    assert review.comments == remarks




@pytest.mark.django_db
def test_tc_br_018_consultancy_enters_only_applicable_stages(stub_iam):
    """TC-BR-018 / BR-RSPC-022 conditional stages not applicable.

    Consultancy record advances through HoD and Dean-RSPC only; no Director stage is entered.
    """
    prop = _proposal(status="draft", proposal_type="consultancy")

    r1 = _client(stub_iam, 10, "faculty").post(_url(prop, "submit"))
    r2 = _client(stub_iam, 50, "Head of Department").post(_url(prop, "endorse"))
    r3 = _client(stub_iam, 100, "Dean (RSPC)").post(_url(prop, "approve"))

    assert (r1.status_code, r2.status_code, r3.status_code) == (200, 200, 200)
    prop.refresh_from_db()
    assert prop.status == "approved_dean"
    roles = list(prop.reviews.order_by("id").values_list("reviewer_role", flat=True))
    assert roles == ["Head of Department", "Dean (RSPC)"]




