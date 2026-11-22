"""API integration tests for hostel endpoints."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hostel.models import Hostel

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, user_id=1001, role="student", permissions=(), modules=("hostel",)):
    session = make_session(
        user_id=user_id,
        role=role,
        modules=modules,
        permissions=permissions,
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def test_hostels_list_endpoint(stub_iam):
    Hostel.objects.create(name="Hall of Residence 1", code="HALL-1", is_active=True)
    Hostel.objects.create(name="Hall of Residence 2", code="HALL-2", is_active=True)

    client = _auth_client(
        stub_iam,
        user_id=1001,
        role="student",
        permissions=["hostel.room.view"],
    )

    resp = client.get("/api/v1/hostel/hostels/")
    assert resp.status_code == 200
    assert len(resp.data) == 2


def test_accommodation_request_submission(stub_iam):
    hostel = Hostel.objects.create(name="Hall of Residence 3", code="HALL-3", is_active=True)
    client = _auth_client(
        stub_iam,
        user_id=2001,
        role="student",
        permissions=["hostel.accommodation.create", "hostel.accommodation.view"],
    )

    payload = {
        "preferred_hostel": hostel.id,
        "academic_year": "2026-2027",
        "remarks": "Medical request",
    }
    resp = client.post("/api/v1/hostel/accommodations/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["user_id"] == 2001
    assert resp.data["status"] == "SUBMITTED"
