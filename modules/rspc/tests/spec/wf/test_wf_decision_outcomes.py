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


@pytest.mark.skip(reason=REASON)
def test_tc_wf_014():
    """TC-WF-014

    source_id: CW-RSPC-01 row 5 (Verification outcome is not eligible for forwarding)
    """


@pytest.mark.skip(reason=REASON)
def test_tc_wf_015():
    """TC-WF-015 | source_id: CW-RSPC-01 row 8 (Dean-RSPC does not approve)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_016():
    """TC-WF-016 | source_id: CW-RSPC-01 row 10 (Director does not approve)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_017():
    """TC-WF-017 | source_id: CW-RSPC-02 row 3 (Department stage applicable and not recommended)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_018():
    """TC-WF-018

    source_id: CW-RSPC-02 row 4 (Department stage not applicable; verification eligible)
    """


@pytest.mark.skip(reason=REASON)
def test_tc_wf_019():
    """TC-WF-019

    source_id: CW-RSPC-02 row 6 (from Consultancy Submitted)
    (Verification not eligible for forwarding)
    """


@pytest.mark.skip(reason=REASON)
def test_tc_wf_020():
    """TC-WF-020

    source_id: CW-RSPC-02 row 6 (from Department Recommended)
    (Verification not eligible for forwarding)
    """


@pytest.mark.skip(reason=REASON)
def test_tc_wf_021():
    """TC-WF-021 | source_id: CW-RSPC-02 row 9 (Dean-RSPC does not approve)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_022():
    """TC-WF-022 | source_id: CW-RSPC-02 row 11 (Director does not approve)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_023():
    """TC-WF-023 | source_id: CW-RSPC-03 row 3 (Verification not eligible for forwarding)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_024():
    """TC-WF-024 | source_id: CW-RSPC-03 row 7 (Dean-RSPC does not approve)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_025():
    """TC-WF-025 | source_id: CW-RSPC-03 row 9 (Director does not approve)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_026():
    """TC-WF-026 | source_id: CW-RSPC-04 row 3 (Verification not eligible for forwarding)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_027():
    """TC-WF-027 | source_id: CW-RSPC-04 row 6 (Dean-RSPC does not approve)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_028():
    """TC-WF-028 | source_id: CW-RSPC-04 row 8 (Director does not approve/authorize)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_029():
    """TC-WF-029

    source_id: CW-RSPC-05 row 3 (Verification or represented budget validation fails)
    """


@pytest.mark.skip(reason=REASON)
def test_tc_wf_030():
    """TC-WF-030 | source_id: CW-RSPC-05 row 6 (Dean-RSPC does not approve)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_031():
    """TC-WF-031 | source_id: CW-RSPC-05 row 8 (Director does not approve/authorize)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_032():
    """TC-WF-032 | source_id: CW-RSPC-06 row 3 (Verification not eligible for forwarding)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_033():
    """TC-WF-033 | source_id: CW-RSPC-06 row 6 (Dean-RSPC does not approve closure)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_034():
    """TC-WF-034 | source_id: CW-RSPC-06 row 8 (Director does not approve closure)"""

