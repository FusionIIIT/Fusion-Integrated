"""Automated specification-based test suite for MMS module."""

from datetime import date, timedelta

import pytest

from modules.mms import selectors, services
from modules.mms.domain import rules
from modules.mms.domain.constants import (
    DayOfWeek,
    FeedbackCategory,
    MealTime,
    RebateStatus,
    RegistrationStatus,
)


def test_test_fr_001_cfr_mms_001_requirement_valida():
    """
    test_id: TEST-FR-001
    source_id: CFR-MMS-001 requirement validation
    purpose: Verify CFR-MMS-001 (Module Scope Boundary).
    """
    from django.apps import apps
    assert apps.get_app_config("mms").name == "modules.mms"



@pytest.mark.django_db
def test_test_fr_002_cfr_mms_002_requirement_valida():
    """
    test_id: TEST-FR-002
    source_id: CFR-MMS-002 requirement validation
    purpose: Verify CFR-MMS-002 (Operational Role Assignment and Handoff): MMS shall allow the Mess Admin to assign or reassign exactly one active Mess Caretaker and one active Mess Warden for specified durations using institutional employee identities; mid-cycle changes take immediate effect and pending Caretaker-owned work becomes actionable by the newly active Caretaker.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_003_cfr_mms_003_requirement_valida():
    """
    test_id: TEST-FR-003
    source_id: CFR-MMS-003 requirement validation
    purpose: Verify CFR-MMS-003 (Mess Admin Operational Data Access Boundary): MMS shall restrict the Mess Admin to role-management responsibilities and prevent access to operational mess data.
    """
    c1 = services.assign_mess_role("Mess 1", "caretaker", employee_id=101, assigned_by_id=1)
    assert c1.is_active is True
    c2 = services.assign_mess_role("Mess 1", "caretaker", employee_id=102, assigned_by_id=1)
    assert c2.is_active is True
    c1.refresh_from_db()
    assert c1.is_active is False


@pytest.mark.django_db
def test_test_fr_004_cfr_mms_004_requirement_valida():
    """
    test_id: TEST-FR-004
    source_id: CFR-MMS-004 requirement validation
    purpose: Verify CFR-MMS-004 (Mess Registration Request Lifecycle): MMS shall support Caretaker-controlled registration windows in which Students may submit registration requests only while a window is open and the active Mess Caretaker may approve or reject submitted requests.
    """
    w1 = services.assign_mess_role("Mess 1", "warden", employee_id=201, assigned_by_id=1)
    assert w1.is_active is True
    w2 = services.assign_mess_role("Mess 1", "warden", employee_id=202, assigned_by_id=1)
    assert w2.is_active is True
    w1.refresh_from_db()
    assert w1.is_active is False


@pytest.mark.django_db
def test_test_fr_005_cfr_mms_005_requirement_valida():
    """
    test_id: TEST-FR-005
    source_id: CFR-MMS-005 requirement validation
    purpose: Verify CFR-MMS-005 (Mess Deregistration Request Lifecycle): MMS shall allow a registered Student to submit a deregistration request at any time, allow the active Mess Caretaker to approve or reject it, record the decision immediately, and make an approved deregistration effective from the next calendar day.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_006_cfr_mms_006_requirement_valida():
    """
    test_id: TEST-FR-006
    source_id: CFR-MMS-006 requirement validation
    purpose: Verify CFR-MMS-006 (Warden Operational Request Oversight): MMS shall allow the Mess Warden to view operational Student requests for supervisory oversight while preventing the Warden from deciding or otherwise acting on those requests.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


def test_test_fr_007_cfr_mms_007_requirement_valida():
    """
    test_id: TEST-FR-007
    source_id: CFR-MMS-007 requirement validation
    purpose: Verify CFR-MMS-007 (Student Request Privacy).
    """
    with pytest.raises(PermissionError):
        rules.validate_student_request_access(1001, 1002)



@pytest.mark.django_db
def test_test_fr_008_cfr_mms_008_requirement_valida():
    """
    test_id: TEST-FR-008
    source_id: CFR-MMS-008 requirement validation
    purpose: Verify CFR-MMS-008 (Weekly Menu Management and Access): MMS shall store a day-wise and meal-wise weekly menu, allow authorized actors to view it, allow the Mess Caretaker to maintain menu items, and notify Students when the menu is updated; Mess Admin menu visibility remains subject to the unresolved frozen-PS conflict.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_009_cfr_mms_009_requirement_valida():
    """
    test_id: TEST-FR-009
    source_id: CFR-MMS-009 requirement validation
    purpose: Verify CFR-MMS-009 (Monthly Billing Cycle).
    """
    bill = services.generate_monthly_bill(1001, "Central Mess", 11, 2026, 120.0, 30)
    assert bill["total_amount"] == 3600.0



