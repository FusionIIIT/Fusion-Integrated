"""Announcements (BR-MMS-032/033; UC-022/023)."""

from django.db import models

from core.db.mixins import TimeStampedModel


class Announcement(TimeStampedModel):
    title = models.CharField(max_length=200)
    body = models.TextField()
    publisher_user_id = models.IntegerField()
    published_at = models.DateTimeField()

    class Meta:
        db_table = "mms_announcement"
        indexes = [
            models.Index(fields=["-published_at"], name="announcement_published_idx"),
        ]

    def __str__(self) -> str:
        return self.title
