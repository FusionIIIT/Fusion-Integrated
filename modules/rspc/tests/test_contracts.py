"""Tests for RSPC contract interface."""
import pytest
from modules.rspc.contracts import get_project_counts
from modules.rspc.models import ResearchProject, ConsultancyProject
from modules.rspc.domain.state_machine import ProposalStatus, ConsultancyStatus


@pytest.mark.django_db
def test_get_project_counts():
    ResearchProject.objects.create(
        user_id=101, title="Active P1", status=ProposalStatus.SUBMITTED
    )
    ResearchProject.objects.create(
        user_id=101, title="Approved P2", status=ProposalStatus.DEAN_APPROVED
    )
    ConsultancyProject.objects.create(
        user_id=101, title="Active C1", status=ConsultancyStatus.ADMIN_VERIFIED
    )

    counts = get_project_counts([101, 102])
    assert counts[101].active_proposals == 1
    assert counts[101].approved_proposals == 1
    assert counts[101].active_consultancies == 1
    assert counts[101].approved_consultancies == 0

    assert counts[102].active_proposals == 0
    assert counts[102].approved_proposals == 0
