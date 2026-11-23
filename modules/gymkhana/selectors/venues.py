"""Venues configured for Gymkhana booking (BR-GYM-020)."""

from __future__ import annotations

from django.conf import settings

DEFAULT_VENUES = (
    "Hall 1",
    "Hall 2",
    "L-101",
    "L-102",
    "Open Air Theatre",
    "SAC Gym",
    "Football Ground",
    "Basketball Court",
    "Badminton Court",
    "Volleyball Court",
)


def configured_venues() -> list[str]:
    return list(getattr(settings, "GYMKHANA_CONFIGURED_VENUES", DEFAULT_VENUES))
