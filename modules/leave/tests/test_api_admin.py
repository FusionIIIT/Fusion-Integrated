"""Leave administration: holiday calendar, offline records, policy (EL-UC-014/015/016)."""

from decimal import Decimal

import pytest

from modules.leave.models import Holiday, LeaveBalance, LeaveRequest

pytestmark = pytest.mark.django_db

URL = "/api/v1/leave"
ADMIN = ("leave.policy.manage", "leave.calendar.manage", "leave.offline.record")


def test_admin_adds_restricted_holiday(as_user):
    """EL-UC-015, BR-EL-031: the leave administrator publishes an RH."""
    r = as_user(900, *ADMIN, kind="staff").post(
        f"{URL}/holidays",
        {"date": "2030-08-15", "name": "Founders Day", "is_restricted": True, "is_published": True},
        format="json",
    )
    assert r.status_code == 201, r.content
    assert Holiday.objects.filter(name="Founders Day", is_restricted=True).exists()


def test_employee_cannot_add_holiday(as_user):
    """BR-EL-036: as_user(101, 'leave.request.create') POST holidays -> 403."""
    r = as_user(101, "leave.request.create").post(
        f"{URL}/holidays",
        {"date": "2030-08-15", "name": "Founders Day", "is_restricted": True, "is_published": True},
        format="json",
    )
    assert r.status_code == 403, r.content


def test_anyone_in_module_can_list_holidays(as_user):
    """Create a Holiday row with Holiday.objects.create(date='2030-01-26', name='Republic Day', is_restricted=False, is_published=True); as_user(101, 'leave.request.view_self') GET holidays -> 200 and 'Republic Day' in the names of r.json()['results']."""
    Holiday.objects.create(
        date="2030-01-26", name="Republic Day", is_restricted=False, is_published=True
    )
    r = as_user(101, "leave.request.view_self").get(f"{URL}/holidays")
    assert r.status_code == 200, r.content
    assert "Republic Day" in [holiday["name"] for holiday in r.json()["results"]]


def test_admin_records_offline_leave(as_user):
    """EL-UC-016, BR-EL-029: as_user(900, *ADMIN, kind='staff') POST offline-records {'user_id': 101, 'category': 'EL', 'start_date': '2030-05-04', 'end_date': '2030-05-08', 'days': '5', 'note': 'sanctioned on paper'} -> 201; LeaveRequest with user_id 101, is_offline True and status 'approved' exists; LeaveBalance EL for 101 year 2030 used == Decimal('5') — create that balance first with LeaveBalance.objects.create(user_id=101, year=2030, category='EL', entitled=Decimal('30'), used=Decimal('0'))."""
    LeaveBalance.objects.create(
        user_id=101, year=2030, category="EL", entitled=Decimal("30"), used=Decimal("0")
    )
    r = as_user(900, *ADMIN, kind="staff").post(
        f"{URL}/offline-records",
        {
            "user_id": 101,
            "category": "EL",
            "start_date": "2030-05-04",
            "end_date": "2030-05-08",
            "days": "5",
            "note": "sanctioned on paper",
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    assert LeaveRequest.objects.filter(user_id=101, is_offline=True, status="approved").exists()
    assert LeaveBalance.objects.get(user_id=101, year=2030, category="EL").used == Decimal("5")


def test_employee_cannot_record_offline_leave(as_user):
    """BR-EL-037: as_user(101, 'leave.request.create') POST offline-records -> 403."""
    r = as_user(101, "leave.request.create").post(
        f"{URL}/offline-records",
        {
            "user_id": 101,
            "category": "EL",
            "start_date": "2030-05-04",
            "end_date": "2030-05-08",
            "days": "5",
            "note": "sanctioned on paper",
        },
        format="json",
    )
    assert r.status_code == 403, r.content


def test_admin_saves_policy(as_user):
    """EL-UC-014, BR-EL-030: POST policies {'category': 'CL', 'annual_entitlement': '8.0', 'carries_forward': False, 'applies_to': 'all', 'is_active': True} -> 201 or 200."""
    r = as_user(900, *ADMIN, kind="staff").post(
        f"{URL}/policies",
        {
            "category": "CL",
            "annual_entitlement": "8.0",
            "carries_forward": False,
            "applies_to": "all",
            "is_active": True,
        },
        format="json",
    )
    assert r.status_code in (201, 200), r.content
