from django.db import models
from django.db.models import F, Q

from modules.gymkhana.models.club import Club


class VenueDayLock(models.Model):
    venue = models.CharField(max_length=60)
    date = models.DateField()

    class Meta:
        db_table = "gymkhana_venuedaylock"
        indexes = [
            models.Index(fields=["venue", "date"], name="gymkhana_venueday_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["venue", "date"],
                name="gymkhana_venueday_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"Lock: {self.venue} on {self.date}"


class Booking(models.Model):
    TYPE_CHOICES = [
        ("session", "Session"),
        ("event", "Event"),
    ]

    booking_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    venue = models.CharField(max_length=60)
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    name = models.CharField(max_length=150, blank=True, default="")
    description = models.TextField()
    poster_url = models.CharField(max_length=500, blank=True, default="")
    poster_file_id = models.CharField(max_length=200, blank=True, default="")
    faculty_councillor_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_booking"
        indexes = [
            models.Index(
                fields=["venue", "date", "start_time"],
                name="gymkhana_bk_venue_slot_idx",
            ),
            models.Index(fields=["club", "date"], name="gymkhana_booking_club_date_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(start_time__lt=F("end_time")),
                name="gymkhana_booking_time_valid",
            ),
            models.CheckConstraint(
                condition=Q(booking_type__in=["session", "event"]),
                name="gymkhana_booking_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.booking_type.capitalize()} ({self.club.name}) in {self.venue} "
            f"on {self.date} {self.start_time}-{self.end_time}"
        )
