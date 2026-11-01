"""Placement domain tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database. Recruiters are the exception:
they are local rows, scoped to one company.
"""
from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


# -- Season and policy ---------------------------------------------------------
class PlacementPolicy(TimeStampedModel):
    """One season of the signed Placement Policy. Switching rules live in
    PolicyCategory, which is per discipline group."""

    season = models.CharField(max_length=12, unique=True)     # "2026-27"
    label = models.CharField(max_length=60, blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Rule 6: from this date, appearing is mandatory for unplaced students.
    mandatory_from = models.DateField(null=True, blank=True)

    # discipline code -> policy group (cse_ece | core | design)
    discipline_groups = models.JSONField(default=dict, blank=True)

    min_cpi_to_register = models.DecimalField(max_digits=4, decimal_places=2,
                                              null=True, blank=True)
    allow_backlog_registration = models.BooleanField(default=True)

    # Rule 20's deadline; after it, registering needs the fee and approval.
    registration_closes_on = models.DateField(null=True, blank=True)

    # Rule 22's April 15: a date, because "2026-27" does not name the year.
    notify_non_joining_by = models.DateField(null=True, blank=True)

    # Rules 20 and 21. Recorded only; PCMS does not take payment.
    late_registration_fee = models.PositiveIntegerField(default=1000)
    reregistration_fee = models.PositiveIntegerField(default=2000)

    # Fallback when the recruiter sets no deadline (PC-BR-013).
    default_offer_response_hours = models.PositiveIntegerField(default=72)

    class Meta:
        db_table = "placement_policy"
        verbose_name_plural = "placement policies"

    def __str__(self) -> str:
        return self.season


class PolicyCategory(TimeStampedModel):
    """One category within a discipline group (policy rule 2).

        CSE/ECE  Cat 1  <=10 LPA      1.5x, one switch then out
                 Cat 2  10-16.5 LPA   2x,   one switch then out
        Core     Cat 1  6.5-11.5 LPA  1.5x and must exceed 11.5
        Design   Cat 1  <=7.5 LPA     1.5x, out once above 12
                 Cat 2  7.5-12 LPA    1.5x, out once above 12
    """

    GROUPS = [("cse_ece", "CSE & ECE"), ("core", "ME, SM and Core"),
              ("design", "Design")]

    policy = models.ForeignKey(PlacementPolicy, on_delete=models.CASCADE,
                               related_name="categories")
    group = models.CharField(max_length=12, choices=GROUPS)
    number = models.PositiveSmallIntegerField()               # Cat 1 / Cat 2

    ctc_min = models.DecimalField(max_digits=8, decimal_places=2,
                                  null=True, blank=True)
    ctc_max = models.DecimalField(max_digits=8, decimal_places=2,
                                  null=True, blank=True)

    switch_multiplier = models.DecimalField(max_digits=4, decimal_places=2,
                                            default=Decimal("1.5"))
    # An absolute floor a switch must exceed, on top of the multiple.
    switch_floor = models.DecimalField(max_digits=8, decimal_places=2,
                                       null=True, blank=True)
    # Holding above this ends the student's season.
    exit_above = models.DecimalField(max_digits=8, decimal_places=2,
                                     null=True, blank=True)
    # Null means unlimited, bounded instead by exit_above.
    max_switches = models.PositiveSmallIntegerField(null=True, blank=True,
                                                    default=1)

    class Meta:
        db_table = "placement_policy_category"
        ordering = ["group", "number"]
        constraints = [
            models.UniqueConstraint(fields=["policy", "group", "number"],
                                    name="policy_category_unique"),
            models.CheckConstraint(
                condition=Q(ctc_min__isnull=True) | Q(ctc_max__isnull=True)
                | Q(ctc_max__gte=models.F("ctc_min")),
                name="policy_category_band_valid"),
        ]
        verbose_name_plural = "policy categories"

    def __str__(self) -> str:
        return f"{self.get_group_display()} Cat {self.number}"
