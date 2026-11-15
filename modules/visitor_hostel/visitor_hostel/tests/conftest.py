"""Fixtures for the Visitors Hostel suite. Permission sets come from
registry.ROLE_GRANTS, so a test cannot grant a code production never would."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from fusion_auth.client import UserRef
from modules.visitor_hostel import registry
from modules.visitor_hostel.domain import meals, tariffs
from modules.visitor_hostel.models import Booking, MealTariff, Room, RoomTariff
from modules.visitor_hostel.services import duty as duty_service

BASE = "/api/v1/visitorhostel"
MODULE = registry.MODULE["code"]

INDENTER = tuple(registry.ROLE_GRANTS["faculty"])
CARETAKER = tuple(registry.ROLE_GRANTS["VhCaretaker"])
INCHARGE = tuple(registry.ROLE_GRANTS["VhIncharge"])

INDENTER_ID, OTHER_INDENTER_ID = 1001, 1002
CARETAKER_ID, INCHARGE_ID = 500, 600

#: Per day, by (category, occupancy). Only A/single and A/double are used in amounts.
ROOM_RATES = {(c, o): Decimal(1000 + 100 * i + (200 if o == "double" else 0))
              for i, c in enumerate(tariffs.CATEGORIES) for o in tariffs.OCCUPANCIES}
MEAL_RATES = {"full_day": Decimal("300"), "breakfast": Decimal("60"),
              "lunch": Decimal("120"), "dinner": Decimal("120"),
              "tea": Decimal("15"), "milk": Decimal("20")}


def principal(user_id, perms, *, kind="faculty", roles=None, active_role=None,
              modules=(MODULE,)):
    return make_principal(user_id=user_id, permissions=perms, kind=kind,
                          roles=roles or (kind,), active_role=active_role or kind,
                          modules=modules)


@pytest.fixture
def act(stub_iam):
    """`act(user_id, perms)` returns an API client signed in as that person."""
    people = {uid: UserRef(user_id=uid, username=f"u{uid}", display_name=f"User {uid}",
                           kind="faculty", email=f"u{uid}@iiitdmj.test")
              for uid in (INDENTER_ID, OTHER_INDENTER_ID, CARETAKER_ID, INCHARGE_ID, 501)}

    def _as(user_id, perms, *, modules=(MODULE,), kind="faculty", roles=None,
            active_role=None):
        stub_iam(make_session(user_id=user_id, permissions=perms, modules=modules,
                              kind=kind, roles=roles or (kind,),
                              active_role=active_role or kind),
                 users=people)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token test")
        return client

    return _as


@pytest.fixture
def world(db):
    """Rooms, every tariff and both officers on duty — what readiness() asks for."""
    start = timezone.localdate() - timedelta(days=365)
    for (category, occupancy), rate in ROOM_RATES.items():
        RoomTariff.objects.create(category=category, occupancy=occupancy,
                                  rate_per_day=rate, effective_from=start)
    for item in meals.PRICED_ITEMS:
        MealTariff.objects.create(item=item, rate=MEAL_RATES[item], effective_from=start)
    rooms = [Room.objects.create(number=n, room_type=t)
             for n, t in (("101", "non_suite"), ("102", "non_suite"), ("201", "suite"))]
    until = timezone.now() + timedelta(days=60)
    duty_service.assign(role="caretaker", user_id=CARETAKER_ID, valid_until=until)
    duty_service.assign(role="incharge", user_id=INCHARGE_ID, valid_until=until)
    return rooms


def requisition(**over):
    today = timezone.localdate()
    data = {
        "visitor_name": "Dr. Visiting Scholar", "visitor_phone": "9000000000",
        "purpose": "Guest lecture", "category": "A", "occupancy": "single",
        "arrival_date": (today + timedelta(days=10)).isoformat(),
        "departure_date": (today + timedelta(days=12)).isoformat(),
        "rooms_required": 1, "occupants": 1, "billing_responsibility": "institute",
    }
    data.update(over)
    return data


def make_booking(status="pending", indenter=INDENTER_ID, arrival_in=10, nights=2, **over):
    """A row in any state, written directly — for tests about what happens next."""
    today = timezone.localdate()
    fields = {
        "indenter_user_id": indenter, "recorded_by_user_id": indenter or CARETAKER_ID,
        "visitor_name": "Guest", "purpose": "Visit", "category": "A",
        "occupancy": "single", "arrival_date": today + timedelta(days=arrival_in),
        "departure_date": today + timedelta(days=arrival_in + nights),
        "rooms_required": 1, "occupants": 1, "billing_responsibility": "institute",
        "status": status, "caretaker_user_id": CARETAKER_ID,
    }
    fields.update(over)
    return Booking.objects.create(**fields)
