"""Celery tasks for Hostel Management."""

from celery import shared_task
from django.utils import timezone

from modules.hostel.models import GuestRoomBooking


@shared_task
def auto_expire_guest_bookings() -> int:
    today = timezone.localdate()
    return GuestRoomBooking.objects.filter(
        status="REQUESTED", check_in__lt=today
    ).update(status="CANCELLED")
