"""Offline-sanctioned leave synchronization models.

Implements retrospective offline record capture (EL-UC-016 / BR-EL-029).
"""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.models.requests import LeaveRequest


class OfflineLeaveRecord(TimeStampedModel):
    request = models.OneToOneField(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="offline_details",
    )
    sanction_reference_number = models.CharField(max_length=100)
    sanction_date = models.DateField()
    sanctioning_authority_name = models.CharField(max_length=150)
    offline_reason = models.TextField()
    entered_by_user_id = models.IntegerField()

    class Meta:
        ordering = ["-created_at"]
