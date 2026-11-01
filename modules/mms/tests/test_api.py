"""API integration tests verifying endpoints, serializers, and permission grants."""

import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.mms.domain.constants import DayOfWeek, MealTime
from modules.mms.models import DailyMenuItem

pytestmark = pytest.mark.django_db


def test_student_menu_view(stub_iam):
    DailyMenuItem.objects.create(
        mess_name="Central Mess",
        day_of_week=DayOfWeek.MONDAY.value,
        meal_time=MealTime.BREAKFAST.value,
        items="Poha, Jalebi, Tea",
    )

    stub_iam(
        make_session(
            user_id=1001,
            modules=("mess_module",),
            permissions=("mess_module.menu.view",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    res = client.get("/api/v1/mms/menu/?mess_name=Central+Mess&day_of_week=MONDAY")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["meal_time"] == "BREAKFAST"
    assert "Poha" in data[0]["items"]


def test_student_submit_rebate(stub_iam):
    stub_iam(
        make_session(
            user_id=2001,
            modules=("mess_module",),
            permissions=("mess_module.rebate.apply",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    start = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
    end = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()

    payload = {
        "mess_name": "Central Mess",
        "start_date": start,
        "end_date": end,
        "reason": "Family vacation",
    }
    res = client.post("/api/v1/mms/rebates/apply/", payload, format="json")
    assert res.status_code == 201
    data = res.json()
    assert data["student_id"] == 2001
    assert data["status"] == "PENDING"
    assert data["duration_days"] == 4


def test_caretaker_manage_registration_window(stub_iam):
    stub_iam(
        make_session(
            user_id=3001,
            modules=("mess_module",),
            permissions=("mess_module.menu.view", "mess_module.registration.review"),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    start = datetime.date.today().isoformat()
    end = (datetime.date.today() + datetime.timedelta(days=15)).isoformat()

    payload = {
        "name": "Monsoon 2026 Window",
        "mess_name": "Central Mess",
        "start_date": start,
        "end_date": end,
    }
    res = client.post("/api/v1/mms/window/", payload, format="json")
    assert res.status_code == 201
    assert res.json()["name"] == "Monsoon 2026 Window"


def test_admin_assign_role(stub_iam):
    stub_iam(
        make_session(
            user_id=9001,
            modules=("mess_module",),
            permissions=("mess_module.role.manage",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    payload = {
        "employee_id": 4001,
        "role": "caretaker",
        "start_date": datetime.date.today().isoformat(),
        "remarks": "Appointed new caretaker",
    }
    res = client.post("/api/v1/mms/roles/", payload, format="json")
    assert res.status_code == 201
    assert res.json()["role"] == "caretaker"
    assert res.json()["employee_id"] == 4001
