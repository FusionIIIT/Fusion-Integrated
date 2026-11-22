"""Vacation food continuity survey (BR-MMS-026/027; UC-016/028;
BW-MMS-08/09/10, CW-MMS-04)."""

from django.db import models

from core.db.mixins import TimeStampedModel


class VacationSurvey(TimeStampedModel):
    vacation = models.CharField(max_length=120)
    response_deadline = models.DateTimeField(db_index=True)
    is_open = models.BooleanField(default=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_vacation_survey"
        indexes = [
            models.Index(fields=["is_open", "response_deadline"], name="survey_open_deadline_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.vacation} survey"
