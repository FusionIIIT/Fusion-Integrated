"""API integration tests verifying endpoints, serializers, and permission grants."""
import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.mms.domain.constants import DayOfWeek, MealTime
from modules.mms.models import DailyMenuItem

pytestmark = pytest.mark.django_db


def test_student_menu_view(stub_iam):
    # Seed menu item
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


def test_role_assignment_get_and_active_roles(stub_iam):
    stub_iam(
        make_session(
            user_id=9001,
            modules=("mess_module",),
            permissions=("mess_module.role.manage", "mess_module.menu.view"),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    # GET roles
    res = client.get("/api/v1/mms/roles/")
    assert res.status_code == 200

    # GET active roles
    res2 = client.get("/api/v1/mms/roles/active/")
    assert res2.status_code == 200
    assert "caretaker" in res2.json()


def test_registration_window_get_and_forbidden(stub_iam):
    # Student session without review permission
    stub_iam(
        make_session(
            user_id=2001,
            modules=("mess_module",),
            permissions=("mess_module.menu.view",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    # GET window
    res = client.get("/api/v1/mms/window/?mess_name=Central+Mess")
    # Might be 200 or 404 depending on whether window exists
    assert res.status_code in [200, 404]

    # Attempt POST without caretaker permission
    payload = {
        "name": "Unauthorized Window",
        "mess_name": "Central Mess",
        "start_date": datetime.date.today().isoformat(),
        "end_date": (datetime.date.today() + datetime.timedelta(days=10)).isoformat(),
    }
    res_post = client.post("/api/v1/mms/window/", payload, format="json")
    assert res_post.status_code == 403


def test_student_registration_lifecycle_api(stub_iam):
    # Caretaker opens window
    stub_iam(
        make_session(
            user_id=3001,
            modules=("mess_module",),
            permissions=("mess_module.registration.review", "mess_module.menu.view"),
        )
    )
    caretaker_client = APIClient()
    caretaker_client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    start = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    end = (datetime.date.today() + datetime.timedelta(days=15)).isoformat()
    w_res = caretaker_client.post(
        "/api/v1/mms/window/",
        {"name": "Semester 1", "mess_name": "Central Mess", "start_date": start, "end_date": end},
        format="json",
    )
    assert w_res.status_code == 201

    # Student submits registration
    stub_iam(
        make_session(
            user_id=2005,
            modules=("mess_module",),
            permissions=("mess_module.registration.submit", "mess_module.menu.view"),
        )
    )
    student_client = APIClient()
    student_client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    reg_res = student_client.post(
        "/api/v1/mms/registration/submit/",
        {"mess_name": "Central Mess", "start_date": start, "remarks": "Hostel student"},
        format="json",
    )
    assert reg_res.status_code == 201
    reg_id = reg_res.json()["id"]

    # Student views own registration
    mine_res = student_client.get("/api/v1/mms/registration/mine/")
    assert mine_res.status_code == 200
    assert mine_res.json()["id"] == reg_id

    # Caretaker lists registrations
    stub_iam(
        make_session(
            user_id=3001,
            modules=("mess_module",),
            permissions=("mess_module.registration.review", "mess_module.menu.view"),
        )
    )
    list_res = caretaker_client.get("/api/v1/mms/registrations/")
    assert list_res.status_code == 200

    # Caretaker reviews and approves registration
    review_res = caretaker_client.post(
        f"/api/v1/mms/registrations/{reg_id}/review/",
        {"approve": True, "remarks": "Eligible student"},
        format="json",
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "REGISTERED"


def test_student_deregistration_lifecycle_api(stub_iam):
    from modules.mms.models import MessRegistration, RegistrationStatus

    # Create registered student
    reg = MessRegistration.objects.create(
        student_id=2010,
        mess_name="Central Mess",
        start_date=datetime.date.today(),
        status=RegistrationStatus.REGISTERED.value,
    )

    # Student requests deregistration
    stub_iam(
        make_session(
            user_id=2010,
            modules=("mess_module",),
            permissions=("mess_module.registration.submit", "mess_module.menu.view"),
        )
    )
    student_client = APIClient()
    student_client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    dereg_res = student_client.post(
        f"/api/v1/mms/registration/{reg.id}/deregister/",
        {"reason": "Moving out of hostel"},
        format="json",
    )
    assert dereg_res.status_code == 200
    assert "deregistration_reason" in dereg_res.json()

    # Caretaker reviews deregistration
    stub_iam(
        make_session(
            user_id=3001,
            modules=("mess_module",),
            permissions=("mess_module.registration.review", "mess_module.menu.view"),
        )
    )
    caretaker_client = APIClient()
    caretaker_client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    review_res = caretaker_client.post(
        f"/api/v1/mms/registrations/{reg.id}/review-deregister/",
        {"approve": True, "remarks": "Approved clearance"},
        format="json",
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "DEREGISTERED"


def test_caretaker_menu_update_api(stub_iam):
    stub_iam(
        make_session(
            user_id=3001,
            modules=("mess_module",),
            permissions=("mess_module.menu.manage", "mess_module.menu.view"),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    payload = {
        "mess_name": "Central Mess",
        "day_of_week": DayOfWeek.WEDNESDAY.value,
        "meal_time": MealTime.DINNER.value,
        "items": "Paneer Butter Masala, Roti, Rice",
    }
    res = client.post("/api/v1/mms/menu/", payload, format="json")
    assert res.status_code == 200
    assert res.json()["meal_time"] == "DINNER"
    assert "Paneer" in res.json()["items"]


def test_rebate_review_and_list_api(stub_iam):
    from modules.mms.models import RebateRequest, RebateStatus

    rebate = RebateRequest.objects.create(
        student_id=2020,
        mess_name="Central Mess",
        start_date=datetime.date.today() + datetime.timedelta(days=2),
        end_date=datetime.date.today() + datetime.timedelta(days=6),
        duration_days=5,
        reason="Home visit",
        status=RebateStatus.PENDING.value,
    )

    stub_iam(
        make_session(
            user_id=3001,
            modules=("mess_module",),
            permissions=("mess_module.rebate.review", "mess_module.menu.view"),
        )
    )
    caretaker_client = APIClient()
    caretaker_client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    # Caretaker lists rebates
    list_res = caretaker_client.get("/api/v1/mms/rebates/")
    assert list_res.status_code == 200

    # Caretaker reviews rebate
    review_res = caretaker_client.post(
        f"/api/v1/mms/rebates/{rebate.id}/review/",
        {"approve": True, "remarks": "Approved by Caretaker"},
        format="json",
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "APPROVED"


def test_feedback_api_get_and_post(stub_iam):
    # Student submits feedback
    stub_iam(
        make_session(
            user_id=2030,
            modules=("mess_module",),
            permissions=("mess_module.feedback.submit", "mess_module.menu.view"),
        )
    )
    student_client = APIClient()
    student_client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    payload = {
        "mess_name": "Central Mess",
        "rating": 5,
        "category": "FOOD_QUALITY",
        "comments": "Great dinner menu today!",
    }
    res = student_client.post("/api/v1/mms/feedback/", payload, format="json")
    assert res.status_code == 201
    assert res.json()["rating"] == 5

    # Caretaker / Warden views feedback
    stub_iam(
        make_session(
            user_id=3001,
            modules=("mess_module",),
            permissions=("mess_module.feedback.view", "mess_module.menu.view"),
        )
    )
    caretaker_client = APIClient()
    caretaker_client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    get_res = caretaker_client.get("/api/v1/mms/feedback/")
    assert get_res.status_code == 200
    assert len(get_res.json()) >= 1
