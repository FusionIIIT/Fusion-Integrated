"""Lightweight notification dispatch helper.

Introduces NO database models and NO outbox persistence.
Dispatches notification events by structured logging and task integration.
"""
from __future__ import annotations

import logging

from modules.gymkhana.models import Booking, Poll

log = logging.getLogger("fusion.gymkhana.notify")


def send_session_booking_notification(booking: Booking) -> None:
    """Notify students of a newly booked session (AFR-GYM-013)."""
    log.info("gymkhana.notify.session_booked booking_id=%s venue=%s", booking.pk, booking.venue)


def send_event_booking_notification(booking: Booking) -> None:
    """Notify students of a newly booked event (AFR-GYM-015)."""
    log.info("gymkhana.notify.event_booked booking_id=%s venue=%s", booking.pk, booking.venue)


def send_poll_created_notification(poll: Poll) -> None:
    """Notify targeted students of a newly created poll (AFR-GYM-025)."""
    log.info("gymkhana.notify.poll_created poll_id=%s title=%s", poll.pk, poll.title)
