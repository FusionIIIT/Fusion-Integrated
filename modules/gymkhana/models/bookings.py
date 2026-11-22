"""Sessions and events share one table so venue exclusivity is one query (BR-GYM-006)."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.clubs import Club


class VenueDay(models.Model):
    """Locked by every booking for its venue and date, so overlapping requests serialize."""

    venue_name = models.CharField(max_length=120)
    date = models.DateField()

    class Meta:
        db_table = "gymkhana_venue_day"
        constraints = [
            models.UniqueConstraint(fields=["venue_name", "date"],
                                    name="gym_venueday_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.venue_name} {self.date}"


BOOKING_KINDS = ("session", "event")


class Booking(TimeStampedModel):
    SESSION, EVENT = BOOKING_KINDS
    KIND_CHOICES = [(SESSION, "Session"), (EVENT, "Event")]

    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="bookings")
    kind = models.CharField(max_length=8, choices=KIND_CHOICES)
    venue_name = models.CharField(max_length=120)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(max_length=4000)
    poster_link = models.CharField(max_length=300, blank=True)
    poster_file_id = models.CharField(max_length=200, blank=True)
    event_name = models.CharField(max_length=200, blank=True)
    faculty_user_id = models.IntegerField(null=True, blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "gymkhana_booking"
        constraints = [
            models.CheckConstraint(condition=Q(start_time__lt=models.F("end_time")),
                                   name="gym_booking_start_before_end"),
            models.CheckConstraint(condition=Q(kind__in=BOOKING_KINDS),
                                   name="gym_booking_kind_valid"),
            models.CheckConstraint(
                condition=Q(kind="session") | (
                    ~Q(event_name="") & ~Q(poster_file_id="")
                    & Q(faculty_user_id__isnull=False)),
                name="gym_booking_event_complete"),
        ]
        indexes = [
            models.Index(fields=["venue_name", "date", "start_time"],
                         name="gym_booking_venue_date_idx"),
            models.Index(fields=["club", "date"], name="gym_booking_club_date_idx"),
        ]
