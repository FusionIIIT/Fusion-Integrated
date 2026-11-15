"""Shared pytest fixtures for Visitors Hostel (VH) test suite."""
from decimal import Decimal
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from modules.vh.models import (
    OccupancyType,
    Room,
    RoomStatus,
    RoomType,
    Tariff,
    VisitorCategory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def category_a(db):
    return VisitorCategory.objects.create(
        code=VisitorCategory.CATEGORY_A,
        name="Category A - Institute Guests / Official",
        description="Official institute invited visitors",
    )


@pytest.fixture
def category_b(db):
    return VisitorCategory.objects.create(
        code=VisitorCategory.CATEGORY_B,
        name="Category B - Invited Academic / Research Visitors",
        description="Invited research and faculty visitors",
    )


@pytest.fixture
def category_c(db):
    return VisitorCategory.objects.create(
        code=VisitorCategory.CATEGORY_C,
        name="Category C - Students / Alumni Guests",
        description="Students and alumni guests",
    )


@pytest.fixture
def category_d(db):
    return VisitorCategory.objects.create(
        code=VisitorCategory.CATEGORY_D,
        name="Category D - Others / Personal",
        description="Personal visitors and others",
    )


@pytest.fixture
def all_categories(category_a, category_b, category_c, category_d):
    return [category_a, category_b, category_c, category_d]


@pytest.fixture
def sample_room(db):
    return Room.objects.create(
        room_number="101",
        room_type=RoomType.NON_SUITE,
        occupancy_type=OccupancyType.DOUBLE,
        floor=1,
        status=RoomStatus.AVAILABLE,
    )


@pytest.fixture
def all_room_combinations(db):
    rooms = []
    combos = [
        ("S1", RoomType.SUITE, OccupancyType.SINGLE, 1),
        ("S2", RoomType.SUITE, OccupancyType.DOUBLE, 1),
        ("NS1", RoomType.NON_SUITE, OccupancyType.SINGLE, 2),
        ("NS2", RoomType.NON_SUITE, OccupancyType.DOUBLE, 2),
    ]
    for num, r_type, occ, fl in combos:
        r, _ = Room.objects.get_or_create(
            room_number=num,
            defaults={
                "room_type": r_type,
                "occupancy_type": occ,
                "floor": fl,
                "status": RoomStatus.AVAILABLE,
            },
        )
        rooms.append(r)
    return rooms


@pytest.fixture
def sample_tariff(db, category_a):
    return Tariff.objects.create(
        category=category_a,
        room_type=RoomType.NON_SUITE,
        occupancy_type=OccupancyType.DOUBLE,
        rate_per_day=Decimal("1000.00"),
        effective_from=timezone.localdate(),
    )


@pytest.fixture
def all_tariffs(db, all_categories):
    tariffs = []
    today = timezone.localdate()
    rates = {
        VisitorCategory.CATEGORY_A: Decimal("500.00"),
        VisitorCategory.CATEGORY_B: Decimal("800.00"),
        VisitorCategory.CATEGORY_C: Decimal("1200.00"),
        VisitorCategory.CATEGORY_D: Decimal("1500.00"),
    }
    for cat in all_categories:
        base_rate = rates[cat.code]
        for r_type in [RoomType.SUITE, RoomType.NON_SUITE]:
            r_mult = Decimal("1.5") if r_type == RoomType.SUITE else Decimal("1.0")
            for occ in [OccupancyType.SINGLE, OccupancyType.DOUBLE]:
                occ_mult = Decimal("1.2") if occ == OccupancyType.DOUBLE else Decimal("1.0")
                final_rate = (base_rate * r_mult * occ_mult).quantize(Decimal("0.01"))
                t, _ = Tariff.objects.get_or_create(
                    category=cat,
                    room_type=r_type,
                    occupancy_type=occ,
                    effective_from=today,
                    defaults={"rate_per_day": final_rate},
                )
                tariffs.append(t)
    return tariffs

