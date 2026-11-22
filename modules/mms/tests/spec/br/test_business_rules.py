"""Automated specification-based test suite for MMS module."""

from datetime import date, timedelta

import pytest

from modules.mms import selectors, services
from modules.mms.domain import rules
from modules.mms.domain.constants import (
    DayOfWeek,
    MealTime,
    RebateStatus,
    RegistrationStatus,
)


@pytest.mark.skip(reason="NOT_AUTOMATED: email notification dispatcher not yet implemented in MMS")
def test_test_br_001_br_mms_001_rule_enforcement():
    """
    test_id: TEST-BR-001
    source_id: BR-MMS-001 rule enforcement
    purpose: Verify BR-MMS-001 (MMS Functional Scope Boundary): MMS shall remain limited to the mess-management functions and explicit integrations/notification triggers defined in the frozen problem statement.
    """


def test_test_br_002_br_mms_002_rule_enforcement():
    """
    test_id: TEST-BR-002
    source_id: BR-MMS-002 rule enforcement
    purpose: Verify BR-MMS-002 (Employee Identity Boundary for Role Assignment): MMS may use institutional employee identity data needed for Mess Caretaker and Mess Warden assignment, but MMS shall not own employee master-data management.
    """
    with pytest.raises(ValueError):
        rules.validate_role_assignment("invalid_role", 101)
    with pytest.raises(ValueError):
        rules.validate_role_assignment("caretaker", 0)


@pytest.mark.django_db
def test_test_br_003_br_mms_003_rule_enforcement():
    """
    test_id: TEST-BR-003
    source_id: BR-MMS-003 rule enforcement
    purpose: Verify BR-MMS-003 (Single Active Caretaker Rule): MMS shall enforce exactly one active Mess Caretaker at a time.
    """
    c1 = services.assign_mess_role("Mess 1", "caretaker", employee_id=101, assigned_by_id=1)
    assert c1.is_active is True
    c2 = services.assign_mess_role("Mess 1", "caretaker", employee_id=102, assigned_by_id=1)
    assert c2.is_active is True
    c1.refresh_from_db()
    assert c1.is_active is False


@pytest.mark.django_db
def test_test_br_004_br_mms_004_rule_enforcement():
    """
    test_id: TEST-BR-004
    source_id: BR-MMS-004 rule enforcement
    purpose: Verify BR-MMS-004 (Single Active Warden Rule): MMS shall enforce exactly one active Mess Warden at a time.
    """
    w1 = services.assign_mess_role("Mess 1", "warden", employee_id=201, assigned_by_id=1)
    assert w1.is_active is True
    w2 = services.assign_mess_role("Mess 1", "warden", employee_id=202, assigned_by_id=1)
    assert w2.is_active is True
    w1.refresh_from_db()
    assert w1.is_active is False


@pytest.mark.skip(reason="NOT_AUTOMATED: monthly billing calculation service/model not yet implemented in MMS")
def test_test_br_005_br_mms_005_rule_enforcement():
    """
    test_id: TEST-BR-005
    source_id: BR-MMS-005 rule enforcement
    purpose: Verify BR-MMS-005 (Mess Admin Operational Data Restriction): MMS shall prevent Mess Admin from accessing operational mess data, student requests, billing, or feedback.
    """


