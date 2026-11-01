from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class MenuItem(TimeStampedModel, UserScopedModel):
    DAY_OF_WEEK = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    MEAL = [
        ("BREAKFAST", "Breakfast"),
        ("LUNCH", "Lunch"),
        ("DINNER", "Dinner"),
    ]

    day_of_week = models.PositiveSmallIntegerField(choices=DAY_OF_WEEK)
    meal = models.CharField(max_length=10, choices=MEAL)
    item_name = models.CharField(max_length=120)
    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "mess_menu_item"
        unique_together = [["day_of_week", "meal", "item_name"]]
        indexes = [["day_of_week", "meal"], ["day_of_week", "meal", "item_name"]]

    def __str__(self):
        return f"{self.item_name} on {self.get_day_of_week_display()} at {self.meal}"
