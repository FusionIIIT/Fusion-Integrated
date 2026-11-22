# Test fixtures and authentication helpers for vh module tests.
from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.vh.models.inventory import InventoryItem
from modules.vh.models.room import Room
from modules.vh.models.tariff import TariffConfig
from modules.vh.registry import _CARETAKER_PERMS, _INCHARGE_PERMS, _INDENTER_PERMS


class SessionSwitchingClient(APIClient):
    # APIClient that ensures FakeIam switches to this client's session on every request
    def __init__(self, stub_iam_setter, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setter = stub_iam_setter
        self._session = session
        self.credentials(HTTP_AUTHORIZATION="Token dev-test-token")

    def generic(self, *args, **kwargs):
        self._setter(self._session)
        return super().generic(*args, **kwargs)


@pytest.fixture
def vh_client(stub_iam):
    # Returns helper to mint APIClient with specific user, module grant, and permissions.
    def _make(user_id=101, perms=_INDENTER_PERMS, modules=("vh",), kind="student"):
        sess = make_session(user_id=user_id, permissions=perms, modules=modules, kind=kind)
        return SessionSwitchingClient(stub_iam, sess)

    return _make


@pytest.fixture
def indenter_client(vh_client):
    return vh_client(user_id=101, perms=_INDENTER_PERMS, kind="student")


@pytest.fixture
def caretaker_client(vh_client):
    return vh_client(user_id=201, perms=_CARETAKER_PERMS, kind="staff")


@pytest.fixture
def incharge_client(vh_client):
    return vh_client(user_id=301, perms=_INCHARGE_PERMS, kind="faculty")


@pytest.fixture
def sample_rooms(db):
    r1 = Room.objects.create(room_number="101", room_type="suite", capacity=2, is_active=True)
    r2 = Room.objects.create(room_number="102", room_type="non_suite", capacity=2, is_active=True)
    r3 = Room.objects.create(room_number="103", room_type="non_suite", capacity=2, is_active=True)
    return r1, r2, r3


@pytest.fixture
def sample_tariffs(db):
    eff = date.today() - timedelta(days=30)
    t1 = TariffConfig.objects.create(
        category="A",
        room_type="suite",
        occupancy="single",
        daily_rate=Decimal("800.00"),
        effective_from=eff,
    )
    t2 = TariffConfig.objects.create(
        category="A",
        room_type="non_suite",
        occupancy="single",
        daily_rate=Decimal("500.00"),
        effective_from=eff,
    )
    t3 = TariffConfig.objects.create(
        category="B",
        room_type="non_suite",
        occupancy="single",
        daily_rate=Decimal("800.00"),
        effective_from=eff,
    )
    return t1, t2, t3


@pytest.fixture
def sample_inventory(db):
    item1 = InventoryItem.objects.create(
        item_name="Bedsheet Deluxe",
        category="linen",
        current_quantity=20,
        minimum_threshold=10,
        unit="pieces",
    )
    item2 = InventoryItem.objects.create(
        item_name="Bath Towel",
        category="linen",
        current_quantity=5,
        minimum_threshold=10,
        unit="pieces",
        is_threshold_alert=True,
    )
    return item1, item2