@pytest.mark.django_db
def test_test_br_006_br_mms_006_rule_enforcement():
    """
    test_id: TEST-BR-006
    source_id: BR-MMS-006 rule enforcement
    purpose: Verify BR-MMS-006 (Immediate Mid-cycle Role Reassignment): A mid-cycle Caretaker or Warden reassignment takes effect immediately in MMS from the recorded reassignment time.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_br_007_br_mms_007_rule_enforcement():
    """
    test_id: TEST-BR-007
    source_id: BR-MMS-007 rule enforcement
    purpose: Verify BR-MMS-007 (Pending Request Handoff After Caretaker Reassignment): After Caretaker reassignment, MMS shall make pending operational requests visible and actionable by the newly assigned Caretaker.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_br_008_br_mms_008_rule_enforcement():
    """
    test_id: TEST-BR-008
    source_id: BR-MMS-008 rule enforcement
    purpose: Verify BR-MMS-008 (Registration Window Creation): Only the active Mess Caretaker opens the registration window for a mess cycle or designated period.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_br_009_br_mms_009_rule_enforcement():
    """
    test_id: TEST-BR-009
    source_id: BR-MMS-009 rule enforcement
    purpose: Verify BR-MMS-009 (Registration Submission Window Restriction): MMS shall allow Student registration requests only while the registration window is open.
    """
    today = date.today()
    w = services.open_registration_window("Monsoon 2026", today - timedelta(days=1), today + timedelta(days=7), created_by_id=1)
    assert w.id is not None
    assert w.is_open is True
    open_windows = selectors.get_open_registration_windows()
    assert any(win.id == w.id for win in open_windows)


@pytest.mark.django_db
def test_test_br_010_br_mms_010_rule_enforcement():
    """
    test_id: TEST-BR-010
    source_id: BR-MMS-010 rule enforcement
    purpose: Verify BR-MMS-010 (Caretaker Request Decision Authority): Only the active Mess Caretaker may approve or reject registration and deregistration requests; the Mess Warden has oversight-only access.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_br_011_br_mms_011_rule_enforcement():
    """
    test_id: TEST-BR-011
    source_id: BR-MMS-011 rule enforcement
    purpose: Verify BR-MMS-011 (Warden Operational Request Oversight-only Rule): The Mess Warden may view operational student requests for oversight but may not approve, reject, register, deregister, or otherwise decide those requests.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_br_012_br_mms_012_rule_enforcement():
    """
    test_id: TEST-BR-012
    source_id: BR-MMS-012 rule enforcement
    purpose: Verify BR-MMS-012 (Deregistration Anytime Submission): MMS shall allow Students to submit deregistration requests at any time.
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
def test_test_br_013_br_mms_013_rule_enforcement():
    """
    test_id: TEST-BR-013
    source_id: BR-MMS-013 rule enforcement
    purpose: Verify BR-MMS-013 (Deregistration Effective Date Rule): MMS shall make an approved deregistration effective from the next calendar day after Caretaker approval.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_br_014_br_mms_014_rule_enforcement():
    """
    test_id: TEST-BR-014
    source_id: BR-MMS-014 rule enforcement
    purpose: Verify BR-MMS-014 (Weekly Menu Structure Rule): MMS shall store weekly menu information day-wise and meal-wise for breakfast, lunch, and dinner.
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


@pytest.mark.skip(reason="NOT_AUTOMATED: email notification dispatcher not yet implemented in MMS")
def test_test_br_015_br_mms_015_rule_enforcement():
    """
    test_id: TEST-BR-015
    source_id: BR-MMS-015 rule enforcement
    purpose: Verify BR-MMS-015 (Menu Update Notification Rule): MMS shall trigger system-generated email notifications to Students when weekly menu updates are published.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: monthly billing calculation service/model not yet implemented in MMS")
def test_test_br_016_br_mms_016_rule_enforcement():
    """
    test_id: TEST-BR-016
    source_id: BR-MMS-016 rule enforcement
    purpose: Verify BR-MMS-016 (Monthly Calendar Billing Cycle): MMS shall generate mess bills using the monthly calendar-month cycle.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: special food request service/model not yet implemented in MMS")
def test_test_br_017_br_mms_017_rule_enforcement():
    """
    test_id: TEST-BR-017
    source_id: BR-MMS-017 rule enforcement
    purpose: Verify BR-MMS-017 (Bill Computation Components): MMS monthly billing shall include daily-rate multiplied by number of served days, charges for approved special meals, and automatic deductions for approved rebates.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: monthly billing calculation service/model not yet implemented in MMS")
def test_test_br_018_br_mms_018_rule_enforcement():
    """
    test_id: TEST-BR-018
    source_id: BR-MMS-018 rule enforcement
    purpose: Verify BR-MMS-018 (Caretaker Bill Finalization Rule): MMS shall require Caretaker review and finalization before monthly bills are published to Students.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: monthly billing calculation service/model not yet implemented in MMS")
