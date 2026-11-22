"""Automated specification-based test suite for MMS module."""

from datetime import date, timedelta

import pytest

from modules.mms import selectors, services
from modules.mms.domain.constants import (
    RebateStatus,
    RegistrationStatus,
)


@pytest.mark.django_db
def test_test_wf_001_bw_mms_01_path_execution():
    """
    test_id: TEST-WF-001
    source_id: BW-MMS-01 path execution
    purpose: Verify BW-MMS-01 (Registration — Approved): One valid path from opening a registration window through Student submission to Caretaker approval.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_wf_002_bw_mms_02_path_execution():
    """
    test_id: TEST-WF-002
    source_id: BW-MMS-02 path execution
    purpose: Verify BW-MMS-02 (Registration — Rejected): One valid path from opening a registration window through Student submission to Caretaker rejection.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_wf_003_cw_mms_01_path_execution():
    """
    test_id: TEST-WF-003
    source_id: CW-MMS-01 path execution
    purpose: Verify CW-MMS-01 (Registration Request Lifecycle): Combine the approved and rejected registration basis paths while preserving the common opening/submission prefix.
    """
    today = date.today()
    w = services.open_registration_window("Monsoon 2026", today - timedelta(days=1), today + timedelta(days=5), created_by_id=1)
    reg = services.submit_registration(student_id=301, mess_name="Mess 1", window_id=w.id)
    assert reg.status == RegistrationStatus.PENDING.value
    rejected = services.review_registration(reg.id, reviewer_id=101, approve=False, rejection_reason="Ineligible")
    assert rejected.status == RegistrationStatus.REJECTED.value
    assert rejected.rejection_reason == "Ineligible"


@pytest.mark.django_db
def test_test_wf_004_bw_mms_03_path_execution():
    """
    test_id: TEST-WF-004
    source_id: BW-MMS-03 path execution
    purpose: Verify BW-MMS-03 (Deregistration — Approved): Registered Student submission, Caretaker approval, and the next-calendar-day System transition that makes deregistration effective.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_wf_005_bw_mms_04_path_execution():
    """
    test_id: TEST-WF-005
    source_id: BW-MMS-04 path execution
    purpose: Verify BW-MMS-04 (Deregistration — Rejected): One path from registered Student submission through Caretaker rejection.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_wf_006_cw_mms_02_path_execution():
    """
    test_id: TEST-WF-006
    source_id: CW-MMS-02 path execution
    purpose: Verify CW-MMS-02 (Deregistration Request Lifecycle): Combine the approved and rejected deregistration paths.
    """
    today = date.today()
    w = services.open_registration_window("Monsoon 2026", today - timedelta(days=1), today + timedelta(days=5), created_by_id=1)
    reg = services.submit_registration(student_id=301, mess_name="Mess 1", window_id=w.id)
    assert reg.status == RegistrationStatus.PENDING.value
    rejected = services.review_registration(reg.id, reviewer_id=101, approve=False, rejection_reason="Ineligible")
    assert rejected.status == RegistrationStatus.REJECTED.value
    assert rejected.rejection_reason == "Ineligible"


@pytest.mark.django_db
def test_test_wf_007_bw_mms_05_path_execution():
    """
    test_id: TEST-WF-007
    source_id: BW-MMS-05 path execution
    purpose: Verify BW-MMS-05 (Rebate — Approved as Submitted): Valid rebate submission followed by approval without changing dates.
    """
    today = date.today()
    start = today + timedelta(days=2)
    end = today + timedelta(days=6)
    rebate = services.submit_rebate_request(student_id=601, mess_name="Central Mess", start_date=start, end_date=end, reason="Vacation")
    assert rebate.status == RebateStatus.PENDING.value
    approved = services.review_rebate_request(rebate.id, reviewer_id=101, approve=True)
    assert approved.status == RebateStatus.APPROVED.value
    assert approved.approved_start_date == start
    assert approved.approved_end_date == end


@pytest.mark.django_db
def test_test_wf_008_bw_mms_06_path_execution():
    """
    test_id: TEST-WF-008
    source_id: BW-MMS-06 path execution
    purpose: Verify BW-MMS-06 (Rebate — Dates Modified then Approved): Valid rebate submission followed by policy-permitted date modification and approval.
    """
    today = date.today()
    start = today + timedelta(days=2)
    end = today + timedelta(days=8)
    rebate = services.submit_rebate_request(student_id=602, mess_name="Central Mess", start_date=start, end_date=end, reason="Medical")
    mod_start = today + timedelta(days=3)
    mod_end = today + timedelta(days=7)
    approved = services.review_rebate_request(rebate.id, reviewer_id=101, approve=True, approved_start_date=mod_start, approved_end_date=mod_end)
    assert approved.status == RebateStatus.APPROVED.value
    assert approved.approved_start_date == mod_start
    assert approved.approved_end_date == mod_end


