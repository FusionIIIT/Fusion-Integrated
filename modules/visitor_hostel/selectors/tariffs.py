"""Tariff rows in the domain's shape."""
from __future__ import annotations

from modules.visitor_hostel.domain import tariffs
from modules.visitor_hostel.models import MealTariff, RoomTariff


def room_rates(category: str | None = None) -> list[tariffs.TariffRow]:
    qs = RoomTariff.objects.all()
    if category:
        qs = qs.filter(category=category)
    return [tariffs.TariffRow(t.pk, tariffs.room_key(t.category, t.occupancy),
                              t.rate_per_day, t.effective_from) for t in qs]


def meal_rates() -> list[tariffs.TariffRow]:
    return [tariffs.TariffRow(t.pk, tariffs.meal_key(t.item), t.rate, t.effective_from)
            for t in MealTariff.objects.all()]
