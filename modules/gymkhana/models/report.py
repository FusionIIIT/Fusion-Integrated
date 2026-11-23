"""Club event report documentation model for Gymkhana."""

from __future__ import annotations

from django.db import models

from modules.gymkhana.models.club import Club


class ClubEventReport(models.Model):
    """Event report submitted by Club Head and reviewed by Club Faculty Councillor."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="event_reports")
    submitted_by_id = models.IntegerField()
    student_incharge_id = models.IntegerField()
    event_name = models.CharField(max_length=150)
    event_date = models.DateTimeField()
    description = models.TextField(blank=True)
    report_file = models.FileField(upload_to="gymkhana/reports/")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_event_report"
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"EventReport(club={self.club.name}, event={self.event_name})"