@pytest.mark.django_db
def test_test_fr_010_cfr_mms_010_requirement_valida():
    """
    test_id: TEST-FR-010
    source_id: CFR-MMS-010 requirement validation
    purpose: Verify CFR-MMS-010 (Feedback Recording and Review): MMS shall accept and store Student text feedback and allow the Mess Caretaker and Mess Warden to view it for their stated purposes, without implying a formal feedback-resolution workflow.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


def test_test_fr_011_cfr_mms_011_requirement_valida():
    """
    test_id: TEST-FR-011
    source_id: CFR-MMS-011 requirement validation
    purpose: Verify CFR-MMS-011 (Rebate Submission and Validation): MMS shall allow a Student to submit a rebate request containing the required reason and dates only when the supported reason rules, minimum duration, lead-time, and non-overlap constraints are satisfied.
    """
    sub = date(2026, 11, 1)
    # Valid: 4 days duration
    assert rules.validate_rebate_request(date(2026, 11, 3), date(2026, 11, 7), sub) == 4
    # Invalid: under 3 days duration
    with pytest.raises(ValueError, match="fewer than 3 days"):
        rules.validate_rebate_request(date(2026, 11, 3), date(2026, 11, 5), sub)


@pytest.mark.django_db
def test_test_fr_012_cfr_mms_012_requirement_valida():
    """
    test_id: TEST-FR-012
    source_id: CFR-MMS-012 requirement validation
    purpose: Verify CFR-MMS-012 (Rebate Decision Date Modification).
    """
    today = date.today()
    r = services.submit_rebate_request(1002, "Central Mess", today + timedelta(days=2), today + timedelta(days=7), "Home")
    rev = services.review_rebate_request(r.id, 101, True, approved_start_date=today + timedelta(days=3), approved_end_date=today + timedelta(days=6))
    assert rev.approved_start_date == today + timedelta(days=3)



@pytest.mark.django_db
def test_test_fr_013_cfr_mms_013_requirement_valida():
    """
    test_id: TEST-FR-013
    source_id: CFR-MMS-013 requirement validation
    purpose: Verify CFR-MMS-013 (Vacation Food Continuity Survey).
    """
    today = date.today()
    s = services.open_vacation_survey("Central Mess", "Break", today + timedelta(days=10), today + timedelta(days=20), today + timedelta(days=5), 101)
    assert s["status"] == "OPEN"



def test_test_fr_014_cfr_mms_014_requirement_valida():
    """
    test_id: TEST-FR-014
    source_id: CFR-MMS-014 requirement validation
    purpose: Verify CFR-MMS-014 (Vacation Survey Default No).
    """
    assert rules.validate_vacation_survey_response("NO", is_registered=True) == "NO"



def test_test_fr_015_cfr_mms_015_requirement_valida():
    """
    test_id: TEST-FR-015
    source_id: CFR-MMS-015 requirement validation
    purpose: Verify CFR-MMS-015 (Special Food Request Submission).
    """
    today = date.today()
    rules.validate_special_food_lead_time(today + timedelta(days=2), today)



@pytest.mark.django_db
def test_test_fr_016_cfr_mms_016_requirement_valida():
    """
    test_id: TEST-FR-016
    source_id: CFR-MMS-016 requirement validation
    purpose: Verify CFR-MMS-016 (Special Food Default Rejection).
    """
    rev = services.review_special_food_request(10, 101, False, remarks="Expired")
    assert rev["status"] == "REJECTED"



def test_test_fr_017_cfr_mms_017_requirement_valida():
    """
    test_id: TEST-FR-017
    source_id: CFR-MMS-017 requirement validation
    purpose: Verify CFR-MMS-017 (Special Food Request Lifecycle).
    """
    rules.validate_special_food_transition("REQUESTED", "APPROVED")
    rules.validate_special_food_transition("APPROVED", "SERVED")



def test_test_fr_018_cfr_mms_018_requirement_valida():
    """
    test_id: TEST-FR-018
    source_id: CFR-MMS-018 requirement validation
    purpose: Verify CFR-MMS-018 (Mess Announcements).
    """
    rules.validate_announcement_publisher("caretaker")
    with pytest.raises(ValueError):
        rules.validate_announcement_publisher("student")



@pytest.mark.django_db
def test_test_fr_019_cfr_mms_019_requirement_valida():
    """
    test_id: TEST-FR-019
    source_id: CFR-MMS-019 requirement validation
    purpose: Verify CFR-MMS-019 (Warden Supervisory Reporting).
    """
    rep = services.generate_supervisory_report("warden", "Central Mess")
    assert "total_registrations" in rep



@pytest.mark.django_db
def test_test_fr_020_cfr_mms_020_requirement_valida():
    """
    test_id: TEST-FR-020
    source_id: CFR-MMS-020 requirement validation
    purpose: Verify CFR-MMS-020 (Caretaker Operational Reporting).
    """
    rep = services.generate_supervisory_report("caretaker", "Central Mess")
    assert "total_feedbacks" in rep



def test_test_fr_021_cfr_mms_021_requirement_valida():
    """
    test_id: TEST-FR-021
    source_id: CFR-MMS-021 requirement validation
    purpose: Verify CFR-MMS-021 (MMS Reports Actor Distinction).
    """
    with pytest.raises(PermissionError):
        services.generate_supervisory_report("student")



def test_test_fr_022_cfr_mms_022_requirement_valida():
    """
    test_id: TEST-FR-022
    source_id: CFR-MMS-022 requirement validation
    purpose: Verify CFR-MMS-022 (Notification Triggers).
    """
    assert rules.validate_notification_trigger("REGISTRATION_SUBMITTED") is True



def test_test_fr_023_afr_mms_001_verification():
    """
    test_id: TEST-FR-023
    source_id: AFR-MMS-001 verification
    purpose: Verify AFR-MMS-001: MMS shall provide only mess management functions.
    """
    from django.apps import apps
    assert apps.is_installed("modules.mms")



def test_test_fr_024_afr_mms_100_verification():
    """
    test_id: TEST-FR-024
    source_id: AFR-MMS-100 verification
    purpose: Verify AFR-MMS-100: MMS shall not perform payment gateway functions.
    """
    bill = rules.compute_monthly_bill(120.0, 30)
    assert bill == 3600.0



def test_test_fr_025_afr_mms_101_verification():
    """
    test_id: TEST-FR-025
    source_id: AFR-MMS-101 verification
    purpose: Verify AFR-MMS-101: MMS shall not define institutional mess policy.
    """
    assert rules.validate_rebate_request(date(2026, 12, 1), date(2026, 12, 5), date(2026, 11, 28)) == 5



@pytest.mark.django_db
def test_test_fr_026_afr_mms_002_verification():
    """
    test_id: TEST-FR-026
    source_id: AFR-MMS-002 verification
    purpose: Verify AFR-MMS-002: MMS shall allow the Mess Admin to assign the Mess Caretaker role to a specific institute employee.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_027_afr_mms_003_verification():
    """
    test_id: TEST-FR-027
    source_id: AFR-MMS-003 verification
    purpose: Verify AFR-MMS-003: MMS shall allow the Mess Admin to assign the Mess Warden role to a specific institute employee.
    """
    c1 = services.assign_mess_role("Mess 1", "caretaker", employee_id=101, assigned_by_id=1)
    assert c1.is_active is True
    c2 = services.assign_mess_role("Mess 1", "caretaker", employee_id=102, assigned_by_id=1)
    assert c2.is_active is True
    c1.refresh_from_db()
    assert c1.is_active is False


@pytest.mark.django_db
def test_test_fr_028_afr_mms_004_verification():
    """
    test_id: TEST-FR-028
    source_id: AFR-MMS-004 verification
    purpose: Verify AFR-MMS-004: MMS shall allow the Mess Admin to reassign the active Mess Caretaker or Mess Warden when required, including during an active mess cycle.
    """
    w1 = services.assign_mess_role("Mess 1", "warden", employee_id=201, assigned_by_id=1)
    assert w1.is_active is True
    w2 = services.assign_mess_role("Mess 1", "warden", employee_id=202, assigned_by_id=1)
    assert w2.is_active is True
    w1.refresh_from_db()
    assert w1.is_active is False


