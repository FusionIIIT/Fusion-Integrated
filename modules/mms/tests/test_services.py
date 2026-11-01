"""Tests for MMS service transactions and invariant enforcement."""

import datetime

import pytest

from modules.mms.domain.constants import MessRole, RebateStatus, RegistrationStatus
from modules.mms.models import MessRoleAssignment
from modules.mms.services import mms as mms_services

pytestmark = pytest.mark.django_db


def test_assign_mess_role_deactivates_previous_active_assignment():
    """BR-MMS-003/004: Each mess has exactly one active caretaker and warden."""
    # First assignment
    a1 = mms_services.assign_mess_role(
        employee_id=101,
        role=MessRole.CARETAKER.value,
        start_date=datetime.date.today(),
        assigned_by_id=1,
    )
    assert a1.is_active is True

    # Reassign Caretaker to employee 102
    a2 = mms_services.assign_mess_role(
        employee_id=102,
        role=MessRole.CARETAKER.value,
        start_date=datetime.date.today(),
        assigned_by_id=1,
    )
    assert a2.is_active is True

    # Check a1 is now inactive
    a1.refresh_from_db()
    assert a1.is_active is False

    # Check active caretakers is exactly 1
    active = MessRoleAssignment.objects.filter(role=MessRole.CARETAKER.value, is_active=True)
    assert active.count() == 1
    assert active.first().employee_id == 102


def test_open_registration_window_closes_prior_active_window():
    """BR-MMS-008: Opening a registration window activates it and archives prior active windows."""
    w1 = mms_services.open_registration_window(
        opened_by_id=101,
        name="Monsoon 2026 Registration",
        start_date=datetime.date(2026, 11, 1),
        end_date=datetime.date(2026, 11, 15),
        mess_name="Central Mess",
    )
    assert w1.is_open is True

    w2 = mms_services.open_registration_window(
        opened_by_id=101,
        name="Winter 2026 Registration",
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 15),
        mess_name="Central Mess",
    )
    assert w2.is_open is True

    w1.refresh_from_db()
    assert w1.is_open is False


def test_submit_registration_success():
    mms_services.open_registration_window(
        opened_by_id=101,
        name="Current Window",
        start_date=datetime.date.today() - datetime.timedelta(days=1),
        end_date=datetime.date.today() + datetime.timedelta(days=10),
        mess_name="Central Mess",
    )

    reg = mms_services.submit_registration(
        student_id=5001,
        start_date=datetime.date.today() + datetime.timedelta(days=5),
        end_date=datetime.date.today() + datetime.timedelta(days=120),
        mess_name="Central Mess",
    )
    assert reg.status == RegistrationStatus.PENDING.value
    assert reg.student_id == 5001


def test_submit_registration_outside_window_fails():
    mms_services.open_registration_window(
        opened_by_id=101,
        name="Expired Window",
        start_date=datetime.date.today() - datetime.timedelta(days=10),
        end_date=datetime.date.today() - datetime.timedelta(days=2),
        mess_name="Central Mess",
    )

    with pytest.raises(ValueError, match="outside the open window"):
        mms_services.submit_registration(
            student_id=5002,
            start_date=datetime.date.today() + datetime.timedelta(days=5),
            mess_name="Central Mess",
        )


def test_rebate_lifecycle_and_review():
    sub_date = datetime.date.today()
    start = sub_date + datetime.timedelta(days=2)
    end = sub_date + datetime.timedelta(days=6)  # 5 days

    rebate = mms_services.submit_rebate_request(
        student_id=5001,
        start_date=start,
        end_date=end,
        reason="Attending Tech Conference",
        mess_name="Central Mess",
    )
    assert rebate.status == RebateStatus.PENDING.value
    assert rebate.duration_days == 5

    # Caretaker reviews and approves
    reviewed = mms_services.review_rebate_request(
        rebate_id=rebate.id,
        reviewed_by_id=101,
        approve=True,
        remarks="Approved as per conference invitation",
    )
    assert reviewed.status == RebateStatus.APPROVED.value
    assert reviewed.reviewed_by_id == 101
