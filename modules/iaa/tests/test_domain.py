"""Workflow requirements: AFR-IAA-019..028, 045, 053..057, and 072..075."""
import pytest

from modules.iaa.domain import state_machine as sm


def test_expense_request_requires_valid_submission_before_routing():
    with pytest.raises(sm.GuardFailed):
        sm.validate_transition("request", "Draft", "Submitted", sm.BASIC_USER,
                              values={"complete": False})
    transition = sm.validate_transition(
        "request", "Draft", "Submitted", sm.BASIC_USER,
        values={"complete": True})
    assert transition.destination == "Submitted"


def test_authority_roles_remain_distinct_for_approval_actions():
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve("request", "Finance Validated", "Approved", sm.FINANCE)
    for role in sm.AUTHORITIES:
        assert sm.resolve("request", "Finance Validated", "Approved", role).destination == "Approved"


def test_final_approval_is_blocked_when_another_configured_level_remains():
    with pytest.raises(sm.GuardFailed):
        sm.validate_transition("request", "Approval Pending", "Approved", sm.DEAN,
                               values={"more_levels": True})
    assert sm.validate_transition("request", "Approval Pending", "Approval Pending",
                                  sm.DEAN, values={"more_levels": True})


def test_overdue_escalation_is_event_only_and_requires_elapsed_limit():
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve("request", "Approval Pending", "Escalated", sm.DEAN)
    with pytest.raises(sm.GuardFailed):
        sm.validate_transition("request", "Approval Pending", "Escalated", sm.SYSTEM,
                               values={"overdue": False})
    assert sm.validate_transition("request", "Approval Pending", "Escalated", sm.SYSTEM,
                                  values={"overdue": True})


def test_anomaly_and_audit_observation_lifecycles_match_source_states():
    assert sm.resolve("anomaly", "Open", "Escalated", sm.FINANCE)
    assert sm.resolve("anomaly", "Escalated", "Resolved", sm.AUDITOR)
    with pytest.raises(sm.GuardFailed):
        sm.validate_transition("observation", "Responded", "Closed", sm.AUDITOR,
                               values={"satisfactory": False})
    assert sm.validate_transition("observation", "Responded", "Open", sm.AUDITOR,
                                  values={"satisfactory": False})


def test_recorded_states_have_no_outgoing_transitions():
    for destination in ("Draft", "Submitted", "Approved", "Rejected"):
        with pytest.raises(sm.InvalidTransition):
            sm.resolve("request", "Recorded", destination, sm.FINANCE)
    with pytest.raises(sm.InvalidTransition):
        sm.resolve("ta_claim", "Recorded", "Submitted", sm.FINANCE)
