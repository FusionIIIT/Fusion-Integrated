"""Club event reports (UC-GYM-010, UC-GYM-012)."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.clubs import Club


class EventReport(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="reports")
    student_incharge_user_id = models.IntegerField()
    event_name = models.CharField(max_length=200)
    event_at = models.DateTimeField()
    description = models.TextField(max_length=4000)
    report_link = models.CharField(max_length=300)
    report_file_id = models.CharField(max_length=200)
    submitted_by_user_id = models.IntegerField()

    class Meta:
        db_table = "gymkhana_event_report"
        constraints = [
            models.CheckConstraint(condition=~Q(report_file_id=""),
                                   name="gym_report_file_present"),
        ]
        indexes = [
            models.Index(fields=["club", "created_at"],
                         name="gym_report_club_created_idx"),
        ]
