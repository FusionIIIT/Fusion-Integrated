"""Weekly menu (BR-MMS-014/015/038/039; UC-008/009)."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class MenuItem(TimeStampedModel):
    MEAL_CHOICES = [("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner")]

    day = models.DateField(db_index=True)
    meal = models.CharField(max_length=16, choices=MEAL_CHOICES)
    item = models.TextField()
    published_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_menu_item"
        indexes = [
            models.Index(fields=["day", "meal"], name="menu_item_day_meal_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(meal__in=("breakfast", "lunch", "dinner")),
                name="menu_item_valid_meal",
            ),
            models.UniqueConstraint(
                fields=["day", "meal", "item"],
                name="menu_item_unique_day_meal_item",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.day} {self.meal}: {self.item}"