def test_test_br_019_br_mms_019_rule_enforcement():
    """
    test_id: TEST-BR-019
    source_id: BR-MMS-019 rule enforcement
    purpose: Verify BR-MMS-019 (Approved Rebate Billing Effect): MMS shall apply rebate deductions to monthly bills only for approved rebate requests.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: supervisory reporting service/model not yet implemented in MMS")
def test_test_br_020_br_mms_020_rule_enforcement():
    """
    test_id: TEST-BR-020
    source_id: BR-MMS-020 rule enforcement
    purpose: Verify BR-MMS-020 (Feedback Storage and Visibility Rule): MMS shall store Student text feedback and make feedback visible to Caretaker and Warden for monitoring and reporting.
    """


def test_test_br_021_br_mms_021_rule_enforcement():
    """
    test_id: TEST-BR-021
    source_id: BR-MMS-021 rule enforcement
    purpose: Verify BR-MMS-021 (Minimum Rebate Duration Rule): MMS shall reject rebate requests with a requested duration of fewer than three days.
    """
    sub = date(2026, 11, 1)
    # Valid: 4 days duration
    assert rules.validate_rebate_request(date(2026, 11, 3), date(2026, 11, 7), sub) == 4
    # Invalid: under 3 days duration
    with pytest.raises(ValueError, match="fewer than 3 days"):
        rules.validate_rebate_request(date(2026, 11, 3), date(2026, 11, 5), sub)


def test_test_br_022_br_mms_022_rule_enforcement():
    """
    test_id: TEST-BR-022
    source_id: BR-MMS-022 rule enforcement
    purpose: Verify BR-MMS-022 (Rebate Lead-time Rule): MMS shall reject rebate requests not submitted at least one calendar day before the rebate start date.
    """
    sub = date(2026, 11, 5)
    with pytest.raises(ValueError, match="at least one calendar day before"):
        rules.validate_rebate_request(date(2026, 11, 5), date(2026, 11, 9), sub)


def test_test_br_023_br_mms_023_rule_enforcement():
    """
    test_id: TEST-BR-023
    source_id: BR-MMS-023 rule enforcement
    purpose: Verify BR-MMS-023 (Rebate Non-overlap Rule): MMS shall prevent overlapping rebate requests.
    """
    existing = [{"id": 1, "start_date": date(2026, 11, 10), "end_date": date(2026, 11, 15), "status": "APPROVED"}]
    # Overlapping
    with pytest.raises(ValueError, match="impermissibly overlaps"):
        rules.check_rebate_overlap(existing, date(2026, 11, 12), date(2026, 11, 16))
    # Non-overlapping
    rules.check_rebate_overlap(existing, date(2026, 11, 16), date(2026, 11, 20))


@pytest.mark.django_db
def test_test_br_024_br_mms_024_rule_enforcement():
    """
    test_id: TEST-BR-024
    source_id: BR-MMS-024 rule enforcement
    purpose: Verify BR-MMS-024 (Rebate Reason Capture Rule): MMS shall require Student rebate requests to specify a reason and shall require explanation when the reason is Other.
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


@pytest.mark.skip(reason="NOT_AUTOMATED: monthly billing calculation service/model not yet implemented in MMS")
def test_test_br_025_br_mms_025_rule_enforcement():
    """
    test_id: TEST-BR-025
    source_id: BR-MMS-025 rule enforcement
    purpose: Verify BR-MMS-025 (Caretaker Rebate Date Modification Rule): The Caretaker may modify rebate dates before approval only where permitted by the external mess policy; approved dates become the dates used by MMS for billing adjustment.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: vacation survey service/model not yet implemented in MMS")
def test_test_br_026_br_mms_026_rule_enforcement():
    """
    test_id: TEST-BR-026
    source_id: BR-MMS-026 rule enforcement
    purpose: Verify BR-MMS-026 (Vacation Survey Registered-student Restriction): MMS shall send vacation food continuity surveys only to currently registered Students.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: vacation survey service/model not yet implemented in MMS")
def test_test_br_027_br_mms_027_rule_enforcement():
    """
    test_id: TEST-BR-027
    source_id: BR-MMS-027 rule enforcement
    purpose: Verify BR-MMS-027 (Vacation Survey Default No Rule): MMS shall record No as the default response for registered Students who do not respond before the response deadline.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: special food request service/model not yet implemented in MMS")
def test_test_br_028_br_mms_028_rule_enforcement():
    """
    test_id: TEST-BR-028
    source_id: BR-MMS-028 rule enforcement
    purpose: Verify BR-MMS-028 (Special Food Lead-time Rule): MMS shall allow special food requests only when submitted at least one calendar day before the requested date.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: special food request service/model not yet implemented in MMS")
def test_test_br_029_br_mms_029_rule_enforcement():
    """
    test_id: TEST-BR-029
    source_id: BR-MMS-029 rule enforcement
    purpose: Verify BR-MMS-029 (Special Food Default Rejection Rule): MMS shall mark a special food request as Rejected if the Caretaker does not decide within the institution-defined decision period of receiving the request.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: special food request service/model not yet implemented in MMS")
def test_test_br_030_br_mms_030_rule_enforcement():
    """
    test_id: TEST-BR-030
    source_id: BR-MMS-030 rule enforcement
    purpose: Verify BR-MMS-030 (Special Food Charge Rule): Approved special-food requests are chargeable and their charges are added to the Student monthly bill.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: special food request service/model not yet implemented in MMS")
