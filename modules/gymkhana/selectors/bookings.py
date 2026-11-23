from datetime import date, time

from django.db.models import Q, QuerySet

from modules.gymkhana.models.booking import ClubBooking
from modules.gymkhana.models.club import Club
from modules.gymkhana.selectors.scoping import scope_bookings


def list_bookings(user, club: Club, booking_date: date | None = None) -> QuerySet[ClubBooking]:
    qs = scope_bookings(user, club)
    if booking_date:
        qs = qs.filter(date=booking_date)
    return qs.order_by("date", "start_time")


def has_venue_overlap(
    venue: str,
    booking_date: date,
    start_time: time,
    end_time: time,
    exclude_id: int | None = None,
) -> bool:
    qs = ClubBooking.objects.filter(
        venue=venue,
        date=booking_date,
    ).filter(Q(start_time__lt=end_time) & Q(end_time__gt=start_time))
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()
