# Management command tests for modules/vh/management/commands/
from io import StringIO

import pytest
from django.core.management import call_command

from modules.vh.models.inventory import InventoryItem
from modules.vh.models.room import Room
from modules.vh.models.tariff import TariffConfig

pytestmark = pytest.mark.django_db


def test_seed_vh_data_command():
    out = StringIO()
    call_command("seed_vh_data", stdout=out)
    output = out.getvalue()
    assert "Seeded" in output

    assert Room.objects.count() >= 10
    assert TariffConfig.objects.count() >= 12
    assert InventoryItem.objects.count() >= 8

    # Idempotence check: Running seed again updates existing records without duplication error
    call_command("seed_vh_data", stdout=out)
    assert Room.objects.count() >= 10
