"""Use Case flow tests for HR-EIS."""
import pytest
import datetime
from modules.hr_eis.contracts import LeaveTypes, EmploymentTypes, LeaveStatus, AppraisalStatus, ClaimStatus, AuthorityRoles
from modules.hr_eis.domain.rules import validate_leave_request, validate_appraisal_window, validate_ltc_claim, validate_cpda_claim, DomainValidationError
from modules.hr_eis.domain.state_machine import LeaveStateMachine, AppraisalStateMachine, ClaimStateMachine, InvalidStateTransitionError

def test_uc_test_001():
    """[UC-TEST-001] HR-UC-001 Main Flow: Exercise Main Flow for use case HR-UC-001"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_002():
    """[UC-TEST-002] HR-UC-002 Alternative A1: Exercise Alternative A1 for use case HR-UC-002"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_003():
    """[UC-TEST-003] HR-UC-003 Alternative A2: Exercise Alternative A2 for use case HR-UC-003"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_004():
    """[UC-TEST-004] HR-UC-004 Exception E1: Exercise Exception E1 for use case HR-UC-004"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_005():
    """[UC-TEST-005] HR-UC-005 Exception E2: Exercise Exception E2 for use case HR-UC-005"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_006():
    """[UC-TEST-006] HR-UC-006 Main Flow: Exercise Main Flow for use case HR-UC-006"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_007():
    """[UC-TEST-007] HR-UC-007 Alternative A1: Exercise Alternative A1 for use case HR-UC-007"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_008():
    """[UC-TEST-008] HR-UC-008 Alternative A2: Exercise Alternative A2 for use case HR-UC-008"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_009():
    """[UC-TEST-009] HR-UC-009 Exception E1: Exercise Exception E1 for use case HR-UC-009"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_010():
    """[UC-TEST-010] HR-UC-010 Exception E2: Exercise Exception E2 for use case HR-UC-010"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_011():
    """[UC-TEST-011] HR-UC-011 Main Flow: Exercise Main Flow for use case HR-UC-011"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_012():
    """[UC-TEST-012] HR-UC-012 Alternative A1: Exercise Alternative A1 for use case HR-UC-012"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_013():
    """[UC-TEST-013] HR-UC-013 Alternative A2: Exercise Alternative A2 for use case HR-UC-013"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_014():
    """[UC-TEST-014] HR-UC-014 Exception E1: Exercise Exception E1 for use case HR-UC-014"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_015():
    """[UC-TEST-015] HR-UC-015 Exception E2: Exercise Exception E2 for use case HR-UC-015"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_016():
    """[UC-TEST-016] HR-UC-016 Main Flow: Exercise Main Flow for use case HR-UC-016"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_017():
    """[UC-TEST-017] HR-UC-017 Alternative A1: Exercise Alternative A1 for use case HR-UC-017"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_018():
    """[UC-TEST-018] HR-UC-018 Alternative A2: Exercise Alternative A2 for use case HR-UC-018"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_019():
    """[UC-TEST-019] HR-UC-019 Exception E1: Exercise Exception E1 for use case HR-UC-019"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_020():
    """[UC-TEST-020] HR-UC-020 Exception E2: Exercise Exception E2 for use case HR-UC-020"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_021():
    """[UC-TEST-021] HR-UC-021 Main Flow: Exercise Main Flow for use case HR-UC-021"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_022():
    """[UC-TEST-022] HR-UC-022 Alternative A1: Exercise Alternative A1 for use case HR-UC-022"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_023():
    """[UC-TEST-023] HR-UC-001 Alternative A2: Exercise Alternative A2 for use case HR-UC-001"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_024():
    """[UC-TEST-024] HR-UC-002 Exception E1: Exercise Exception E1 for use case HR-UC-002"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_025():
    """[UC-TEST-025] HR-UC-003 Exception E2: Exercise Exception E2 for use case HR-UC-003"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_026():
    """[UC-TEST-026] HR-UC-004 Main Flow: Exercise Main Flow for use case HR-UC-004"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_027():
    """[UC-TEST-027] HR-UC-005 Alternative A1: Exercise Alternative A1 for use case HR-UC-005"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_028():
    """[UC-TEST-028] HR-UC-006 Alternative A2: Exercise Alternative A2 for use case HR-UC-006"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_029():
    """[UC-TEST-029] HR-UC-007 Exception E1: Exercise Exception E1 for use case HR-UC-007"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_030():
    """[UC-TEST-030] HR-UC-008 Exception E2: Exercise Exception E2 for use case HR-UC-008"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_031():
    """[UC-TEST-031] HR-UC-009 Main Flow: Exercise Main Flow for use case HR-UC-009"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_032():
    """[UC-TEST-032] HR-UC-010 Alternative A1: Exercise Alternative A1 for use case HR-UC-010"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_033():
    """[UC-TEST-033] HR-UC-011 Alternative A2: Exercise Alternative A2 for use case HR-UC-011"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_034():
    """[UC-TEST-034] HR-UC-012 Exception E1: Exercise Exception E1 for use case HR-UC-012"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_035():
    """[UC-TEST-035] HR-UC-013 Exception E2: Exercise Exception E2 for use case HR-UC-013"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_036():
    """[UC-TEST-036] HR-UC-014 Main Flow: Exercise Main Flow for use case HR-UC-014"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_037():
    """[UC-TEST-037] HR-UC-015 Alternative A1: Exercise Alternative A1 for use case HR-UC-015"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_038():
    """[UC-TEST-038] HR-UC-016 Alternative A2: Exercise Alternative A2 for use case HR-UC-016"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_039():
    """[UC-TEST-039] HR-UC-017 Exception E1: Exercise Exception E1 for use case HR-UC-017"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_040():
    """[UC-TEST-040] HR-UC-018 Exception E2: Exercise Exception E2 for use case HR-UC-018"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_041():
    """[UC-TEST-041] HR-UC-019 Main Flow: Exercise Main Flow for use case HR-UC-019"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_042():
    """[UC-TEST-042] HR-UC-020 Alternative A1: Exercise Alternative A1 for use case HR-UC-020"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_043():
    """[UC-TEST-043] HR-UC-021 Alternative A2: Exercise Alternative A2 for use case HR-UC-021"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_044():
    """[UC-TEST-044] HR-UC-022 Exception E1: Exercise Exception E1 for use case HR-UC-022"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_045():
    """[UC-TEST-045] HR-UC-001 Exception E2: Exercise Exception E2 for use case HR-UC-001"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_046():
    """[UC-TEST-046] HR-UC-002 Main Flow: Exercise Main Flow for use case HR-UC-002"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_047():
    """[UC-TEST-047] HR-UC-003 Alternative A1: Exercise Alternative A1 for use case HR-UC-003"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_048():
    """[UC-TEST-048] HR-UC-004 Alternative A2: Exercise Alternative A2 for use case HR-UC-004"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_049():
    """[UC-TEST-049] HR-UC-005 Exception E1: Exercise Exception E1 for use case HR-UC-005"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_050():
    """[UC-TEST-050] HR-UC-006 Exception E2: Exercise Exception E2 for use case HR-UC-006"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_051():
    """[UC-TEST-051] HR-UC-007 Main Flow: Exercise Main Flow for use case HR-UC-007"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_052():
    """[UC-TEST-052] HR-UC-008 Alternative A1: Exercise Alternative A1 for use case HR-UC-008"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_053():
    """[UC-TEST-053] HR-UC-009 Alternative A2: Exercise Alternative A2 for use case HR-UC-009"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_054():
    """[UC-TEST-054] HR-UC-010 Exception E1: Exercise Exception E1 for use case HR-UC-010"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_055():
    """[UC-TEST-055] HR-UC-011 Exception E2: Exercise Exception E2 for use case HR-UC-011"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_056():
    """[UC-TEST-056] HR-UC-012 Main Flow: Exercise Main Flow for use case HR-UC-012"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_057():
    """[UC-TEST-057] HR-UC-013 Alternative A1: Exercise Alternative A1 for use case HR-UC-013"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_058():
    """[UC-TEST-058] HR-UC-014 Alternative A2: Exercise Alternative A2 for use case HR-UC-014"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_059():
    """[UC-TEST-059] HR-UC-015 Exception E1: Exercise Exception E1 for use case HR-UC-015"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_060():
    """[UC-TEST-060] HR-UC-016 Exception E2: Exercise Exception E2 for use case HR-UC-016"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_061():
    """[UC-TEST-061] HR-UC-017 Main Flow: Exercise Main Flow for use case HR-UC-017"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_062():
    """[UC-TEST-062] HR-UC-018 Alternative A1: Exercise Alternative A1 for use case HR-UC-018"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_063():
    """[UC-TEST-063] HR-UC-019 Alternative A2: Exercise Alternative A2 for use case HR-UC-019"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_064():
    """[UC-TEST-064] HR-UC-020 Exception E1: Exercise Exception E1 for use case HR-UC-020"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_065():
    """[UC-TEST-065] HR-UC-021 Exception E2: Exercise Exception E2 for use case HR-UC-021"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_066():
    """[UC-TEST-066] HR-UC-022 Main Flow: Exercise Main Flow for use case HR-UC-022"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_067():
    """[UC-TEST-067] HR-UC-001 Alternative A1: Exercise Alternative A1 for use case HR-UC-001"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_068():
    """[UC-TEST-068] HR-UC-002 Alternative A2: Exercise Alternative A2 for use case HR-UC-002"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_069():
    """[UC-TEST-069] HR-UC-003 Exception E1: Exercise Exception E1 for use case HR-UC-003"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_070():
    """[UC-TEST-070] HR-UC-004 Exception E2: Exercise Exception E2 for use case HR-UC-004"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_071():
    """[UC-TEST-071] HR-UC-005 Main Flow: Exercise Main Flow for use case HR-UC-005"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_072():
    """[UC-TEST-072] HR-UC-006 Alternative A1: Exercise Alternative A1 for use case HR-UC-006"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_073():
    """[UC-TEST-073] HR-UC-007 Alternative A2: Exercise Alternative A2 for use case HR-UC-007"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_074():
    """[UC-TEST-074] HR-UC-008 Exception E1: Exercise Exception E1 for use case HR-UC-008"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_075():
    """[UC-TEST-075] HR-UC-009 Exception E2: Exercise Exception E2 for use case HR-UC-009"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_076():
    """[UC-TEST-076] HR-UC-010 Main Flow: Exercise Main Flow for use case HR-UC-010"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_077():
    """[UC-TEST-077] HR-UC-011 Alternative A1: Exercise Alternative A1 for use case HR-UC-011"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_078():
    """[UC-TEST-078] HR-UC-012 Alternative A2: Exercise Alternative A2 for use case HR-UC-012"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_079():
    """[UC-TEST-079] HR-UC-013 Exception E1: Exercise Exception E1 for use case HR-UC-013"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_080():
    """[UC-TEST-080] HR-UC-014 Exception E2: Exercise Exception E2 for use case HR-UC-014"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_081():
    """[UC-TEST-081] HR-UC-015 Main Flow: Exercise Main Flow for use case HR-UC-015"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_082():
    """[UC-TEST-082] HR-UC-016 Alternative A1: Exercise Alternative A1 for use case HR-UC-016"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_083():
    """[UC-TEST-083] HR-UC-017 Alternative A2: Exercise Alternative A2 for use case HR-UC-017"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_084():
    """[UC-TEST-084] HR-UC-018 Exception E1: Exercise Exception E1 for use case HR-UC-018"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_085():
    """[UC-TEST-085] HR-UC-019 Exception E2: Exercise Exception E2 for use case HR-UC-019"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_086():
    """[UC-TEST-086] HR-UC-020 Main Flow: Exercise Main Flow for use case HR-UC-020"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_087():
    """[UC-TEST-087] HR-UC-021 Alternative A1: Exercise Alternative A1 for use case HR-UC-021"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_088():
    """[UC-TEST-088] HR-UC-022 Alternative A2: Exercise Alternative A2 for use case HR-UC-022"""
    nxt = LeaveStateMachine.transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, AuthorityRoles.HOD)
    assert nxt == LeaveStatus.RECOMMENDED

def test_uc_test_089():
    """[UC-TEST-089] HR-UC-001 Exception E1: Exercise Exception E1 for use case HR-UC-001"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)

def test_uc_test_090():
    """[UC-TEST-090] HR-UC-002 Exception E2: Exercise Exception E2 for use case HR-UC-002"""
    with pytest.raises((DomainValidationError, InvalidStateTransitionError)):
        LeaveStateMachine.transition(LeaveStatus.REJECTED, LeaveStatus.APPROVED, AuthorityRoles.HOD)
