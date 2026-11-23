from django.db import models
from django.db.models import Index

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.club import Club
from modules.gymkhana.storage import gymkhana_upload_storage


class ClubEventReport(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="event_reports")
    title = models.CharField(max_length=200)
    description = models.TextField()
    student_incharge_id = models.IntegerField(db_index=True)
    event_name = models.CharField(max_length=200)
    event_datetime = models.DateTimeField()
    report_file = models.FileField(
        upload_to="reports/",
        storage=gymkhana_upload_storage,
    )
    submitted_by_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "gymkhana_event_report"
        indexes = [
            Index(fields=["club", "created_at"], name="gym_report_club_created_idx"),
        ]
