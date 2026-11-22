from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.iaa.domain import state_machine as sm


class AuditObservation(TimeStampedModel):
    record = models.ForeignKey("iaa.FinancialRecord", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="observations")
    respondent_user_id = models.IntegerField()
    title = models.CharField(max_length=200)
    detail = models.TextField()
    status = models.CharField(max_length=10,
                              choices=[(s, s.title()) for s in sm.OBSERVATION_STATES],
                              default=sm.OBS_OPEN)
    cycle = models.PositiveSmallIntegerField(default=1)
    raised_by = models.IntegerField()
    raised_role = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(status__in=sm.OBSERVATION_STATES),
                                   name="iaa_observation_status_known"),
        ]
        indexes = [
            models.Index(fields=["respondent_user_id", "status"], name="iaa_obs_respondent_idx"),
            models.Index(fields=["status", "-created_at"], name="iaa_obs_status_idx"),
        ]

    def delete(self, *args, **kwargs):
        raise ValueError("Audit observations are never deleted (IAA-BR-301).")


class ObservationResponse(TimeStampedModel):
    PENDING = "pending"
    SATISFACTORY = "satisfactory"
    UNSATISFACTORY = "unsatisfactory"

    observation = models.ForeignKey(AuditObservation, on_delete=models.PROTECT,
                                    related_name="responses")
    cycle = models.PositiveSmallIntegerField()
    corrective_action = models.TextField()
    evidence_link = models.URLField(max_length=500, blank=True)
    responded_by = models.IntegerField()
    verdict = models.CharField(max_length=16, default=PENDING,
                               choices=[(PENDING, "Pending"), (SATISFACTORY, "Satisfactory"),
                                        (UNSATISFACTORY, "Unsatisfactory")])
    reviewed_by = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["cycle"]
        constraints = [
            models.UniqueConstraint(fields=["observation", "cycle"],
                                    name="iaa_obs_response_one_per_cycle"),
        ]

    def delete(self, *args, **kwargs):
        raise ValueError("Audit history is never deleted (IAA-BR-301).")
