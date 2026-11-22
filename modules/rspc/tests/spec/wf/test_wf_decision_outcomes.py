"""WF decision outcomes (TC-WF-013..034)."""

from decimal import Decimal

import pytest

from modules.rspc.models import Proposal
from modules.rspc.services import proposal as proposal_services

REASON = (
    "NOT_AUTOMATED: the state and actor action named in this case do not exist in "
    "the implemented RSPC state machines, and no API or service interface can drive "
    "the request to the precondition state"
)


@pytest.mark.django_db
def test_tc_wf_013():
    """TC-WF-013 | source_id: CW-RSPC-01 row 3 (Not recommended)."""
    proposal = proposal_services.create_proposal(
        user_id=10,
        title="WF-013 proposal",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="SERB",
        proposed_budget=Decimal("1000000.00"),
    )
    proposal_services.submit_proposal(proposal=proposal, actor_user_id=10)
    proposal.refresh_from_db()
    assert proposal.status == "submitted_hod"  # 'Proposal Submitted'

    # HoD (user 20, not the PI) records the "not recommended" outcome.
    proposal_services.reject_proposal(
        proposal=proposal, actor_user_id=20, actor_role="hod", comments="Not recommended"
    )

    proposal = Proposal.objects.get(pk=proposal.pk)
    # Spec: state becomes 'Department Not Recommended' (not a success state).
    assert proposal.status == "Department Not Recommended"
    assert proposal.status not in ("endorsed_hod", "approved_dean")











































