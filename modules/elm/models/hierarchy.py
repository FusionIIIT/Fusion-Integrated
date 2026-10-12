"""Employee Leave Management policy and routing hierarchy."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class ELMPolicy(TimeStampedModel):
    """Current, unversioned leave-policy parameters used for validation and routing.

    The baseline has no draft/publish/effective-version lifecycle: this row is
    the current configured value, and every validator reads it directly.
    """

    class Category(models.TextChoices):
        CASUAL = "CL", "Casual Leave"
        RESTRICTED_HOLIDAY = "RH", "Restricted Holiday"
        SPECIAL_CASUAL = "SCL", "Special Casual Leave"
        EARNED = "EL", "Earned Leave"
        COMPLEMENTARY = "COL", "Complementary Leave"
        VACATION = "VL", "Vacation Leave"

    class Counting(models.TextChoices):
        CONSECUTIVE = "consecutive", "Count every day including weekends and closed holidays"
        EXCLUDE_WEEKEND = "exclude_weekend", "Weekends count; closed holidays excluded"
        CLOSED_HOLIDAY = "closed_holiday", "Only closed holidays count (weekend excluded)"
        HALF_DAY = "half_day", "Half-day availability"

    entity_type = models.CharField(
        max_length=32,
        choices=Category.choices,
        db_index=True,
    )
    allotment_days = models.PositiveSmallIntegerField(
        default=0,
        help_text="Annual entitlement in whole days; fractional splits are stored separately.",
    )
    first_half = models.BooleanField(default=False, help_text="CL: first-half availability")
    second_half = models.BooleanField(default=False, help_text="CL: second-half availability")
    carry_forward = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether unused entitlement carries forward; null = not applicable.",
    )
    convert_ratio = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="VL-to-EL conversion ratio; null = no conversion.",
    )
    counting_policy = models.CharField(
        max_length=32,
        choices=Counting.choices,
        default=Counting.CONSECUTIVE,
        help_text="How an approved interval is counted for this category.",
    )
    requires_substitute = models.BooleanField(
        default=False,
        help_text="Whether responsibility coverage is required before approval.",
    )
    station_leave_supported = models.BooleanField(
        default=False,
        help_text="Whether this category accepts Station Leave details.",
    )
    medical_evidence_required = models.BooleanField(
        default=False,
        help_text="COL: supporting medical evidence may be required.",
    )

    class Meta:
        db_table = "elm_policy"
        constraints = [
            models.CheckConstraint(
                condition=~Q(entity_type="CL") | (Q(first_half=True) | Q(second_half=True)),
                name="cl_half_supported",
            ),
            models.CheckConstraint(
                condition=Q(convert_ratio__isnull=True)
                | Q(convert_ratio__gt=0),
                name="vl_conversion_positive",
            ),
            models.CheckConstraint(
                condition=Q(carry_forward__isnull=True)
                | Q(carry_forward=True)
                | Q(carry_forward=False),
                name="carry_forward_boolean",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_entity_type_display()} policy"


class HierarchyLevel(TimeStampedModel):
    """One rung of the sanctioning hierarchy for a leave category and unit."""

    category = models.ForeignKey(
        ELMPolicy,
        on_delete=models.CASCADE,
        related_name="hierarchy_levels",
    )
    rank = models.PositiveSmallIntegerField(
        default=0,
        help_text="Lower rank is looked up first in the chain.",
    )
    role = models.CharField(
        max_length=80,
        help_text="Named role, e.g. Deputy Registrar (Estt.), Dean, Registrar, Director.",
    )
    decision = models.CharField(
        max_length=32,
        choices=[
            ("final", "Final — controls the outcome"),
            ("recommend", "Recommend — request continues"),
        ],
        default="final",
        help_text="Final closes the path; recommend routes onward.",
    )
    requires_establishment = models.BooleanField(
        default=False,
        help_text="Step applies an Establishment verification/routing pass.",
    )
    applies_to_unit = models.CharField(
        max_length=80,
        blank=True,
        help_text="Unit Head's own unit; leave this blank for a role owned at institute level.",
    )

    class Meta:
        db_table = "elm_hierarchy_level"
        ordering = ["category", "rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "rank"],
                name="hierarchy_rank_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.category} -> {self.role}"
