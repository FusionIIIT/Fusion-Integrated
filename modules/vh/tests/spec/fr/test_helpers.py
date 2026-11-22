"""Reusable data helpers for VH Student 2 backend specification tests."""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from django.utils import timezone

from modules.vh.models import Booking, BookingStatus

ROOT = Path(__file__).resolve().parents[5]


def load_design(strategy: str) -> list[dict]:
    path = ROOT / "docs" / "09-vh" / "spec-tests" / f"{strategy.upper()}_DESIGN.json"
    return json.loads(path.read_text(encoding="utf-8"))


def case_id(case: dict) -> str:
    return f"{case['test_id']}__{case['source_id'].replace(' ', '_')}"


def make_booking(category, *, status=BookingStatus.PENDING, days=10, stay=2, rooms=1, indenter_id=1, **extra):
    today = timezone.localdate()
    data = {
        "indenter_id": indenter_id,
        "visitor_name": "Spec Guest",
        "visitor_email": "guest@example.test",
        "visitor_category": category,
        "visit_purpose": "Specification test stay",
        "check_in_date": today + timedelta(days=days),
        "check_out_date": today + timedelta(days=days + stay),
        "number_of_rooms": rooms,
        "number_of_occupants": 1,
        "status": status,
        "billing_responsibility": "VISITOR",
    }
    data.update(extra)
    return Booking.objects.create(**data)


def booking_payload(category_id, *, days=10, stay=2, **extra):
    today = timezone.localdate()
    data = {
        "indenter_id": 1,
        "visitor_name": "Spec Guest",
        "visitor_email": "guest@example.test",
        "visitor_category": category_id,
        "visit_purpose": "Specification test stay",
        "check_in_date": str(today + timedelta(days=days)),
        "check_out_date": str(today + timedelta(days=days + stay)),
        "expected_check_in_time": "15:00:00",
        "expected_check_out_time": "11:00:00",
        "number_of_rooms": 1,
        "number_of_occupants": 1,
        "billing_responsibility": "VISITOR",
    }
    data.update(extra)
    return data


def post_booking(api_client, category_id, *, days=10, stay=2, **extra):
    return api_client.post(
        "/api/v1/vh/bookings/",
        booking_payload(category_id, days=days, stay=stay, **extra),
        format="json",
    )
