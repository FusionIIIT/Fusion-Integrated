from django.db import models

from core.db.mixins import TimeStampedModel


class ItemCategory(models.TextChoices):
    CONSUMABLE = "CONSUMABLE", "Consumable"
    EQUIPMENT = "EQUIPMENT", "Equipment"
    SERVICE = "SERVICE", "Service"
    FURNITURE = "FURNITURE", "Furniture"


class UnitOfMeasure(models.TextChoices):
    PIECE = "PIECE", "Piece"
    BOX = "BOX", "Box"
    KG = "KG", "Kilogram"
    METER = "METER", "Meter"
    PACKET = "PACKET", "Packet"
    SET = "SET", "Set"


class ItemMaster(TimeStampedModel):
    item_code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=32,
        choices=ItemCategory.choices,
        default=ItemCategory.CONSUMABLE,
    )
    unit_of_measure = models.CharField(
        max_length=32,
        choices=UnitOfMeasure.choices,
        default=UnitOfMeasure.PIECE,
    )
    minimum_stock_level = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "psm_item_master"
        ordering = ["item_code"]

    def __str__(self) -> str:
        return f"{self.item_code} - {self.name}"
