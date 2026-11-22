"""VMS Public Contracts Tests.
Verifies contract DTOs and public querying interfaces.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms import contracts
from modules.vms.models.visitors import BlacklistEntry
from modules.vms.services.registration import request_or_create_visit

pytestmark = pytest.mark.django_db


def test_get_active_visitors_on_campus():
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Rohan",
            "last_name": "Mehta",
            "phone": "9812345678",
            "email": "rohan@example.com",
            "id_type": "aadhaar",
            "id_number": "999888777666",
        },
        host_user_id=101,
        purpose="Campus Interview",
        valid_from=now,
        valid_to=now + timedelta(hours=3),
    )
    visit.status = "on_site"
    visit.check_in_time = now
    visit.save()

    active = contracts.get_active_visitors_on_campus()
    assert len(active) >= 1
    dto = next(a for a in active if a.visitor_id == visit.visitor.id)
    assert dto.full_name == "Rohan Mehta"
    assert dto.host_user_id == 101


def test_get_visitor_clearance_status():
    h_clean = "HASH_CLEAN_VISITOR"
    h_blacklisted = "HASH_BL_VISITOR"

    BlacklistEntry.objects.create(
        id_number_hash=h_blacklisted,
        full_name="Banned Guest",
        phone="9000000000",
        reason="Test blacklist",
        severity="critical",
    )

    res = contracts.get_visitor_clearance_status([h_clean, h_blacklisted])
    assert res[h_clean].is_cleared is True
    assert res[h_clean].is_blacklisted is False

    assert res[h_blacklisted].is_cleared is False
    assert res[h_blacklisted].is_blacklisted is True


def test_is_host_entertaining_visitors():
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Sameer",
            "last_name": "Khan",
            "phone": "9876541230",
            "email": "sameer@example.com",
            "id_type": "aadhaar",
            "id_number": "111222333444",
        },
        host_user_id=505,
        purpose="Faculty Consultation",
        valid_from=now,
        valid_to=now + timedelta(hours=2),
    )
    visit.status = "on_site"
    visit.save()

    res = contracts.is_host_entertaining_visitors([505, 999])
    assert res[505] is True
    assert res[999] is False
