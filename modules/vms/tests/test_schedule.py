"""VMS Celery Tasks Tests."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models.access import GateAlert
from modules.vms.services.registration import request_or_create_visit
from modules.vms.tasks import check_overstays, expire_stale_visits

pytestmark = pytest.mark.django_db


def test_overstay_task_detection():
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Overstay",
            "last_name": "Guest",
            "phone": "9777111222",
            "email": "overstay@example.com",
            "id_type": "aadhaar",
            "id_number": "776655443322",
        },
        host_user_id=1,
        purpose="Old Meeting",
        valid_from=now - timedelta(hours=5),
        valid_to=now - timedelta(hours=1),
    )
    visit.status = "on_site"
    visit.save()

    count = check_overstays()
    assert count >= 1
    assert GateAlert.objects.filter(alert_type="overstay", visit_id=visit.id).exists()


def test_stale_request_expiry_task():
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Stale",
            "last_name": "Guest",
            "phone": "9777222333",
            "email": "stale@example.com",
            "id_type": "aadhaar",
            "id_number": "334455667788",
        },
        host_user_id=1,
        purpose="Past Date",
        valid_from=now - timedelta(days=2),
        valid_to=now - timedelta(days=1),
    )
    assert visit.status == "requested"

    updated = expire_stale_visits()
    assert updated >= 1
    visit.refresh_from_db()
    assert visit.status == "expired"
