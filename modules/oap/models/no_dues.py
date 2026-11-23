from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.oap.domain import no_dues as nd


class NoDuesCase(TimeStampedModel, UserScopedModel):
    finalized = models.BooleanField(default=False)
    finalized_by_user_id = models.IntegerField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "oap_no_dues_case"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id"],
                condition=Q(finalized=False),
                name="oap_one_open_no_dues_per_student",
            ),
        ]


class NoDuesResult(TimeStampedModel):
    DOMAIN_CHOICES = [(d, d) for d in nd.DOMAINS]
    RESULT_CHOICES = [
        (nd.PENDING, "Pending"),
        (nd.CLEAR, "Clear"),
        (nd.OUTSTANDING, "Outstanding"),
    ]

    case = models.ForeignKey(NoDuesCase, on_delete=models.CASCADE, related_name="results")
    domain = models.CharField(max_length=32, choices=DOMAIN_CHOICES)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default=nd.PENDING)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "oap_no_dues_result"
        constraints = [
            models.UniqueConstraint(fields=["case", "domain"], name="oap_one_result_per_domain"),
        ]
