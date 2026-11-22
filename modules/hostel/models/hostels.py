"""Hostel and Room aggregate models.

Institute users are referenced by plain integer user_id.
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class Hostel(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "hostel_hostel"
        indexes = [
            models.Index(fields=["code"], name="hostel_code_idx"),
            models.Index(fields=["is_active"], name="hostel_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class HostelRoleBinding(TimeStampedModel):
    ROLE_CHOICES = [
        ("warden", "Hostel Warden"),
        ("caretaker", "Hostel Caretaker"),
    ]

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="role_bindings")
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    shift_details = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "hostel_role_binding"
        indexes = [
            models.Index(fields=["user_id", "role", "is_active"], name="hostel_binding_user_idx"),
            models.Index(fields=["hostel", "role", "is_active"], name="hostel_binding_hostel_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.role} u{self.user_id} @ {self.hostel.code}"


class Room(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=20)
    capacity = models.PositiveSmallIntegerField(default=1)
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = "hostel_room"
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "room_number"],
                name="hostel_room_unique_number",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gt=0),
                name="hostel_room_capacity_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["hostel", "room_number"], name="hostel_room_num_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.hostel.code}-{self.room_number}"
