from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.visitor_hostel.models import BookingRequest, Room, VisitorCategoryTariff
from modules.visitor_hostel.registry import ROLE_GRANTS


@pytest.fixture
def actor(stub_iam):
    def login(role="student", user_id=1001, *, modules=("visitor_hostel",), kind="student"):
        if role in {"vh_caretaker", "vh_in_charge"}:
            from django.utils import timezone

            from modules.visitor_hostel.models import RoleAssignment

            RoleAssignment.objects.update_or_create(
                role=role,
                defaults={
                    "user_id": user_id,
                    "starts_at": timezone.now() - timedelta(days=1),
                    "ends_at": timezone.now() + timedelta(days=30),
                    "email": "operator@example.test",
                },
            )
        stub_iam(
            make_session(
                user_id=user_id,
                permissions=ROLE_GRANTS.get(role, ()),
                modules=modules,
                roles=(role,),
                active_role=role,
                kind=kind,
            )
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token test")
        return client

    return login


@pytest.fixture
def payload():
    return {
        "visitor_name": "Guest",
        "visitor_category": "A",
        "purpose": "Research visit",
        "check_in_date": str(date.today() + timedelta(days=10)),
        "check_out_date": str(date.today() + timedelta(days=12)),
        "room_type": "suite",
        "occupancy": "single",
        "number_of_rooms": 1,
    }


@pytest.fixture
def booking(db, payload):
    obj = BookingRequest.objects.create(indenter_id=1001, **payload)
    obj.refresh_from_db()
    return obj


@pytest.fixture
def room(db):
    return Room.objects.create(room_number="VH-101", room_type="suite")


@pytest.fixture
def tariff(db):
    return VisitorCategoryTariff.objects.create(
        category="A",
        room_type="suite",
        occupancy="single",
        daily_rate=Decimal("400.00"),
        effective_from=date(2020, 1, 1),
    )


def endpoint(booking, action=""):
    return f"/api/v1/visitor-hostel/bookings/{booking.pk}/" + (f"{action}/" if action else "")

