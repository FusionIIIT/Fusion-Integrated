"""Institution-defined special food policy (BR-MMS-029; ISS-MMS-013).

The decision period is not frozen by the spec, so it is an effective-dated
policy row, never edited in place. `readiness()` reports a missing row as an
unmet prerequisite rather than 500ing on first use.
"""

from django.db import models

from core.db.mixins import TimeStampedModel


class SpecialFoodPolicy(TimeStampedModel):
    decision_period_hours = models.PositiveIntegerField(
        help_text="Institution-defined decision period in hours."
    )
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "mms_special_food_policy"

    def __str__(self) -> str:
        return f"special_food_policy:{self.decision_period_hours}h"
