import uuid

from django.db import models

from core.db.mixins import TimeStampedModel


class Complaint(TimeStampedModel):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    complainant_user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=120)
    description = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    @property
    def complaint_id(self):
        return self.public_id

    class Meta:
        db_table = "complaints_complaint"
        ordering = ["-submitted_at"]


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE,
                                  related_name="attachments")
    name = models.CharField(max_length=120)
    content_type = models.CharField(max_length=120)
    size_bytes = models.PositiveBigIntegerField()
    storage_key = models.CharField(max_length=500, blank=True)
    sha256 = models.CharField(max_length=64)

    class Meta:
        db_table = "complaints_attachment"


class ComplaintNotification(TimeStampedModel):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE,
                                  related_name="notifications")
    recipient_user_id = models.IntegerField(db_index=True)
    recipient_email = models.EmailField(blank=True)
    topic = models.CharField(max_length=80, default="complaint.submitted")
    status = models.CharField(max_length=16, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "complaints_notification"

    def __str__(self):
        return f"{self.topic} -> {self.recipient_user_id} ({self.status})"
