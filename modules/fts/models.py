from django.db import models

from core.db.mixins import TimeStampedModel


class File(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"
        CLOSED = "CLOSED", "Closed"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    creator_id = models.IntegerField(db_index=True)
    current_holder_id = models.IntegerField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    def __str__(self) -> str:
        return f"[{self.id}] {self.title} ({self.status})"


class FileMovement(models.Model):
    file = models.ForeignKey(
        File,
        on_delete=models.CASCADE,
        related_name="movements",
    )
    sender_id = models.IntegerField(db_index=True)
    recipient_id = models.IntegerField(db_index=True)
    comment = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"File {self.file_id}: {self.sender_id} -> {self.recipient_id} at {self.timestamp}"