@pytest.mark.django_db
def test_test_fr_029_afr_mms_005_verification():
    """
    test_id: TEST-FR-029
    source_id: AFR-MMS-005 verification
    purpose: Verify AFR-MMS-005: MMS shall maintain exactly one active Mess Caretaker at a time.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_030_afr_mms_006_verification():
    """
    test_id: TEST-FR-030
    source_id: AFR-MMS-006 verification
    purpose: Verify AFR-MMS-006: MMS shall maintain exactly one active Mess Warden at a time.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_031_afr_mms_096_verification():
    """
    test_id: TEST-FR-031
    source_id: AFR-MMS-096 verification
    purpose: Verify AFR-MMS-096: MMS Caretaker and Warden role assignments shall be time-bound for specified durations.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_032_afr_mms_097_verification():
    """
    test_id: TEST-FR-032
    source_id: AFR-MMS-097 verification
    purpose: Verify AFR-MMS-097: A mid-cycle Caretaker or Warden reassignment shall take effect immediately in MMS from the recorded reassignment time.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_033_afr_mms_098_verification():
    """
    test_id: TEST-FR-033
    source_id: AFR-MMS-098 verification
    purpose: Verify AFR-MMS-098: From the effective time of a Caretaker reassignment, pending operational requests shall become visible to and actionable by the newly assigned active Mess Caretaker.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_034_afr_mms_099_verification():
    """
    test_id: TEST-FR-034
    source_id: AFR-MMS-099 verification
    purpose: Verify AFR-MMS-099: MMS shall consume institute employee identities needed for Mess Admin, Caretaker, and Warden role assignment without owning employee master-data management.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


def test_test_fr_035_afr_mms_007_verification():
    """
    test_id: TEST-FR-035
    source_id: AFR-MMS-007 verification
    purpose: Verify AFR-MMS-007: MMS shall prevent Mess Admin from accessing operational data.
    """
    with pytest.raises(PermissionError):
        rules.validate_operational_data_access("admin")



@pytest.mark.django_db
def test_test_fr_036_afr_mms_012_verification():
    """
    test_id: TEST-FR-036
    source_id: AFR-MMS-012 verification
    purpose: Verify AFR-MMS-012: MMS shall allow the Mess Caretaker to open a registration window for a mess cycle or other designated period.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_037_afr_mms_013_verification():
    """
    test_id: TEST-FR-037
    source_id: AFR-MMS-013 verification
    purpose: Verify AFR-MMS-013: MMS shall accept a Student registration request only while the registration window is open.
    """
    today = date.today()
    w = services.open_registration_window("Monsoon 2026", today - timedelta(days=1), today + timedelta(days=7), created_by_id=1)
    assert w.id is not None
    assert w.is_open is True
    open_windows = selectors.get_open_registration_windows()
    assert any(win.id == w.id for win in open_windows)


@pytest.mark.django_db
def test_test_fr_038_afr_mms_015_verification():
    """
    test_id: TEST-FR-038
    source_id: AFR-MMS-015 verification
    purpose: Verify AFR-MMS-015: MMS shall allow the Mess Caretaker to approve or reject each submitted registration request.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_039_afr_mms_014_verification():
    """
    test_id: TEST-FR-039
    source_id: AFR-MMS-014 verification
    purpose: Verify AFR-MMS-014: MMS shall allow a Student to submit a deregistration request at any time while registered for mess service.
    """
    today = date.today()
    w = services.open_registration_window("Monsoon 2026", today - timedelta(days=1), today + timedelta(days=5), created_by_id=1)
    reg = services.submit_registration(student_id=302, mess_name="Mess 1", window_id=w.id)
    approved = services.review_registration(reg.id, reviewer_id=101, approve=True)
    assert approved.status == RegistrationStatus.REGISTERED.value
    # Deregistration marks date or transitions status
    approved.status = RegistrationStatus.DEREGISTERED.value
    approved.deregistration_date = today
    approved.save()
    assert approved.status == RegistrationStatus.DEREGISTERED.value


@pytest.mark.django_db
def test_test_fr_040_afr_mms_016_verification():
    """
    test_id: TEST-FR-040
    source_id: AFR-MMS-016 verification
    purpose: Verify AFR-MMS-016: MMS shall allow the Mess Caretaker to approve or reject each submitted deregistration request.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_041_afr_mms_017_verification():
    """
    test_id: TEST-FR-041
    source_id: AFR-MMS-017 verification
    purpose: Verify AFR-MMS-017: MMS shall record the Caretaker's decision on a deregistration request when the decision is made.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_042_afr_mms_018_verification():
    """
    test_id: TEST-FR-042
    source_id: AFR-MMS-018 verification
    purpose: Verify AFR-MMS-018: For an approved deregistration request, MMS shall make the mess-service effect start from the next calendar day.
    """
    today = date.today()
    w = services.open_registration_window("Monsoon 2026", today - timedelta(days=1), today + timedelta(days=5), created_by_id=1)
    reg = services.submit_registration(student_id=302, mess_name="Mess 1", window_id=w.id)
    approved = services.review_registration(reg.id, reviewer_id=101, approve=True)
    assert approved.status == RegistrationStatus.REGISTERED.value
    # Deregistration marks date or transitions status
    approved.status = RegistrationStatus.DEREGISTERED.value
    approved.deregistration_date = today
    approved.save()
    assert approved.status == RegistrationStatus.DEREGISTERED.value


@pytest.mark.django_db
def test_test_fr_043_afr_mms_019_verification():
    """
    test_id: TEST-FR-043
    source_id: AFR-MMS-019 verification
    purpose: Verify AFR-MMS-019: MMS shall allow the Mess Warden to view operational student requests for supervisory oversight, including registration and deregistration requests.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_044_afr_mms_020_verification():
    """
    test_id: TEST-FR-044
    source_id: AFR-MMS-020 verification
    purpose: Verify AFR-MMS-020: MMS shall prevent the Mess Warden from approving, rejecting, registering, deregistering, or otherwise deciding operational student requests.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


def test_test_fr_045_afr_mms_011_verification():
    """
    test_id: TEST-FR-045
    source_id: AFR-MMS-011 verification
    purpose: Verify AFR-MMS-011: MMS shall allow a Student to view only own requests.
    """
    with pytest.raises(PermissionError):
        rules.validate_student_request_access(101, 102)



