from django.db import models

from modules.gymkhana.models.club import Club


class ClubEventReport(models.Model):
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="event_reports",
    )
    student_incharge_id = models.BigIntegerField()
    event_name = models.CharField(max_length=150)
    event_date = models.DateField()
    event_time = models.TimeField()
    description = models.TextField()
    report_file_url = models.CharField(max_length=500)
    report_file_id = models.CharField(max_length=200)
    submitted_by_user_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_event_report"
        indexes = [
            models.Index(fields=["club", "event_date"], name="gymkhana_report_club_date_idx"),
        ]

    def __str__(self) -> str:
        return f"Report: {self.event_name} ({self.club.name}) on {self.event_date}"