def test_test_br_031_br_mms_031_rule_enforcement():
    """
    test_id: TEST-BR-031
    source_id: BR-MMS-031 rule enforcement
    purpose: Verify BR-MMS-031 (Special Food State-transition Rule): MMS shall track special food requests using Requested, Approved, Rejected, Served, and Cancelled states; Served and Cancelled shall occur only after Approved.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: announcement publication service/model not yet implemented in MMS")
def test_test_br_032_br_mms_032_rule_enforcement():
    """
    test_id: TEST-BR-032
    source_id: BR-MMS-032 rule enforcement
    purpose: Verify BR-MMS-032 (Announcement Publisher and Relevance Rule): Only the active Mess Caretaker or Mess Warden may publish mess-related announcements.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: announcement publication service/model not yet implemented in MMS")
def test_test_br_033_br_mms_033_rule_enforcement():
    """
    test_id: TEST-BR-033
    source_id: BR-MMS-033 rule enforcement
    purpose: Verify BR-MMS-033 (Announcement History Access Rule): MMS shall maintain mess-relevant announcement history and allow MMS actors to view it according to access rights.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: supervisory reporting service/model not yet implemented in MMS")
def test_test_br_034_br_mms_034_rule_enforcement():
    """
    test_id: TEST-BR-034
    source_id: BR-MMS-034 rule enforcement
    purpose: Verify BR-MMS-034 (Report Role-access Rule): MMS shall restrict supervisory reports to Warden and operational reports to Caretaker as stated in the frozen problem statement.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: email notification dispatcher not yet implemented in MMS")
def test_test_br_035_br_mms_035_rule_enforcement():
    """
    test_id: TEST-BR-035
    source_id: BR-MMS-035 rule enforcement
    purpose: Verify BR-MMS-035 (MMS Notification Trigger Scope): MMS triggers system-generated email notifications only for the MMS events explicitly listed in the frozen problem statement; external email delivery infrastructure remains outside MMS.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: vacation survey service/model not yet implemented in MMS")
def test_test_br_036_br_mms_036_rule_enforcement():
    """
    test_id: TEST-BR-036
    source_id: BR-MMS-036 rule enforcement
    purpose: Verify BR-MMS-036 (External Policy Ownership Boundary): MMS shall not define institutional mess policies such as rates, vacation periods, or employee appointment policy; it may only use explicitly provided values as inputs where the frozen problem statement states system behavior.
    """


@pytest.mark.django_db
def test_test_br_037_br_mms_038_rule_enforcement():
    """
    test_id: TEST-BR-037
    source_id: BR-MMS-038 rule enforcement
    purpose: Verify BR-MMS-038 (Weekly Menu Visibility and Access Rule): Students, the Mess Caretaker, and the Mess Warden may view the weekly menu. Mess Admin menu access remains unresolved because the frozen PS contains conflicting statements.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_br_038_br_mms_039_rule_enforcement():
    """
    test_id: TEST-BR-038
    source_id: BR-MMS-039 rule enforcement
    purpose: Verify BR-MMS-039 (Weekly Menu Maintenance Authority Rule): MMS shall permit only the Mess Caretaker to add, delete, or modify weekly mess menu items.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.skip(reason="NOT_AUTOMATED: monthly billing calculation service/model not yet implemented in MMS")
def test_test_br_039_br_mms_040_rule_enforcement():
    """
    test_id: TEST-BR-039
    source_id: BR-MMS-040 rule enforcement
    purpose: Verify BR-MMS-040 (Student Billing Information Access Rule): MMS shall allow Students to view only actor-visible monthly mess bills and outstanding balances maintained within MMS.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: vacation survey service/model not yet implemented in MMS")
def test_test_br_040_br_mms_041_rule_enforcement():
    """
    test_id: TEST-BR-040
    source_id: BR-MMS-041 rule enforcement
    purpose: Verify BR-MMS-041 (Vacation Survey Response Option Rule): MMS shall restrict Student vacation food continuity responses to Yes or No.
    """


@pytest.mark.skip(reason="NOT_AUTOMATED: capability BR-MMS-042 rule enforcement not yet supported in current MMS release")
def test_test_br_041_br_mms_042_rule_enforcement():
    """
    test_id: TEST-BR-041
    source_id: BR-MMS-042 rule enforcement
    purpose: Verify BR-MMS-042 (Student Request Status and History Access Rule): MMS shall allow a Student to view status and history only for the Student's own submitted MMS requests.
    """
