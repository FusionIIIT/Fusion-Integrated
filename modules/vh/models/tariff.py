# Tariff configuration model for VHMS.
from django.db import models
from django.db.models import CheckConstraint, Index, Q, UniqueConstraint

from core.db.mixins import TimeStampedModel
from modules.vh.domain.rules import OCCUPANCY_CHOICES, ROOM_TYPE_CHOICES, VISITOR_CATEGORY_CHOICES


class TariffConfig(TimeStampedModel):
    # Effective-dated institutional tariffs by category, room type, and occupancy.
    category = models.CharField(
        max_length=1,
        choices=VISITOR_CATEGORY_CHOICES,
        db_index=True,
    )
    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPE_CHOICES,
    )
    occupancy = models.CharField(
        max_length=10,
        choices=OCCUPANCY_CHOICES,
    )
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField(db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_tariff_config"
        indexes = [
            Index(
                fields=["category", "room_type", "occupancy", "effective_from"],
                name="vh_tariff_lookup_idx",
            ),
        ]
        constraints = [
            UniqueConstraint(
                fields=["category", "room_type", "occupancy", "effective_from"],
                name="vh_tariff_unique_effective",
            ),
            CheckConstraint(
                condition=Q(daily_rate__gte=0),
                name="vh_tariff_rate_non_neg",
            ),
        ]

    def __str__(self) -> str:
        return f"Cat {self.category} {self.room_type} {self.occupancy}: Rs.{self.daily_rate}"
