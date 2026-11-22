"""Workflow state transition tests for HR-EIS."""
import pytest
import datetime
from modules.hr_eis.contracts import LeaveTypes, EmploymentTypes, LeaveStatus, AppraisalStatus, ClaimStatus, AuthorityRoles
from modules.hr_eis.domain.state_machine import LeaveStateMachine, AppraisalStateMachine, ClaimStateMachine, InvalidStateTransitionError

def test_wf_test_001():
    """[WF-TEST-001] CW-HR-01 submission-path-path: Verify state progression in CW-HR-01 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_002():
    """[WF-TEST-002] CW-HR-02 approval-step-path: Verify state progression in CW-HR-02 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_003():
    """[WF-TEST-003] CW-HR-03 rejection-step-path: Verify state progression in CW-HR-03 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_004():
    """[WF-TEST-004] CW-HR-04 settlement-step-path: Verify state progression in CW-HR-04 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_005():
    """[WF-TEST-005] CW-HR-01 audit-verification-path: Verify state progression in CW-HR-01 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_006():
    """[WF-TEST-006] CW-HR-02 submission-path-path: Verify state progression in CW-HR-02 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_007():
    """[WF-TEST-007] CW-HR-03 approval-step-path: Verify state progression in CW-HR-03 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_008():
    """[WF-TEST-008] CW-HR-04 rejection-step-path: Verify state progression in CW-HR-04 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_009():
    """[WF-TEST-009] CW-HR-01 settlement-step-path: Verify state progression in CW-HR-01 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_010():
    """[WF-TEST-010] CW-HR-02 audit-verification-path: Verify state progression in CW-HR-02 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_011():
    """[WF-TEST-011] CW-HR-03 submission-path-path: Verify state progression in CW-HR-03 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_012():
    """[WF-TEST-012] CW-HR-04 approval-step-path: Verify state progression in CW-HR-04 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_013():
    """[WF-TEST-013] CW-HR-01 rejection-step-path: Verify state progression in CW-HR-01 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_014():
    """[WF-TEST-014] CW-HR-02 settlement-step-path: Verify state progression in CW-HR-02 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_015():
    """[WF-TEST-015] CW-HR-03 audit-verification-path: Verify state progression in CW-HR-03 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_016():
    """[WF-TEST-016] CW-HR-04 submission-path-path: Verify state progression in CW-HR-04 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_017():
    """[WF-TEST-017] CW-HR-01 approval-step-path: Verify state progression in CW-HR-01 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_018():
    """[WF-TEST-018] CW-HR-02 rejection-step-path: Verify state progression in CW-HR-02 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_019():
    """[WF-TEST-019] CW-HR-03 settlement-step-path: Verify state progression in CW-HR-03 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_020():
    """[WF-TEST-020] CW-HR-04 audit-verification-path: Verify state progression in CW-HR-04 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_021():
    """[WF-TEST-021] CW-HR-01 submission-path-path: Verify state progression in CW-HR-01 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_022():
    """[WF-TEST-022] CW-HR-02 approval-step-path: Verify state progression in CW-HR-02 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_023():
    """[WF-TEST-023] CW-HR-03 rejection-step-path: Verify state progression in CW-HR-03 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_024():
    """[WF-TEST-024] CW-HR-04 settlement-step-path: Verify state progression in CW-HR-04 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_025():
    """[WF-TEST-025] CW-HR-01 audit-verification-path: Verify state progression in CW-HR-01 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_026():
    """[WF-TEST-026] CW-HR-02 submission-path-path: Verify state progression in CW-HR-02 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_027():
    """[WF-TEST-027] CW-HR-03 approval-step-path: Verify state progression in CW-HR-03 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_028():
    """[WF-TEST-028] CW-HR-04 rejection-step-path: Verify state progression in CW-HR-04 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_029():
    """[WF-TEST-029] CW-HR-01 settlement-step-path: Verify state progression in CW-HR-01 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_030():
    """[WF-TEST-030] CW-HR-02 audit-verification-path: Verify state progression in CW-HR-02 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_031():
    """[WF-TEST-031] CW-HR-03 submission-path-path: Verify state progression in CW-HR-03 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_032():
    """[WF-TEST-032] CW-HR-04 approval-step-path: Verify state progression in CW-HR-04 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_033():
    """[WF-TEST-033] CW-HR-01 rejection-step-path: Verify state progression in CW-HR-01 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_034():
    """[WF-TEST-034] CW-HR-02 settlement-step-path: Verify state progression in CW-HR-02 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_035():
    """[WF-TEST-035] CW-HR-03 audit-verification-path: Verify state progression in CW-HR-03 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_036():
    """[WF-TEST-036] CW-HR-04 submission-path-path: Verify state progression in CW-HR-04 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_037():
    """[WF-TEST-037] CW-HR-01 approval-step-path: Verify state progression in CW-HR-01 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_038():
    """[WF-TEST-038] CW-HR-02 rejection-step-path: Verify state progression in CW-HR-02 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_039():
    """[WF-TEST-039] CW-HR-03 settlement-step-path: Verify state progression in CW-HR-03 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_040():
    """[WF-TEST-040] CW-HR-04 audit-verification-path: Verify state progression in CW-HR-04 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_041():
    """[WF-TEST-041] CW-HR-01 submission-path-path: Verify state progression in CW-HR-01 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_042():
    """[WF-TEST-042] CW-HR-02 approval-step-path: Verify state progression in CW-HR-02 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_043():
    """[WF-TEST-043] CW-HR-03 rejection-step-path: Verify state progression in CW-HR-03 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_044():
    """[WF-TEST-044] CW-HR-04 settlement-step-path: Verify state progression in CW-HR-04 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_045():
    """[WF-TEST-045] CW-HR-01 audit-verification-path: Verify state progression in CW-HR-01 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_046():
    """[WF-TEST-046] CW-HR-02 submission-path-path: Verify state progression in CW-HR-02 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_047():
    """[WF-TEST-047] CW-HR-03 approval-step-path: Verify state progression in CW-HR-03 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_048():
    """[WF-TEST-048] CW-HR-04 rejection-step-path: Verify state progression in CW-HR-04 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_049():
    """[WF-TEST-049] CW-HR-01 settlement-step-path: Verify state progression in CW-HR-01 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_050():
    """[WF-TEST-050] CW-HR-02 audit-verification-path: Verify state progression in CW-HR-02 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_051():
    """[WF-TEST-051] CW-HR-03 submission-path-path: Verify state progression in CW-HR-03 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_052():
    """[WF-TEST-052] CW-HR-04 approval-step-path: Verify state progression in CW-HR-04 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_053():
    """[WF-TEST-053] CW-HR-01 rejection-step-path: Verify state progression in CW-HR-01 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_054():
    """[WF-TEST-054] CW-HR-02 settlement-step-path: Verify state progression in CW-HR-02 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_055():
    """[WF-TEST-055] CW-HR-03 audit-verification-path: Verify state progression in CW-HR-03 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_056():
    """[WF-TEST-056] CW-HR-04 submission-path-path: Verify state progression in CW-HR-04 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_057():
    """[WF-TEST-057] CW-HR-01 approval-step-path: Verify state progression in CW-HR-01 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_058():
    """[WF-TEST-058] CW-HR-02 rejection-step-path: Verify state progression in CW-HR-02 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_059():
    """[WF-TEST-059] CW-HR-03 settlement-step-path: Verify state progression in CW-HR-03 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_060():
    """[WF-TEST-060] CW-HR-04 audit-verification-path: Verify state progression in CW-HR-04 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_061():
    """[WF-TEST-061] CW-HR-01 submission-path-path: Verify state progression in CW-HR-01 along submission-path"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR

def test_wf_test_062():
    """[WF-TEST-062] CW-HR-02 approval-step-path: Verify state progression in CW-HR-02 along approval-step"""
    s = LeaveStateMachine.transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, AuthorityRoles.DIRECTOR)
    assert s == LeaveStatus.APPROVED

def test_wf_test_063():
    """[WF-TEST-063] CW-HR-03 rejection-step-path: Verify state progression in CW-HR-03 along rejection-step"""
    s = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, AuthorityRoles.HOD)
    assert s == LeaveStatus.REJECTED

def test_wf_test_064():
    """[WF-TEST-064] CW-HR-04 settlement-step-path: Verify state progression in CW-HR-04 along settlement-step"""
    s = ClaimStateMachine.transition(ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.SETTLED_FINANCE, AuthorityRoles.ACCOUNTANT)
    assert s == ClaimStatus.SETTLED_FINANCE

def test_wf_test_065():
    """[WF-TEST-065] CW-HR-01 audit-verification-path: Verify state progression in CW-HR-01 along audit-verification"""
    s = ClaimStateMachine.transition(ClaimStatus.SUBMITTED, ClaimStatus.VERIFIED_HR, AuthorityRoles.HR_ADMIN)
    assert s == ClaimStatus.VERIFIED_HR
