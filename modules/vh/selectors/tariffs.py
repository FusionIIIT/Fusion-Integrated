# Tariff queries for VHMS.
from datetime import date
from decimal import Decimal

from django.db.models import QuerySet

from modules.vh.domain.tariffs import lookup_default_tariff
from modules.vh.models.tariff import TariffConfig


def list_tariffs(active_only: bool = True) -> QuerySet[TariffConfig]:
    # Returns tariff configuration records.
    qs = TariffConfig.objects.all().order_by("category", "room_type", "-effective_from")
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def get_applicable_tariff(
    category: str,
    room_type: str,
    occupancy: str,
    as_of_date: date | None = None,
) -> Decimal:
    # BR-VH-023: Automatically selects effective tariff for category and occupancy.
    query_date = as_of_date or date.today()
    tariffs = (
        TariffConfig.objects.filter(
            category=category.upper(),
            room_type=room_type.lower(),
            occupancy=occupancy.lower(),
            effective_from__lte=query_date,
            is_active=True,
        )
        .order_by("-effective_from")
        .first()
    )
    if tariffs:
        return tariffs.daily_rate
    return lookup_default_tariff(category, room_type, occupancy)
