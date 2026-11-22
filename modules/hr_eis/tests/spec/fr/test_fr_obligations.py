"""Functional Requirement tests for HR-EIS."""
import pytest
import datetime
from modules.hr_eis.contracts import LeaveTypes, EmploymentTypes, LeaveStatus, ClaimStatus
from modules.hr_eis.domain.rules import validate_leave_request, validate_appraisal_window, validate_ltc_claim, validate_cpda_claim, DomainValidationError
from modules.hr_eis.domain.state_machine import LeaveStateMachine, ClaimStateMachine

def test_fr_test_001():
    """[FR-TEST-001] HR-AFR-001 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-001 under HR-CFR-002"""
    res = validate_leave_request(available_balance=16.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_002():
    """[FR-TEST-002] HR-AFR-002 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-002 under HR-CFR-003"""
    res = validate_leave_request(available_balance=17.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_003():
    """[FR-TEST-003] HR-AFR-003 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-003 under HR-CFR-004"""
    res = validate_leave_request(available_balance=18.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_004():
    """[FR-TEST-004] HR-AFR-004 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-004 under HR-CFR-005"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=14.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_005():
    """[FR-TEST-005] HR-AFR-005 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-005 under HR-CFR-006"""
    res = validate_leave_request(available_balance=20.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_006():
    """[FR-TEST-006] HR-AFR-006 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-006 under HR-CFR-007"""
    res = validate_leave_request(available_balance=21.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_007():
    """[FR-TEST-007] HR-AFR-007 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-007 under HR-CFR-008"""
    res = validate_leave_request(available_balance=22.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_008():
    """[FR-TEST-008] HR-AFR-008 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-008 under HR-CFR-009"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=18.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_009():
    """[FR-TEST-009] HR-AFR-009 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-009 under HR-CFR-010"""
    res = validate_leave_request(available_balance=24.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_010():
    """[FR-TEST-010] HR-AFR-010 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-010 under HR-CFR-011"""
    res = validate_leave_request(available_balance=25.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_011():
    """[FR-TEST-011] HR-AFR-011 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-011 under HR-CFR-012"""
    res = validate_leave_request(available_balance=26.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_012():
    """[FR-TEST-012] HR-AFR-012 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-012 under HR-CFR-013"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=22.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_013():
    """[FR-TEST-013] HR-AFR-013 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-013 under HR-CFR-014"""
    res = validate_leave_request(available_balance=28.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_014():
    """[FR-TEST-014] HR-AFR-014 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-014 under HR-CFR-001"""
    res = validate_leave_request(available_balance=29.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_015():
    """[FR-TEST-015] HR-AFR-015 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-015 under HR-CFR-002"""
    res = validate_leave_request(available_balance=30.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_016():
    """[FR-TEST-016] HR-AFR-016 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-016 under HR-CFR-003"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=26.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_017():
    """[FR-TEST-017] HR-AFR-017 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-017 under HR-CFR-004"""
    res = validate_leave_request(available_balance=32.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_018():
    """[FR-TEST-018] HR-AFR-018 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-018 under HR-CFR-005"""
    res = validate_leave_request(available_balance=33.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_019():
    """[FR-TEST-019] HR-AFR-019 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-019 under HR-CFR-006"""
    res = validate_leave_request(available_balance=34.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_020():
    """[FR-TEST-020] HR-AFR-020 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-020 under HR-CFR-007"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=30.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_021():
    """[FR-TEST-021] HR-AFR-021 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-021 under HR-CFR-008"""
    res = validate_leave_request(available_balance=36.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_022():
    """[FR-TEST-022] HR-AFR-022 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-022 under HR-CFR-009"""
    res = validate_leave_request(available_balance=37.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_023():
    """[FR-TEST-023] HR-AFR-023 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-023 under HR-CFR-010"""
    res = validate_leave_request(available_balance=38.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_024():
    """[FR-TEST-024] HR-AFR-024 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-024 under HR-CFR-011"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=34.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_025():
    """[FR-TEST-025] HR-AFR-025 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-025 under HR-CFR-012"""
    res = validate_leave_request(available_balance=40.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_026():
    """[FR-TEST-026] HR-AFR-026 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-026 under HR-CFR-013"""
    res = validate_leave_request(available_balance=41.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_027():
    """[FR-TEST-027] HR-AFR-027 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-027 under HR-CFR-014"""
    res = validate_leave_request(available_balance=42.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_028():
    """[FR-TEST-028] HR-AFR-028 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-028 under HR-CFR-001"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=38.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_029():
    """[FR-TEST-029] HR-AFR-029 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-029 under HR-CFR-002"""
    res = validate_leave_request(available_balance=44.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_030():
    """[FR-TEST-030] HR-AFR-030 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-030 under HR-CFR-003"""
    res = validate_leave_request(available_balance=45.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_031():
    """[FR-TEST-031] HR-AFR-031 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-031 under HR-CFR-004"""
    res = validate_leave_request(available_balance=46.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_032():
    """[FR-TEST-032] HR-AFR-032 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-032 under HR-CFR-005"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=42.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_033():
    """[FR-TEST-033] HR-AFR-033 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-033 under HR-CFR-006"""
    res = validate_leave_request(available_balance=48.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_034():
    """[FR-TEST-034] HR-AFR-034 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-034 under HR-CFR-007"""
    res = validate_leave_request(available_balance=49.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_035():
    """[FR-TEST-035] HR-AFR-035 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-035 under HR-CFR-008"""
    res = validate_leave_request(available_balance=50.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_036():
    """[FR-TEST-036] HR-AFR-036 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-036 under HR-CFR-009"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=46.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_037():
    """[FR-TEST-037] HR-AFR-037 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-037 under HR-CFR-010"""
    res = validate_leave_request(available_balance=52.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_038():
    """[FR-TEST-038] HR-AFR-038 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-038 under HR-CFR-011"""
    res = validate_leave_request(available_balance=53.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_039():
    """[FR-TEST-039] HR-AFR-039 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-039 under HR-CFR-012"""
    res = validate_leave_request(available_balance=54.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_040():
    """[FR-TEST-040] HR-AFR-040 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-040 under HR-CFR-013"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=50.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_041():
    """[FR-TEST-041] HR-AFR-041 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-041 under HR-CFR-014"""
    res = validate_leave_request(available_balance=56.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_042():
    """[FR-TEST-042] HR-AFR-042 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-042 under HR-CFR-001"""
    res = validate_leave_request(available_balance=57.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_043():
    """[FR-TEST-043] HR-AFR-043 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-043 under HR-CFR-002"""
    res = validate_leave_request(available_balance=58.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_044():
    """[FR-TEST-044] HR-AFR-044 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-044 under HR-CFR-003"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=54.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_045():
    """[FR-TEST-045] HR-AFR-045 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-045 under HR-CFR-004"""
    res = validate_leave_request(available_balance=60.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_046():
    """[FR-TEST-046] HR-AFR-046 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-046 under HR-CFR-005"""
    res = validate_leave_request(available_balance=61.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_047():
    """[FR-TEST-047] HR-AFR-047 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-047 under HR-CFR-006"""
    res = validate_leave_request(available_balance=62.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_048():
    """[FR-TEST-048] HR-AFR-048 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-048 under HR-CFR-007"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=58.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_049():
    """[FR-TEST-049] HR-AFR-049 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-049 under HR-CFR-008"""
    res = validate_leave_request(available_balance=64.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_050():
    """[FR-TEST-050] HR-AFR-050 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-050 under HR-CFR-009"""
    res = validate_leave_request(available_balance=65.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_051():
    """[FR-TEST-051] HR-AFR-051 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-051 under HR-CFR-010"""
    res = validate_leave_request(available_balance=66.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_052():
    """[FR-TEST-052] HR-AFR-052 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-052 under HR-CFR-011"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=62.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_053():
    """[FR-TEST-053] HR-AFR-053 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-053 under HR-CFR-012"""
    res = validate_leave_request(available_balance=68.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_054():
    """[FR-TEST-054] HR-AFR-054 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-054 under HR-CFR-013"""
    res = validate_leave_request(available_balance=69.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_055():
    """[FR-TEST-055] HR-AFR-055 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-055 under HR-CFR-014"""
    res = validate_leave_request(available_balance=70.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_056():
    """[FR-TEST-056] HR-AFR-056 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-056 under HR-CFR-001"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=66.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_057():
    """[FR-TEST-057] HR-AFR-057 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-057 under HR-CFR-002"""
    res = validate_leave_request(available_balance=72.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_058():
    """[FR-TEST-058] HR-AFR-058 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-058 under HR-CFR-003"""
    res = validate_leave_request(available_balance=73.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_059():
    """[FR-TEST-059] HR-AFR-059 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-059 under HR-CFR-004"""
    res = validate_leave_request(available_balance=74.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_060():
    """[FR-TEST-060] HR-AFR-060 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-060 under HR-CFR-005"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=70.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_061():
    """[FR-TEST-061] HR-AFR-061 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-061 under HR-CFR-006"""
    res = validate_leave_request(available_balance=76.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_062():
    """[FR-TEST-062] HR-AFR-062 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-062 under HR-CFR-007"""
    res = validate_leave_request(available_balance=77.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_063():
    """[FR-TEST-063] HR-AFR-063 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-063 under HR-CFR-008"""
    res = validate_leave_request(available_balance=78.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_064():
    """[FR-TEST-064] HR-AFR-064 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-064 under HR-CFR-009"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=74.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_065():
    """[FR-TEST-065] HR-AFR-065 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-065 under HR-CFR-010"""
    res = validate_leave_request(available_balance=80.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_066():
    """[FR-TEST-066] HR-AFR-066 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-066 under HR-CFR-011"""
    res = validate_leave_request(available_balance=81.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_067():
    """[FR-TEST-067] HR-AFR-067 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-067 under HR-CFR-012"""
    res = validate_leave_request(available_balance=82.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_068():
    """[FR-TEST-068] HR-AFR-068 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-068 under HR-CFR-013"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=78.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_069():
    """[FR-TEST-069] HR-AFR-069 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-069 under HR-CFR-014"""
    res = validate_leave_request(available_balance=84.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_070():
    """[FR-TEST-070] HR-AFR-070 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-070 under HR-CFR-001"""
    res = validate_leave_request(available_balance=85.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_071():
    """[FR-TEST-071] HR-AFR-071 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-071 under HR-CFR-002"""
    res = validate_leave_request(available_balance=86.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_072():
    """[FR-TEST-072] HR-AFR-072 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-072 under HR-CFR-003"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=82.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_073():
    """[FR-TEST-073] HR-AFR-073 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-073 under HR-CFR-004"""
    res = validate_leave_request(available_balance=88.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_074():
    """[FR-TEST-074] HR-AFR-074 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-074 under HR-CFR-005"""
    res = validate_leave_request(available_balance=89.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_075():
    """[FR-TEST-075] HR-AFR-075 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-075 under HR-CFR-006"""
    res = validate_leave_request(available_balance=90.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_076():
    """[FR-TEST-076] HR-AFR-076 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-076 under HR-CFR-007"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=86.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_077():
    """[FR-TEST-077] HR-AFR-077 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-077 under HR-CFR-008"""
    res = validate_leave_request(available_balance=92.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_078():
    """[FR-TEST-078] HR-AFR-078 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-078 under HR-CFR-009"""
    res = validate_leave_request(available_balance=93.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_079():
    """[FR-TEST-079] HR-AFR-079 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-079 under HR-CFR-010"""
    res = validate_leave_request(available_balance=94.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_080():
    """[FR-TEST-080] HR-AFR-080 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-080 under HR-CFR-011"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=90.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_081():
    """[FR-TEST-081] HR-AFR-081 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-081 under HR-CFR-012"""
    res = validate_leave_request(available_balance=96.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_082():
    """[FR-TEST-082] HR-AFR-082 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-082 under HR-CFR-013"""
    res = validate_leave_request(available_balance=97.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_083():
    """[FR-TEST-083] HR-AFR-083 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-083 under HR-CFR-014"""
    res = validate_leave_request(available_balance=98.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True

def test_fr_test_084():
    """[FR-TEST-084] HR-AFR-084 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-084 under HR-CFR-001"""
    with pytest.raises(DomainValidationError):
        validate_leave_request(available_balance=5.0, requested_days=94.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)

def test_fr_test_085():
    """[FR-TEST-085] HR-AFR-085 requirement-obligation: Verify compliance of EIS functional obligation HR-AFR-085 under HR-CFR-002"""
    res = validate_leave_request(available_balance=100.0, requested_days=2.0, leave_type=LeaveTypes.CASUAL, employment_type=EmploymentTypes.FACULTY)
    assert res is True
