from django.db import models
from django.db.models import CheckConstraint, F, Index, Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.domain.constants import BOOKING_TYPES, CONFIGURED_VENUES
from modules.gymkhana.models.club import Club


class ClubBooking(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="bookings")
    booking_type = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    venue = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True)
    created_by_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "gymkhana_booking"
        indexes = [
            Index(fields=["venue", "date"], name="gym_book_venue_date_idx"),
            Index(fields=["club", "date"], name="gym_book_club_date_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(start_time__lt=F("end_time")),
                name="gymkhana_booking_valid_time_range",
            ),
            CheckConstraint(
                condition=Q(booking_type__in=list(BOOKING_TYPES)),
                name="gymkhana_booking_valid_type",
            ),
            CheckConstraint(
                condition=Q(venue__in=list(CONFIGURED_VENUES)),
                name="gymkhana_booking_valid_venue",
            ),
        ]
