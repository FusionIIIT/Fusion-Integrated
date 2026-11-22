"""Vacation survey response (BR-MMS-027/041; UC-017/028; BW-MMS-08/09/10)."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class VacationResponse(TimeStampedModel):
    RESPONSE_CHOICES = [("yes", "Yes"), ("no", "No"), ("default_no", "Default No")]

    survey = models.IntegerField(db_index=True)
    student_user_id = models.IntegerField(db_index=True)
    response = models.CharField(max_length=16, choices=RESPONSE_CHOICES)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_vacation_response"
        indexes = [
            models.Index(
                fields=["student_user_id", "response"], name="vacation_response_student_idx"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "student_user_id"],
                name="one_vacation_response_per_student_per_survey",
            ),
            models.CheckConstraint(
                condition=Q(response__in=("yes", "no", "default_no")),
                name="vacation_response_valid_option",
            ),
        ]

    def __str__(self) -> str:
        return f"survey:{self.survey} student:{self.student_user_id} {self.response}"
