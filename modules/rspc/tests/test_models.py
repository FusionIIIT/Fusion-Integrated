from decimal import Decimal

import pytest
from django.db import IntegrityError

from modules.rspc.models import (
    ConsultancyProject,
    FundRequest,
    ProjectStaffAppointment,
    ResearchProposal,
)

pytestmark = pytest.mark.django_db


def make_proposal(**overrides) -> ResearchProposal:
    data = {
        "title": "Low-power edge inference",
        "faculty_user_id": 101,
        "department": "CSE",
        "funding_agency": "SERB",
        "proposed_budget": Decimal("1500000.00"),
        "duration_months": 24,
        "objectives": "Study quantised models on microcontrollers.",
    }
    return ResearchProposal.objects.create(**{**data, **overrides})


def test_proposal_defaults_to_draft():
    assert make_proposal().status == ResearchProposal.Status.DRAFT


def test_proposal_holds_faculty_as_plain_id_not_fk():
    field = ResearchProposal._meta.get_field("faculty_user_id")
    assert not field.is_relation
    assert make_proposal(faculty_user_id=7).faculty_user_id == 7


def test_consultancy_defaults_and_str():
    project = ConsultancyProject.objects.create(
        title="Bridge audit",
        faculty_user_id=102,
        client_name="PWD",
        financial_terms=Decimal("250000.00"),
        deliverables="Audit report",
        start_date="2026-01-01",
        end_date="2026-06-30",
    )
    assert project.status == ConsultancyProject.Status.SUBMITTED
    assert str(project) == "Bridge audit - PWD"


def test_staff_appointment_defaults_and_cascade():
    proposal = make_proposal()
    appt = ProjectStaffAppointment.objects.create(
        proposal=proposal, position_title="JRF", stipend=Decimal("37000.00"), duration_months=12
    )
    assert appt.status == ProjectStaffAppointment.Status.REQUESTED
    assert appt.candidate_name == ""
    proposal.delete()
    assert not ProjectStaffAppointment.objects.filter(pk=appt.pk).exists()


def test_fund_request_defaults_and_related_name():
    proposal = make_proposal()
    FundRequest.objects.create(
        proposal=proposal, requested_amount=Decimal("50000.00"), purpose="Equipment"
    )
    request = proposal.fund_requests.get()
    assert request.status == FundRequest.Status.SUBMITTED


def test_staff_appointment_requires_a_proposal():
    with pytest.raises(IntegrityError):
        ProjectStaffAppointment.objects.create(
            proposal_id=None, position_title="SRF", stipend=Decimal("42000.00"), duration_months=6
        )


def test_status_vocabularies_follow_the_approval_chain():
    assert [c.value for c in ResearchProposal.Status] == [
        "draft", "submitted", "hod_approved", "admin_verified",
        "dean_approved", "director_approved", "rejected",
    ]
    assert "director_approved" not in ConsultancyProject.Status.values