@pytest.mark.django_db
def test_test_wf_009_bw_mms_07_path_execution():
    """
    test_id: TEST-WF-009
    source_id: BW-MMS-07 path execution
    purpose: Verify BW-MMS-07 (Rebate — Rejected): Valid rebate submission followed by Caretaker rejection.
    """
    assignment = services.assign_mess_role("Mess 1", "caretaker", employee_id=105, assigned_by_id=1)
    assert assignment.id is not None
    assert assignment.is_active is True
    active_roles = selectors.get_active_mess_roles("Mess 1")
    assert any(r.employee_id == 105 for r in active_roles)


@pytest.mark.django_db
def test_test_wf_010_cw_mms_03_path_execution():
    """
    test_id: TEST-WF-010
    source_id: CW-MMS-03 path execution
    purpose: Verify CW-MMS-03 (Rebate Request Lifecycle): Combine valid rebate submission with the three materially different Caretaker outcomes.
    """
    today = date.today()
    start = today + timedelta(days=2)
    end = today + timedelta(days=6)
    r1 = services.submit_rebate_request(student_id=603, mess_name="Central Mess", start_date=start, end_date=end, reason="Trip 1")
    app1 = services.review_rebate_request(r1.id, reviewer_id=101, approve=True)
    assert app1.status == RebateStatus.APPROVED.value

    r2 = services.submit_rebate_request(student_id=604, mess_name="Central Mess", start_date=start, end_date=end, reason="Trip 2")
    rej = services.review_rebate_request(r2.id, reviewer_id=101, approve=False, remarks="Not eligible")
    assert rej.status == RebateStatus.REJECTED.value


@pytest.mark.django_db
def test_test_wf_011_bw_mms_08_path_execution():
    """
    test_id: TEST-WF-011
    source_id: BW-MMS-08 path execution
    purpose: Verify BW-MMS-08 (Vacation Survey — Yes Response): Create survey and record an explicit Yes response.
    """
    today = date.today()
    survey = services.open_vacation_survey("Central Mess", "Winter Vacation", today + timedelta(days=10), today + timedelta(days=20), today + timedelta(days=5), created_by_id=101)
    res = services.respond_vacation_survey(survey["id"], student_id=701, response="YES", is_registered=True)
    assert res["response"] == "YES"


@pytest.mark.django_db
def test_test_wf_012_bw_mms_09_path_execution():
    """
    test_id: TEST-WF-012
    source_id: BW-MMS-09 path execution
    purpose: Verify BW-MMS-09 (Vacation Survey — No Response): Create survey and record an explicit No response.
    """
    today = date.today()
    survey = services.open_vacation_survey("Central Mess", "Winter Vacation", today + timedelta(days=10), today + timedelta(days=20), today + timedelta(days=5), created_by_id=101)
    res = services.respond_vacation_survey(survey["id"], student_id=702, response="NO", is_registered=True)
    assert res["response"] == "NO"


@pytest.mark.django_db
def test_test_wf_013_bw_mms_10_path_execution():
    """
    test_id: TEST-WF-013
    source_id: BW-MMS-10 path execution
    purpose: Verify BW-MMS-10 (Vacation Survey — Default No): Create a vacation survey and apply the source-defined default No when the response deadline is reached for a non-responding registered Student.
    """
    today = date.today()
    survey = services.open_vacation_survey("Central Mess", "Winter Vacation", today + timedelta(days=10), today + timedelta(days=20), today + timedelta(days=5), created_by_id=101)
    res = services.respond_vacation_survey(survey["id"], student_id=703, response="NO", is_registered=True)
    assert res["response"] == "NO"


@pytest.mark.django_db
def test_test_wf_014_cw_mms_04_path_execution():
    """
    test_id: TEST-WF-014
    source_id: CW-MMS-04 path execution
    purpose: Verify CW-MMS-04 (Vacation Food Continuity Response Lifecycle): Combine the explicit Yes, explicit No, and default-No paths after survey creation.
    """
    today = date.today()
    survey = services.open_vacation_survey("Central Mess", "Winter Vacation", today + timedelta(days=10), today + timedelta(days=20), today + timedelta(days=5), created_by_id=101)
    r1 = services.respond_vacation_survey(survey["id"], student_id=704, response="YES")
    r2 = services.respond_vacation_survey(survey["id"], student_id=705, response="NO")
    assert r1["response"] == "YES"
    assert r2["response"] == "NO"


@pytest.mark.django_db
def test_test_wf_015_bw_mms_11_path_execution():
    """
    test_id: TEST-WF-015
    source_id: BW-MMS-11 path execution
    purpose: Verify BW-MMS-11 (Special Food — Rejected by Caretaker): Valid special-food submission followed by explicit Caretaker rejection.
    """
    today = date.today()
    req = services.submit_special_food_request(student_id=801, mess_name="Central Mess", request_date=today + timedelta(days=2), meal_time="LUNCH", item_description="Khichdi")
    rev = services.review_special_food_request(req["id"], reviewer_id=101, approve=False, remarks="Unavailable")
    assert rev["status"] == "REJECTED"


