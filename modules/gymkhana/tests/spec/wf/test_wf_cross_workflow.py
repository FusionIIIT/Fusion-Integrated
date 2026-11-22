"""A8 WF tests - cross-workflow dependency.

Generated from the frozen WF_DESIGN.json. Every case is NOT_AUTOMATED because
the A8_BASE backend has no Gymkhana functionality to drive (see each skip reason).
"""
import pytest


@pytest.mark.skip(reason='NOT_AUTOMATED: A8_BASE contains no Gymkhana module (INSTALLED_APPS has only modules.directory, modules.accesscontrol, modules.placement; config/urls.py mounts no gymkhana routes; registry/permissions.json defines no gymkhana permissions or roles); specifically no Club model or UC-GYM-001/UC-GYM-011/UC-GYM-004 interface, so neither the Club Confirmed precondition nor the membership application can be performed. The specified action cannot be executed through any existing backend interface.')
def test_wf_t26_positive():
    """WF-T26 | source_id: Cross-workflow dependency: BW-GYM-03 outcome Club Confirmed enabling BW-GYM-01 transition 1 guard

    purpose: Verify the specified relationship that a club established and confirmed via BW-GYM-03 is a club to which a student can then apply under BW-GYM-01. The specification declares no Composite Workflow, so this checks only the stated guard 'Club is confirmed' and not a combined workflow.
    test_type: positive
    preconditions: The Student Admin has created a club (Club Open) and then approved it (Club Confirmed). A student has no application to that club.
    action_or_input: The student applies for membership to the newly confirmed club (UC-GYM-004).
    expected_result: Submission succeeds and the application is in state 'Membership Application Open'.
    """
