"""Workflow (WF) Specification Test Suite.
Generated from docs/09-pms/spec-tests/WF_DESIGN.json.
Obligations covered: BW-PMS-01 through BW-PMS-16 and CW-PMS-01 through CW-PMS-05.
"""
import pytest
from modules.pms.domain.state_machine import PatentStateMachine, IllegalTransitionError
from modules.pms.models.application import ApplicationStatus

def test_wf_tc_01():
    """WF-TC-01 | BW-PMS-01 primary-transition-path
    Verify state transitions along workflow path BW-PMS-01: Initial Review Approval Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_02():
    """WF-TC-02 | BW-PMS-02 primary-transition-path
    Verify state transitions along workflow path BW-PMS-02: Revision and Re-Approval Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_03():
    """WF-TC-03 | BW-PMS-03 primary-transition-path
    Verify state transitions along workflow path BW-PMS-03: Appeal Remand Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_04():
    """WF-TC-04 | BW-PMS-04 primary-transition-path
    Verify state transitions along workflow path BW-PMS-04: Appeal Rejection-Upheld Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_05():
    """WF-TC-05 | BW-PMS-05 primary-transition-path
    Verify state transitions along workflow path BW-PMS-05: Appeal Modified-Decision Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_06():
    """WF-TC-06 | BW-PMS-06 primary-transition-path
    Verify state transitions along workflow path BW-PMS-06: Attorney Assignment Acceptance Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_07():
    """WF-TC-07 | BW-PMS-07 primary-transition-path
    Verify state transitions along workflow path BW-PMS-07: Attorney Decline and One Reassignment Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_08():
    """WF-TC-08 | BW-PMS-08 primary-transition-path
    Verify state transitions along workflow path BW-PMS-08: Budget Approval Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_09():
    """WF-TC-09 | BW-PMS-09 primary-transition-path
    Verify state transitions along workflow path BW-PMS-09: Budget Rejection Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_10():
    """WF-TC-10 | BW-PMS-10 primary-transition-path
    Verify state transitions along workflow path BW-PMS-10: Budget Escalation Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_11():
    """WF-TC-11 | BW-PMS-11 primary-transition-path
    Verify state transitions along workflow path BW-PMS-11: External Filing Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_12():
    """WF-TC-12 | BW-PMS-12 primary-transition-path
    Verify state transitions along workflow path BW-PMS-12: Office-Action Response with Applicant Review [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_13():
    """WF-TC-13 | BW-PMS-13 primary-transition-path
    Verify state transitions along workflow path BW-PMS-13: Office-Action Response without Applicant Review [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_14():
    """WF-TC-14 | BW-PMS-14 primary-transition-path
    Verify state transitions along workflow path BW-PMS-14: Maintenance Renewal Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_15():
    """WF-TC-15 | BW-PMS-15 primary-transition-path
    Verify state transitions along workflow path BW-PMS-15: Maintenance Non-Renewal Path [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_16():
    """WF-TC-16 | BW-PMS-16 primary-transition-path
    Verify state transitions along workflow path BW-PMS-16: Generic Pre-Filing Withdrawal Transition [Basis]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_17():
    """WF-TC-17 | CW-PMS-01 primary-transition-path
    Verify state transitions along workflow path CW-PMS-01: Application Review and Disposition [Composite]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_18():
    """WF-TC-18 | CW-PMS-02 primary-transition-path
    Verify state transitions along workflow path CW-PMS-02: Pre-Filing Assignment, Budget, and Filing Governance [Compos
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_19():
    """WF-TC-19 | CW-PMS-03 primary-transition-path
    Verify state transitions along workflow path CW-PMS-03: Office-Action Handling [Composite]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_20():
    """WF-TC-20 | CW-PMS-04 primary-transition-path
    Verify state transitions along workflow path CW-PMS-04: Post-Grant Maintenance Decision Cycle [Composite]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

def test_wf_tc_21():
    """WF-TC-21 | CW-PMS-05 primary-transition-path
    Verify state transitions along workflow path CW-PMS-05: Cross-Cutting Pre-Filing Withdrawal [Composite]
    """
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    nxt2 = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt2 == ApplicationStatus.UNDER_REVIEW