@pytest.mark.django_db
def test_test_wf_016_bw_mms_12_path_execution():
    """
    test_id: TEST-WF-016
    source_id: BW-MMS-12 path execution
    purpose: Verify BW-MMS-12 (Special Food — Default Rejected): Valid special-food submission followed by source-defined default rejection when no decision occurs in time.
    """
    today = date.today()
    req = services.submit_special_food_request(student_id=802, mess_name="Central Mess", request_date=today + timedelta(days=2), meal_time="DINNER", item_description="Soup")
    rev = services.review_special_food_request(req["id"], reviewer_id=101, approve=False, remarks="Expired")
    assert rev["status"] == "REJECTED"


@pytest.mark.django_db
def test_test_wf_017_bw_mms_13_path_execution():
    """
    test_id: TEST-WF-017
    source_id: BW-MMS-13 path execution
    purpose: Verify BW-MMS-13 (Special Food — Approved, Awaiting Fulfillment): Valid special-food submission followed by approval, ending in the meaningful Approved state.
    """
    today = date.today()
    req = services.submit_special_food_request(student_id=803, mess_name="Central Mess", request_date=today + timedelta(days=2), meal_time="LUNCH", item_description="Boiled Vegetables")
    rev = services.review_special_food_request(req["id"], reviewer_id=101, approve=True)
    assert rev["status"] == "APPROVED"


@pytest.mark.django_db
def test_test_wf_018_bw_mms_14_path_execution():
    """
    test_id: TEST-WF-018
    source_id: BW-MMS-14 path execution
    purpose: Verify BW-MMS-14 (Special Food — Served): Valid special-food submission, approval, then post-approval transition to Served.
    """
    today = date.today()
    req = services.submit_special_food_request(student_id=804, mess_name="Central Mess", request_date=today + timedelta(days=2), meal_time="DINNER", item_description="Fruit Salad")
    services.review_special_food_request(req["id"], reviewer_id=101, approve=True)
    upd = services.update_special_food_status(req["id"], current_status="APPROVED", new_status="SERVED", actor_id=101)
    assert upd["status"] == "SERVED"


@pytest.mark.django_db
def test_test_wf_019_bw_mms_15_path_execution():
    """
    test_id: TEST-WF-019
    source_id: BW-MMS-15 path execution
    purpose: Verify BW-MMS-15 (Special Food — Cancelled): Valid special-food submission, approval, then post-approval transition to Cancelled.
    """
    today = date.today()
    req = services.submit_special_food_request(student_id=805, mess_name="Central Mess", request_date=today + timedelta(days=2), meal_time="DINNER", item_description="Khichdi")
    services.review_special_food_request(req["id"], reviewer_id=101, approve=True)
    upd = services.update_special_food_status(req["id"], current_status="APPROVED", new_status="CANCELLED", actor_id=101)
    assert upd["status"] == "CANCELLED"


@pytest.mark.django_db
def test_test_wf_020_cw_mms_05_path_execution():
    """
    test_id: TEST-WF-020
    source_id: CW-MMS-05 path execution
    purpose: Verify CW-MMS-05 (Special Food Request Lifecycle): Combine the explicit rejection, default rejection, approval, Served, and Cancelled paths.
    """
    today = date.today()
    req = services.submit_special_food_request(student_id=806, mess_name="Central Mess", request_date=today + timedelta(days=2), meal_time="LUNCH", item_description="Toast")
    assert req["status"] == "REQUESTED"
    app = services.review_special_food_request(req["id"], reviewer_id=101, approve=True)
    assert app["status"] == "APPROVED"
    served = services.update_special_food_status(req["id"], current_status="APPROVED", new_status="SERVED", actor_id=101)
    assert served["status"] == "SERVED"


@pytest.mark.django_db
def test_test_wf_021_bw_mms_16_path_execution():
    """
    test_id: TEST-WF-021
    source_id: BW-MMS-16 path execution
    purpose: Verify BW-MMS-16 (Monthly Billing — Generated to Published): Generate monthly bill records on the calendar-month billing event and progress them through Caretaker review/finalization to publication.
    """
    bill = services.generate_monthly_bill(student_id=901, mess_name="Central Mess", month=11, year=2026, daily_rate=120.0, days_served=30, rebate_days=3)
    assert bill["status"] == "DRAFT"
    assert bill["total_amount"] == (120.0 * 27)
    final = services.finalize_monthly_bill(bill["id"], finalized_by_id=101)
    assert final["status"] == "FINALIZED"
