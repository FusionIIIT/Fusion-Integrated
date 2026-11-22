"""VMS API Integration and Permission Gate Tests."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.vms.services.registration import request_or_create_visit

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, **session_kwargs):
    stub_iam(make_session(**session_kwargs))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def test_unauthenticated_request_denied(client):
    res = client.get("/api/v1/vms/visits/")
    assert res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_missing_module_grant_denied(stub_iam):
    client = _auth_client(stub_iam, user_id=1, modules=(), permissions=("vms.visit.create",))
    res = client.get("/api/v1/vms/visits/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_visit_creation_endpoint(stub_iam):
    client = _auth_client(stub_iam, user_id=10, modules=("vms",), permissions=("vms.visit.create",))
    now = timezone.now()
    payload = {
        "first_name": "Siddharth",
        "last_name": "Rao",
        "phone": "9898989898",
        "email": "sid@example.com",
        "id_type": "aadhaar",
        "id_number": "123412341234",
        "host_user_id": 10,
        "purpose": "Official Meeting",
        "valid_from": (now + timedelta(hours=1)).isoformat(),
        "valid_to": (now + timedelta(hours=4)).isoformat(),
        "allowed_zones": ["MAIN_GATE", "ADMIN_BLOCK"],
        "visit_type": "pre_registered",
    }
    res = client.post("/api/v1/vms/visits/", data=payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    assert "pass_number" in res.data
    assert res.data["status"] == "requested"


def test_visit_scoping_host_sees_only_own_visits(stub_iam):
    now = timezone.now()
    v1 = request_or_create_visit(
        visitor_data={
            "first_name": "V1",
            "last_name": "L1",
            "phone": "90001",
            "email": "v1@ex.com",
            "id_type": "aadhaar",
            "id_number": "ID1",
        },
        host_user_id=101,
        purpose="Host 101 Visit",
        valid_from=now,
        valid_to=now + timedelta(hours=2),
    )
    v2 = request_or_create_visit(
        visitor_data={
            "first_name": "V2",
            "last_name": "L2",
            "phone": "90002",
            "email": "v2@ex.com",
            "id_type": "aadhaar",
            "id_number": "ID2",
        },
        host_user_id=202,
        purpose="Host 202 Visit",
        valid_from=now,
        valid_to=now + timedelta(hours=2),
    )

    client101 = _auth_client(
        stub_iam, user_id=101, modules=("vms",), permissions=("vms.visit.create",)
    )
    res = client101.get("/api/v1/vms/visits/")
    assert res.status_code == status.HTTP_200_OK
    returned_ids = [item["id"] for item in res.data]
    assert v1.id in returned_ids
    assert v2.id not in returned_ids


def test_host_approval_endpoint(stub_iam):
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Deepak",
            "last_name": "Jain",
            "phone": "90003",
            "email": "d@ex.com",
            "id_type": "aadhaar",
            "id_number": "ID3",
        },
        host_user_id=101,
        purpose="Consultation",
        valid_from=now,
        valid_to=now + timedelta(hours=2),
    )
    client = _auth_client(
        stub_iam, user_id=101, modules=("vms",), permissions=("vms.visit.approve",)
    )
    res = client.post(f"/api/v1/vms/visits/{visit.id}/approve/")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["status"] == "approved"


def test_gate_check_in_and_checkout_endpoints(stub_iam):
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Manish",
            "last_name": "Tiwari",
            "phone": "90004",
            "email": "m@ex.com",
            "id_type": "aadhaar",
            "id_number": "ID4",
        },
        host_user_id=101,
        purpose="Lab access",
        valid_from=now - timedelta(minutes=5),
        valid_to=now + timedelta(hours=2),
    )
    visit.status = "approved"
    visit.save()

    guard_client = _auth_client(
        stub_iam, user_id=50, modules=("vms",), permissions=("vms.gate.scan",)
    )
    checkin_res = guard_client.post(
        "/api/v1/vms/gate/check-in/",
        data={"qr_code_hash": visit.qr_code_hash, "gate_name": "Gate 2"},
        format="json",
    )
    assert checkin_res.status_code == status.HTTP_200_OK
    assert checkin_res.data["status"] == "on_site"

    checkout_res = guard_client.post(
        "/api/v1/vms/gate/check-out/",
        data={"visit_id": visit.id, "gate_name": "Gate 2"},
        format="json",
    )
    assert checkout_res.status_code == status.HTTP_200_OK
    assert checkout_res.data["status"] == "completed"


def test_zone_verification_endpoint(stub_iam):
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Rohit",
            "last_name": "Gupta",
            "phone": "90005",
            "email": "r@ex.com",
            "id_type": "aadhaar",
            "id_number": "ID5",
        },
        host_user_id=101,
        purpose="Campus Tour",
        valid_from=now - timedelta(minutes=5),
        valid_to=now + timedelta(hours=2),
        allowed_zones=["MAIN_GATE", "LIBRARY"],
    )
    guard_client = _auth_client(
        stub_iam, user_id=50, modules=("vms",), permissions=("vms.gate.scan",)
    )

    res = guard_client.post(
        "/api/v1/vms/gate/verify-zone/",
        data={"visit_id": visit.id, "requested_zone": "LIBRARY"},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.data["allowed"] is True


def test_offline_sync_api(stub_iam):
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Off",
            "last_name": "Line",
            "phone": "90009",
            "email": "o@ex.com",
            "id_type": "aadhaar",
            "id_number": "IDOFF",
        },
        host_user_id=101,
        purpose="Sync Test",
        valid_from=now - timedelta(minutes=5),
        valid_to=now + timedelta(hours=2),
    )
    visit.status = "approved"
    visit.save()

    guard_client = _auth_client(
        stub_iam, user_id=50, modules=("vms",), permissions=("vms.gate.scan",)
    )
    res = guard_client.post(
        "/api/v1/vms/gate/reconcile-offline/",
        data={"records": [{"qr_code_hash": visit.qr_code_hash, "action": "check_in"}]},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.data["processed"] == 1


def test_admin_alerts_and_blacklist_api(stub_iam):
    admin_client = _auth_client(
        stub_iam, user_id=1, modules=("vms",), permissions=("vms.security.admin",)
    )
    # Post blacklist
    bl_res = admin_client.post(
        "/api/v1/vms/security/blacklist/",
        data={
            "id_type": "aadhaar",
            "id_number": "BL999",
            "full_name": "Blacklisted",
            "reason": "Security Alert",
        },
        format="json",
    )
    assert bl_res.status_code == status.HTTP_201_CREATED

    # Get alerts
    alerts_res = admin_client.get("/api/v1/vms/security/alerts/")
    assert alerts_res.status_code == status.HTTP_200_OK


def test_emergency_muster_api(stub_iam):
    chief_client = _auth_client(
        stub_iam, user_id=1, modules=("vms",), permissions=("vms.emergency.muster",)
    )
    res = chief_client.post("/api/v1/vms/emergency/muster/")
    assert res.status_code == status.HTTP_201_CREATED
    assert "muster_code" in res.data