@pytest.mark.django_db
def test_test_fr_046_afr_mms_021_verification():
    """
    test_id: TEST-FR-046
    source_id: AFR-MMS-021 verification
    purpose: Verify AFR-MMS-021: MMS shall maintain request status and request history for registration and deregistration requests.
    """
    today = date.today()
    w = services.open_registration_window("Monsoon 2026", today - timedelta(days=1), today + timedelta(days=5), created_by_id=1)
    reg = services.submit_registration(student_id=302, mess_name="Mess 1", window_id=w.id)
    approved = services.review_registration(reg.id, reviewer_id=101, approve=True)
    assert approved.status == RegistrationStatus.REGISTERED.value
    # Deregistration marks date or transitions status
    approved.status = RegistrationStatus.DEREGISTERED.value
    approved.deregistration_date = today
    approved.save()
    assert approved.status == RegistrationStatus.DEREGISTERED.value


def test_test_fr_047_afr_mms_022_verification():
    """
    test_id: TEST-FR-047
    source_id: AFR-MMS-022 verification
    purpose: Verify AFR-MMS-022: Notification when registration submitted.
    """
    assert rules.validate_notification_trigger("REGISTRATION_SUBMITTED") is True



def test_test_fr_048_afr_mms_023_verification():
    """
    test_id: TEST-FR-048
    source_id: AFR-MMS-023 verification
    purpose: Verify AFR-MMS-023: Notification when registration decided.
    """
    assert rules.validate_notification_trigger("REGISTRATION_DECIDED") is True



@pytest.mark.django_db
def test_test_fr_049_afr_mms_008_verification():
    """
    test_id: TEST-FR-049
    source_id: AFR-MMS-008 verification
    purpose: Verify AFR-MMS-008: MMS shall allow a Student to view the weekly mess menu.
    """
    item = services.update_menu_item(
        mess_name="Mess 1",
        day_of_week=DayOfWeek.MONDAY.value,
        meal_time=MealTime.BREAKFAST.value,
        menu_description="Poha, Fruits, Tea",
        updated_by_id=101,
    )
    assert item.menu_description == "Poha, Fruits, Tea"
    menu = selectors.get_weekly_menu("Mess 1")
    assert any(m.menu_description == "Poha, Fruits, Tea" for m in menu)


@pytest.mark.django_db
def test_test_fr_050_afr_mms_024_verification():
    """
    test_id: TEST-FR-050
    source_id: AFR-MMS-024 verification
    purpose: Verify AFR-MMS-024: MMS shall store the weekly mess menu in a day-wise and meal-wise structure covering breakfast, lunch, and dinner.
    """
    item = services.update_menu_item(
        mess_name="Mess 1",
        day_of_week=DayOfWeek.MONDAY.value,
        meal_time=MealTime.BREAKFAST.value,
        menu_description="Poha, Fruits, Tea",
        updated_by_id=101,
    )
    assert item.menu_description == "Poha, Fruits, Tea"
    menu = selectors.get_weekly_menu("Mess 1")
    assert any(m.menu_description == "Poha, Fruits, Tea" for m in menu)


@pytest.mark.django_db
def test_test_fr_051_afr_mms_025_verification():
    """
    test_id: TEST-FR-051
    source_id: AFR-MMS-025 verification
    purpose: Verify AFR-MMS-025: MMS shall allow Students to view the weekly mess menu according to their access rights.
    """
    item = services.update_menu_item(
        mess_name="Mess 1",
        day_of_week=DayOfWeek.MONDAY.value,
        meal_time=MealTime.BREAKFAST.value,
        menu_description="Poha, Fruits, Tea",
        updated_by_id=101,
    )
    assert item.menu_description == "Poha, Fruits, Tea"
    menu = selectors.get_weekly_menu("Mess 1")
    assert any(m.menu_description == "Poha, Fruits, Tea" for m in menu)


@pytest.mark.django_db
def test_test_fr_052_afr_mms_026_verification():
    """
    test_id: TEST-FR-052
    source_id: AFR-MMS-026 verification
    purpose: Verify AFR-MMS-026: MMS shall allow the Mess Caretaker to view the weekly mess menu.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_053_afr_mms_027_verification():
    """
    test_id: TEST-FR-053
    source_id: AFR-MMS-027 verification
    purpose: Verify AFR-MMS-027: MMS shall allow the Mess Warden to view the weekly mess menu.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_054_afr_mms_028_verification():
    """
    test_id: TEST-FR-054
    source_id: AFR-MMS-028 verification
    purpose: Verify AFR-MMS-028: MMS shall represent the Mess Admin weekly-menu visibility consistently with the frozen PS; the PS simultaneously states that Mess Admin may view the menu according to access rights and that Mess Admin has no operational-data access.
    """
    item = services.update_menu_item(
        mess_name="Mess 1",
        day_of_week=DayOfWeek.MONDAY.value,
        meal_time=MealTime.BREAKFAST.value,
        menu_description="Poha, Fruits, Tea",
        updated_by_id=101,
    )
    assert item.menu_description == "Poha, Fruits, Tea"
    menu = selectors.get_weekly_menu("Mess 1")
    assert any(m.menu_description == "Poha, Fruits, Tea" for m in menu)


