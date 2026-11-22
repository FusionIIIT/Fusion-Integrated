"""Accommodations and room allotments models.

Student user_id is integer; isolation via UserScopedModel.
"""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.hostel.models.hostels import Hostel, Room


class AccommodationRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("SUBMITTED", "Submitted"),
        ("ALLOCATED", "Allocated"),
        ("REJECTED", "Rejected"),
    ]

    preferred_hostel = models.ForeignKey(Hostel, on_delete=models.SET_NULL, null=True, blank=True)
    academic_year = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUBMITTED")
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "hostel_accommodation_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="accom_user_status_idx"),
            models.Index(fields=["academic_year", "status"], name="accom_year_status_idx"),
        ]

    def __str__(self) -> str:
        return f"u{self.user_id} - {self.academic_year} ({self.status})"


class RoomAllotment(TimeStampedModel, UserScopedModel):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="allotments")
    academic_year = models.CharField(max_length=20)
    allotted_by_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)
    vacated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "hostel_room_allotment"
        indexes = [
            models.Index(fields=["user_id", "is_active"], name="allot_user_active_idx"),
            models.Index(fields=["room", "is_active"], name="allot_room_active_idx"),
        ]

    def __str__(self) -> str:
        return f"u{self.user_id} in {self.room} ({'active' if self.is_active else 'vacated'})"


class RoomExchange(TimeStampedModel):
    student_a_user_id = models.IntegerField(db_index=True)
    student_b_user_id = models.IntegerField(db_index=True)
    room_a = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="exchanges_from")
    room_b = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="exchanges_to")
    approved_by_user_id = models.IntegerField()
    reason = models.TextField()

    class Meta:
        db_table = "hostel_room_exchange"
        indexes = [
            models.Index(
                fields=["student_a_user_id", "student_b_user_id"],
                name="exchange_students_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Exchange u{self.student_a_user_id} <-> u{self.student_b_user_id}"