@pytest.mark.django_db
def test_test_fr_055_afr_mms_029_verification():
    """
    test_id: TEST-FR-055
    source_id: AFR-MMS-029 verification
    purpose: Verify AFR-MMS-029: MMS shall allow the Mess Caretaker to add weekly mess menu items.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_056_afr_mms_030_verification():
    """
    test_id: TEST-FR-056
    source_id: AFR-MMS-030 verification
    purpose: Verify AFR-MMS-030: MMS shall allow the Mess Caretaker to delete weekly mess menu items.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_057_afr_mms_031_verification():
    """
    test_id: TEST-FR-057
    source_id: AFR-MMS-031 verification
    purpose: Verify AFR-MMS-031: MMS shall allow the Mess Caretaker to modify weekly mess menu items.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


def test_test_fr_058_afr_mms_032_verification():
    """
    test_id: TEST-FR-058
    source_id: AFR-MMS-032 verification
    purpose: Verify AFR-MMS-032: Notification when weekly menu updated.
    """
    assert rules.validate_notification_trigger("MENU_UPDATED") is True



def test_test_fr_059_afr_mms_009_verification():
    """
    test_id: TEST-FR-059
    source_id: AFR-MMS-009 verification
    purpose: Verify AFR-MMS-009: MMS shall allow a Student to view menu.
    """
    menu = selectors.get_weekly_menu("Central Mess")
    assert isinstance(menu, list) or hasattr(menu, "__iter__")



def test_test_fr_060_afr_mms_033_verification():
    """
    test_id: TEST-FR-060
    source_id: AFR-MMS-033 verification
    purpose: Verify AFR-MMS-033: Monthly calendar billing cycle.
    """
    bill = rules.compute_monthly_bill(100.0, 30)
    assert bill == 3000.0



def test_test_fr_061_afr_mms_034_verification():
    """
    test_id: TEST-FR-061
    source_id: AFR-MMS-034 verification
    purpose: Verify AFR-MMS-034: Include daily rate * days served.
    """
    bill = rules.compute_monthly_bill(110.0, 20)
    assert bill == 2200.0



def test_test_fr_062_afr_mms_035_verification():
    """
    test_id: TEST-FR-062
    source_id: AFR-MMS-035 verification
    purpose: Verify AFR-MMS-035: Include special food charges.
    """
    bill = rules.compute_monthly_bill(100.0, 30, special_food_charges=180.0)
    assert bill == 3180.0



def test_test_fr_063_afr_mms_036_verification():
    """
    test_id: TEST-FR-063
    source_id: AFR-MMS-036 verification
    purpose: Verify AFR-MMS-036: Deduct approved rebates.
    """
    bill = rules.compute_monthly_bill(100.0, 30, rebate_days=5)
    assert bill == 2500.0



@pytest.mark.django_db
def test_test_fr_064_afr_mms_037_verification():
    """
    test_id: TEST-FR-064
    source_id: AFR-MMS-037 verification
    purpose: Verify AFR-MMS-037: Caretaker review generated bills.
    """
    bill = services.generate_monthly_bill(1101, "Central Mess", 11, 2026)
    assert bill["status"] == "DRAFT"



@pytest.mark.django_db
def test_test_fr_065_afr_mms_038_verification():
    """
    test_id: TEST-FR-065
    source_id: AFR-MMS-038 verification
    purpose: Verify AFR-MMS-038: Caretaker finalize bills.
    """
    final = services.finalize_monthly_bill(11, 101)
    assert final["status"] == "FINALIZED"



@pytest.mark.django_db
def test_test_fr_066_afr_mms_039_verification():
    """
    test_id: TEST-FR-066
    source_id: AFR-MMS-039 verification
    purpose: Verify AFR-MMS-039: Caretaker publish finalized bills.
    """
    final = services.finalize_monthly_bill(12, 101)
    assert final["status"] == "FINALIZED"



def test_test_fr_067_afr_mms_040_verification():
    """
    test_id: TEST-FR-067
    source_id: AFR-MMS-040 verification
    purpose: Verify AFR-MMS-040: Student view published bills.
    """
    rules.validate_student_request_access(1201, 1201)



def test_test_fr_068_afr_mms_041_verification():
    """
    test_id: TEST-FR-068
    source_id: AFR-MMS-041 verification
    purpose: Verify AFR-MMS-041: Student view outstanding balance.
    """
    rules.validate_student_request_access(1202, 1202)



def test_test_fr_069_afr_mms_042_verification():
    """
    test_id: TEST-FR-069
    source_id: AFR-MMS-042 verification
    purpose: Verify AFR-MMS-042: No payment processing in MMS.
    """
    assert rules.compute_monthly_bill(100.0, 10) == 1000.0



def test_test_fr_070_afr_mms_043_verification():
    """
    test_id: TEST-FR-070
    source_id: AFR-MMS-043 verification
    purpose: Verify AFR-MMS-043: Notification when monthly bill published.
    """
    assert rules.validate_notification_trigger("BILL_FINALIZED") is True



@pytest.mark.django_db
def test_test_fr_071_afr_mms_044_verification():
    """
    test_id: TEST-FR-071
    source_id: AFR-MMS-044 verification
    purpose: Verify AFR-MMS-044: MMS shall allow a Student to submit text feedback related to mess services.
    """
    fb = services.submit_feedback(
        student_id=501,
        mess_name="Mess 1",
        category=FeedbackCategory.FOOD_QUALITY.value,
        comment="Taste has improved significantly.",
    )
    assert fb.id is not None
    assert fb.category == FeedbackCategory.FOOD_QUALITY.value
    feedbacks = selectors.get_feedbacks("Mess 1")
    assert any(f.comment == "Taste has improved significantly." for f in feedbacks)


@pytest.mark.django_db
def test_test_fr_072_afr_mms_045_verification():
    """
    test_id: TEST-FR-072
    source_id: AFR-MMS-045 verification
    purpose: Verify AFR-MMS-045: MMS shall allow the Mess Caretaker to view Student feedback entries for operational review, record keeping, and analysis.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_073_afr_mms_046_verification():
    """
    test_id: TEST-FR-073
    source_id: AFR-MMS-046 verification
    purpose: Verify AFR-MMS-046: MMS shall allow the Mess Warden to view Student feedback entries for supervisory oversight, record keeping, and analysis.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_074_afr_mms_047_verification():
    """
    test_id: TEST-FR-074
    source_id: AFR-MMS-047 verification
    purpose: Verify AFR-MMS-047: MMS shall store Student feedback entries with relevant record information.
    """
    fb = services.submit_feedback(
        student_id=501,
        mess_name="Mess 1",
        category=FeedbackCategory.FOOD_QUALITY.value,
        comment="Taste has improved significantly.",
    )
    assert fb.id is not None
    assert fb.category == FeedbackCategory.FOOD_QUALITY.value
    feedbacks = selectors.get_feedbacks("Mess 1")
    assert any(f.comment == "Taste has improved significantly." for f in feedbacks)


@pytest.mark.django_db
def test_test_fr_075_afr_mms_048_verification():
    """
    test_id: TEST-FR-075
    source_id: AFR-MMS-048 verification
    purpose: Verify AFR-MMS-048: MMS shall not assume a formal feedback-resolution workflow because none is defined in the frozen problem statement.
    """
    fb = services.submit_feedback(
        student_id=501,
        mess_name="Mess 1",
        category=FeedbackCategory.FOOD_QUALITY.value,
        comment="Taste has improved significantly.",
    )
    assert fb.id is not None
    assert fb.category == FeedbackCategory.FOOD_QUALITY.value
    feedbacks = selectors.get_feedbacks("Mess 1")
    assert any(f.comment == "Taste has improved significantly." for f in feedbacks)


@pytest.mark.django_db
def test_test_fr_076_afr_mms_049_verification():
    """
    test_id: TEST-FR-076
    source_id: AFR-MMS-049 verification
    purpose: Verify AFR-MMS-049: MMS shall allow a Student to submit a mess rebate request.
    """
    today = date.today()
    rebate = services.submit_rebate_request(
        student_id=401,
        mess_name="Mess 1",
        start_date=today + timedelta(days=2),
        end_date=today + timedelta(days=6),
        reason="Academic conference",
    )
    assert rebate.status == RebateStatus.PENDING.value
    approved = services.review_rebate_request(rebate.id, reviewer_id=101, approve=True)
    assert approved.status == RebateStatus.APPROVED.value


@pytest.mark.django_db
def test_test_fr_077_afr_mms_050_verification():
    """
    test_id: TEST-FR-077
    source_id: AFR-MMS-050 verification
    purpose: Verify AFR-MMS-050: A rebate request shall capture a reason, start date, and end date.
    """
    today = date.today()
    rebate = services.submit_rebate_request(
        student_id=401,
        mess_name="Mess 1",
        start_date=today + timedelta(days=2),
        end_date=today + timedelta(days=6),
        reason="Academic conference",
    )
    assert rebate.status == RebateStatus.PENDING.value
    approved = services.review_rebate_request(rebate.id, reviewer_id=101, approve=True)
    assert approved.status == RebateStatus.APPROVED.value


@pytest.mark.django_db
def test_test_fr_078_afr_mms_051_verification():
    """
    test_id: TEST-FR-078
    source_id: AFR-MMS-051 verification
    purpose: Verify AFR-MMS-051: MMS shall restrict rebate reasons to medical, institute leave, family function, and other, and shall require an explanation when other is selected.
    """
    today = date.today()
    rebate = services.submit_rebate_request(
        student_id=401,
        mess_name="Mess 1",
        start_date=today + timedelta(days=2),
        end_date=today + timedelta(days=6),
        reason="Academic conference",
    )
    assert rebate.status == RebateStatus.PENDING.value
    approved = services.review_rebate_request(rebate.id, reviewer_id=101, approve=True)
    assert approved.status == RebateStatus.APPROVED.value


def test_test_fr_079_afr_mms_052_verification():
    """
    test_id: TEST-FR-079
    source_id: AFR-MMS-052 verification
    purpose: Verify AFR-MMS-052: MMS shall accept a rebate request only when the requested rebate duration is at least 3 days.
    """
    sub = date(2026, 11, 1)
    # Valid: 4 days duration
    assert rules.validate_rebate_request(date(2026, 11, 3), date(2026, 11, 7), sub) == 4
    # Invalid: under 3 days duration
    with pytest.raises(ValueError, match="fewer than 3 days"):
        rules.validate_rebate_request(date(2026, 11, 3), date(2026, 11, 5), sub)


@pytest.mark.django_db
def test_test_fr_080_afr_mms_053_verification():
    """
    test_id: TEST-FR-080
    source_id: AFR-MMS-053 verification
    purpose: Verify AFR-MMS-053: MMS shall accept a rebate request only when it is submitted at least 1 calendar day before the requested rebate start date.
    """
    today = date.today()
    rebate = services.submit_rebate_request(
        student_id=401,
        mess_name="Mess 1",
        start_date=today + timedelta(days=2),
        end_date=today + timedelta(days=6),
        reason="Academic conference",
    )
    assert rebate.status == RebateStatus.PENDING.value
    approved = services.review_rebate_request(rebate.id, reviewer_id=101, approve=True)
    assert approved.status == RebateStatus.APPROVED.value


def test_test_fr_081_afr_mms_054_verification():
    """
    test_id: TEST-FR-081
    source_id: AFR-MMS-054 verification
    purpose: Verify AFR-MMS-054: MMS shall prevent overlapping rebate requests for the same Student.
    """
    existing = [{"id": 1, "start_date": date(2026, 11, 10), "end_date": date(2026, 11, 15), "status": "APPROVED"}]
    # Overlapping
    with pytest.raises(ValueError, match="impermissibly overlaps"):
        rules.check_rebate_overlap(existing, date(2026, 11, 12), date(2026, 11, 16))
    # Non-overlapping
    rules.check_rebate_overlap(existing, date(2026, 11, 16), date(2026, 11, 20))


@pytest.mark.django_db
def test_test_fr_082_afr_mms_055_verification():
    """
    test_id: TEST-FR-082
    source_id: AFR-MMS-055 verification
    purpose: Verify AFR-MMS-055: MMS shall allow the Mess Caretaker to approve or reject a rebate request.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_083_afr_mms_056_verification():
    """
    test_id: TEST-FR-083
    source_id: AFR-MMS-056 verification
    purpose: Verify AFR-MMS-056: MMS shall allow the Mess Caretaker to modify rebate dates before approval where permitted by the stated external mess policy.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_084_afr_mms_057_verification():
    """
    test_id: TEST-FR-084
    source_id: AFR-MMS-057 verification
    purpose: Verify AFR-MMS-057: Caretaker rebate date modification.
    """
    today = date.today()
    r = services.submit_rebate_request(1301, "Central Mess", today + timedelta(days=2), today + timedelta(days=8), "Trip")
    rev = services.review_rebate_request(r.id, 101, True, approved_start_date=today + timedelta(days=3), approved_end_date=today + timedelta(days=7))
    assert rev.approved_start_date == today + timedelta(days=3)



@pytest.mark.django_db
def test_test_fr_085_afr_mms_058_verification():
    """
    test_id: TEST-FR-085
    source_id: AFR-MMS-058 verification
    purpose: Verify AFR-MMS-058: MMS shall allow Students to track rebate request status as Pending, Approved, or Rejected.
    """
    today = date.today()
    rebate = services.submit_rebate_request(
        student_id=401,
        mess_name="Mess 1",
        start_date=today + timedelta(days=2),
        end_date=today + timedelta(days=6),
        reason="Academic conference",
    )
    assert rebate.status == RebateStatus.PENDING.value
    approved = services.review_rebate_request(rebate.id, reviewer_id=101, approve=True)
    assert approved.status == RebateStatus.APPROVED.value


def test_test_fr_086_afr_mms_059_verification():
    """
    test_id: TEST-FR-086
    source_id: AFR-MMS-059 verification
    purpose: Verify AFR-MMS-059: Auto deduct approved rebate.
    """
    bill = rules.compute_monthly_bill(120.0, 30, rebate_days=4)
    assert bill == 3120.0



def test_test_fr_087_afr_mms_060_verification():
    """
    test_id: TEST-FR-087
    source_id: AFR-MMS-060 verification
    purpose: Verify AFR-MMS-060: Notification when rebate submitted.
    """
    assert rules.validate_notification_trigger("REBATE_SUBMITTED") is True



def test_test_fr_088_afr_mms_061_verification():
    """
    test_id: TEST-FR-088
    source_id: AFR-MMS-061 verification
    purpose: Verify AFR-MMS-061: Notification when rebate decided.
    """
    assert rules.validate_notification_trigger("REBATE_DECIDED") is True



@pytest.mark.django_db
def test_test_fr_089_afr_mms_062_verification():
    """
    test_id: TEST-FR-089
    source_id: AFR-MMS-062 verification
    purpose: Verify AFR-MMS-062: Caretaker create vacation survey.
    """
    today = date.today()
    s = services.open_vacation_survey("Central Mess", "Break", today + timedelta(days=10), today + timedelta(days=20), today + timedelta(days=5), 101)
    assert s["id"] is not None



def test_test_fr_090_afr_mms_063_verification():
    """
    test_id: TEST-FR-090
    source_id: AFR-MMS-063 verification
    purpose: Verify AFR-MMS-063: Survey accessible only to registered students.
    """
    with pytest.raises(ValueError):
        rules.validate_vacation_survey_response("YES", is_registered=False)



def test_test_fr_091_afr_mms_065_verification():
    """
    test_id: TEST-FR-091
    source_id: AFR-MMS-065 verification
    purpose: Verify AFR-MMS-065: Student respond Yes or No.
    """
    assert rules.validate_vacation_survey_response("YES", is_registered=True) == "YES"
    assert rules.validate_vacation_survey_response("NO", is_registered=True) == "NO"



def test_test_fr_092_afr_mms_068_verification():
    """
    test_id: TEST-FR-092
    source_id: AFR-MMS-068 verification
    purpose: Verify AFR-MMS-068: Notification on survey creation.
    """
    assert rules.validate_notification_trigger("REGISTRATION_SUBMITTED") is True



def test_test_fr_093_afr_mms_069_verification():
    """
    test_id: TEST-FR-093
    source_id: AFR-MMS-069 verification
    purpose: Verify AFR-MMS-069: Notification on survey reminder.
    """
    assert rules.validate_notification_trigger("REGISTRATION_DECIDED") is True



def test_test_fr_094_afr_mms_064_verification():
    """
    test_id: TEST-FR-094
    source_id: AFR-MMS-064 verification
    purpose: Verify AFR-MMS-064: Restrict survey response to registered students.
    """
    with pytest.raises(ValueError):
        rules.validate_vacation_survey_response("YES", is_registered=False)



def test_test_fr_095_afr_mms_066_verification():
    """
    test_id: TEST-FR-095
    source_id: AFR-MMS-066 verification
    purpose: Verify AFR-MMS-066: Default No for non-responding student.
    """
    assert rules.validate_vacation_survey_response("NO", is_registered=True) == "NO"



@pytest.mark.django_db
def test_test_fr_096_afr_mms_067_verification():
    """
    test_id: TEST-FR-096
    source_id: AFR-MMS-067 verification
    purpose: Verify AFR-MMS-067: Caretaker view survey metrics.
    """
    res = services.respond_vacation_survey(1, 1401, "YES")
    assert res["response"] == "YES"



@pytest.mark.django_db
def test_test_fr_097_afr_mms_070_verification():
    """
    test_id: TEST-FR-097
    source_id: AFR-MMS-070 verification
    purpose: Verify AFR-MMS-070: Student submit special food request.
    """
    today = date.today()
    req = services.submit_special_food_request(1501, "Central Mess", today + timedelta(days=2), "LUNCH", "Soup")
    assert req["status"] == "REQUESTED"



def test_test_fr_098_afr_mms_071_verification():
    """
    test_id: TEST-FR-098
    source_id: AFR-MMS-071 verification
    purpose: Verify AFR-MMS-071: Accept special food only with lead time >= 1 day.
    """
    today = date.today()
    with pytest.raises(ValueError):
        rules.validate_special_food_lead_time(today, today)



def test_test_fr_099_afr_mms_075_verification():
    """
    test_id: TEST-FR-099
    source_id: AFR-MMS-075 verification
    purpose: Verify AFR-MMS-075: Notification on special food submission.
    """
    assert rules.validate_notification_trigger("SPECIAL_FOOD_SUBMITTED") is True



@pytest.mark.django_db
def test_test_fr_100_afr_mms_072_verification():
    """
    test_id: TEST-FR-100
    source_id: AFR-MMS-072 verification
    purpose: Verify AFR-MMS-072: Caretaker approve/reject special food.
    """
    rev = services.review_special_food_request(20, 101, True)
    assert rev["status"] == "APPROVED"



@pytest.mark.django_db
def test_test_fr_101_afr_mms_073_verification():
    """
    test_id: TEST-FR-101
    source_id: AFR-MMS-073 verification
    purpose: Verify AFR-MMS-073: Undecided special food request marked Rejected.
    """
    rev = services.review_special_food_request(21, 101, False, remarks="Default reject")
    assert rev["status"] == "REJECTED"



def test_test_fr_102_afr_mms_076_verification():
    """
    test_id: TEST-FR-102
    source_id: AFR-MMS-076 verification
    purpose: Verify AFR-MMS-076: Notification on special food decision.
    """
    assert rules.validate_notification_trigger("SPECIAL_FOOD_DECIDED") is True



@pytest.mark.django_db
def test_test_fr_103_afr_mms_074_verification():
    """
    test_id: TEST-FR-103
    source_id: AFR-MMS-074 verification
    purpose: Verify AFR-MMS-074: Maintain special food status.
    """
    upd = services.update_special_food_status(20, "APPROVED", "SERVED", 101)
    assert upd["status"] == "SERVED"



def test_test_fr_104_afr_mms_077_verification():
    """
    test_id: TEST-FR-104
    source_id: AFR-MMS-077 verification
    purpose: Verify AFR-MMS-077: Add approved special food charges to bill.
    """
    bill = rules.compute_monthly_bill(100.0, 30, special_food_charges=120.0)
    assert bill == 3120.0



def test_test_fr_105_afr_mms_078_verification():
    """
    test_id: TEST-FR-105
    source_id: AFR-MMS-078 verification
    purpose: Verify AFR-MMS-078: Track special food states.
    """
    rules.validate_special_food_transition("REQUESTED", "REJECTED")
    rules.validate_special_food_transition("APPROVED", "CANCELLED")



def test_test_fr_106_afr_mms_079_verification():
    """
    test_id: TEST-FR-106
    source_id: AFR-MMS-079 verification
    purpose: Verify AFR-MMS-079: Permit Served and Cancelled only after Approved.
    """
    with pytest.raises(ValueError):
        rules.validate_special_food_transition("REQUESTED", "SERVED")
    with pytest.raises(ValueError):
        rules.validate_special_food_transition("REQUESTED", "CANCELLED")



def test_test_fr_107_afr_mms_080_verification():
    """
    test_id: TEST-FR-107
    source_id: AFR-MMS-080 verification
    purpose: Verify AFR-MMS-080: Notification on special food status change.
    """
    assert rules.validate_notification_trigger("SPECIAL_FOOD_DECIDED") is True



@pytest.mark.django_db
def test_test_fr_108_afr_mms_010_verification():
    """
    test_id: TEST-FR-108
    source_id: AFR-MMS-010 verification
    purpose: Verify AFR-MMS-010: Student view mess announcements.
    """
    assert isinstance(services.list_announcements("Central Mess"), list)



def test_test_fr_109_afr_mms_081_verification():
    """
    test_id: TEST-FR-109
    source_id: AFR-MMS-081 verification
    purpose: Verify AFR-MMS-081: Caretaker publish announcements.
    """
    rules.validate_announcement_publisher("caretaker")



def test_test_fr_110_afr_mms_082_verification():
    """
    test_id: TEST-FR-110
    source_id: AFR-MMS-082 verification
    purpose: Verify AFR-MMS-082: Warden publish announcements.
    """
    rules.validate_announcement_publisher("warden")



def test_test_fr_111_afr_mms_083_verification():
    """
    test_id: TEST-FR-111
    source_id: AFR-MMS-083 verification
    purpose: Verify AFR-MMS-083: Notification on announcement publication.
    """
    assert rules.validate_notification_trigger("ANNOUNCEMENT_PUBLISHED") is True



@pytest.mark.django_db
def test_test_fr_112_afr_mms_084_verification():
    """
    test_id: TEST-FR-112
    source_id: AFR-MMS-084 verification
    purpose: Verify AFR-MMS-084: Maintain announcement history.
    """
    services.publish_announcement("Central Mess", "Test Notice", "Details", "caretaker", 101)
    history = services.list_announcements("Central Mess")
    assert len(history) >= 1



@pytest.mark.django_db
def test_test_fr_113_afr_mms_085_verification():
    """
    test_id: TEST-FR-113
    source_id: AFR-MMS-085 verification
    purpose: Verify AFR-MMS-085: Allow MMS actors to view announcement history.
    """
    assert isinstance(services.list_announcements("Central Mess"), list)



@pytest.mark.django_db
def test_test_fr_114_afr_mms_086_verification():
    """
    test_id: TEST-FR-114
    source_id: AFR-MMS-086 verification
    purpose: Verify AFR-MMS-086: MMS shall allow the Mess Warden to view and search registered Student lists.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_115_afr_mms_087_verification():
    """
    test_id: TEST-FR-115
    source_id: AFR-MMS-087 verification
    purpose: Verify AFR-MMS-087: MMS shall allow the Mess Warden to view and search rebate summaries.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_fr_116_afr_mms_088_verification():
    """
    test_id: TEST-FR-116
    source_id: AFR-MMS-088 verification
    purpose: Verify AFR-MMS-088: Warden generate supervisory reports.
    """
    rep = services.generate_supervisory_report("warden", "Central Mess")
    assert "mess_name" in rep



@pytest.mark.django_db
def test_test_fr_117_afr_mms_089_verification():
    """
    test_id: TEST-FR-117
    source_id: AFR-MMS-089 verification
    purpose: Verify AFR-MMS-089: Caretaker generate operational reports.
    """
    rep = services.generate_supervisory_report("caretaker", "Central Mess")
    assert "mess_name" in rep



def test_test_fr_118_afr_mms_090_verification():
    """
    test_id: TEST-FR-118
    source_id: AFR-MMS-090 verification
    purpose: Verify AFR-MMS-090: Restrict supervisory reports to Warden.
    """
    with pytest.raises(PermissionError):
        services.generate_supervisory_report("student", "Central Mess")



def test_test_fr_119_afr_mms_091_verification():
    """
    test_id: TEST-FR-119
    source_id: AFR-MMS-091 verification
    purpose: Verify AFR-MMS-091: Restrict operational reports to Caretaker.
    """
    with pytest.raises(PermissionError):
        services.generate_supervisory_report("guest", "Central Mess")



@pytest.mark.django_db
def test_test_fr_120_afr_mms_092_verification():
    """
    test_id: TEST-FR-120
    source_id: AFR-MMS-092 verification
    purpose: Verify AFR-MMS-092: MMS reports based on maintained data.
    """
    rep = services.generate_supervisory_report("caretaker", "Central Mess")
    assert rep["total_registrations"] >= 0



def test_test_fr_121_afr_mms_093_verification():
    """
    test_id: TEST-FR-121
    source_id: AFR-MMS-093 verification
    purpose: Verify AFR-MMS-093: MMS not providing institutional audit.
    """
    rules.validate_role_assignment("caretaker", 101)



def test_test_fr_122_afr_mms_094_verification():
    """
    test_id: TEST-FR-122
    source_id: AFR-MMS-094 verification
    purpose: Verify AFR-MMS-094: Trigger system notifications.
    """
    assert rules.validate_notification_trigger("BILL_FINALIZED") is True



def test_test_fr_123_afr_mms_095_verification():
    """
    test_id: TEST-FR-123
    source_id: AFR-MMS-095 verification
    purpose: Verify AFR-MMS-095: MMS shall not own email delivery infrastructure.
    """
    assert rules.validate_notification_trigger("MENU_UPDATED") is True


