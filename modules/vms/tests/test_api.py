"""Comprehensive integration tests for VMS Django REST Framework API endpoints."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from modules.vms.models import (
    CampusGate,
    Host,
    PassStatus,
    RequestStatus,
    Visitor,
    VisitorPass,
    VisitRequest,
)


@pytest.mark.django_db
class TestVmsApiEndpointsComprehensive:
    """Exhaustive tests for HTTP status codes, serializers, and JSON responses."""

    @pytest.fixture
    def client(self):
        return APIClient()

    @pytest.fixture
    def setup_api_data(self):
        host = Host.objects.create(
            user_id=101,
            employee_id="EMP-API-101",
            full_name="Prof. API Host",
            department="CSE",
            designation="Professor",
            email="apihost@iiitdmj.ac.in",
        )
        gate = CampusGate.objects.create(
            gate_id="GATE-API-01",
            gate_name="North Gate",
            location_zone="MAIN_CAMPUS",
            is_operational=True,
        )
        return host, gate

    def test_pre_register_endpoint_success(self, client, setup_api_data):
        host, _ = setup_api_data
        now = timezone.now()
        payload = {
            "visitor_name": "API Test Visitor",
            "visitor_phone": "9800012345",
            "visitor_email": "api_visitor@test.org",
            "id_doc_type": "AADHAAR",
            "id_doc_number": "1234-5555-6666",
            "organization": "API Corp",
            "host_id": host.user_id,
            "purpose": "API Verification",
            "scheduled_start": now.isoformat(),
            "scheduled_end": (now + timedelta(hours=2)).isoformat(),
            "remarks": "Automated API test",
        }
        res = client.post("/api/v1/vms/requests/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()
        assert "request_id" in data
        assert data["status"] == "PENDING_HOST_APPROVAL"

    def test_pre_register_endpoint_invalid_time(self, client, setup_api_data):
        host, _ = setup_api_data
        now = timezone.now()
        payload = {
            "visitor_name": "Invalid Time Visitor",
            "visitor_phone": "9800012346",
            "visitor_email": "inv@test.org",
            "id_doc_type": "AADHAAR",
            "id_doc_number": "1234-5555-7777",
            "host_id": host.user_id,
            "purpose": "Invalid Window",
            "scheduled_start": now.isoformat(),
            "scheduled_end": (now - timedelta(hours=1)).isoformat(),
        }
        res = client.post("/api/v1/vms/requests/", payload, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_pre_register_endpoint_missing_mandatory_field(self, client, setup_api_data):
        host, _ = setup_api_data
        now = timezone.now()
        payload = {
            "visitor_name": "Incomplete Visitor",
            "host_id": host.user_id,
            "purpose": "Incomplete",
            "scheduled_start": now.isoformat(),
            "scheduled_end": (now + timedelta(hours=2)).isoformat(),
        }
        res = client.post("/api/v1/vms/requests/", payload, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_requests_list_endpoint(self, client, setup_api_data):
        res = client.get("/api/v1/vms/requests/")
        assert res.status_code == status.HTTP_200_OK
        assert isinstance(res.json(), list)

    def test_host_pending_requests_endpoint(self, client, setup_api_data):
        host, _ = setup_api_data
        res = client.get(f"/api/v1/vms/host/pending/?user_id={host.user_id}")
        assert res.status_code == status.HTTP_200_OK
        assert isinstance(res.json(), list)

    def test_host_pending_requests_default_user(self, client):
        res = client.get("/api/v1/vms/host/pending/")
        assert res.status_code == status.HTTP_200_OK

    def test_host_pending_requests_empty_for_unrelated_host(self, client):
        res = client.get("/api/v1/vms/host/pending/?user_id=98765")
        assert res.status_code == status.HTTP_200_OK
        assert len(res.json()) == 0

    def test_host_decision_endpoint_approve(self, client, setup_api_data):
        host, _ = setup_api_data
        now = timezone.now()
        v = Visitor.objects.create(
            full_name="Decide Visitor",
            phone="9800000001",
            email="d@test.org",
            id_document_number="DOC-D",
        )
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Decide Meeting",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.PENDING_HOST_APPROVAL,
        )
        payload = {
            "user_id": host.user_id,
            "outcome": "APPROVE",
            "permitted_zones": ["MAIN_CAMPUS", "ACADEMIC_ZONE"],
            "special_instructions": "Wear visitor ID badge at all times",
        }
        res = client.post(
            f"/api/v1/vms/requests/{req.request_id}/decision/", payload, format="json"
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["outcome"] == "APPROVE"
        assert data["pass"] is not None

    def test_host_decision_endpoint_reject(self, client, setup_api_data):
        host, _ = setup_api_data
        now = timezone.now()
        v = Visitor.objects.create(
            full_name="Reject Visitor",
            phone="9800000002",
            email="rej@test.org",
            id_document_number="DOC-REJ",
        )
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Reject Meeting",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.PENDING_HOST_APPROVAL,
        )
        payload = {
            "user_id": host.user_id,
            "outcome": "REJECT",
        }
        res = client.post(
            f"/api/v1/vms/requests/{req.request_id}/decision/", payload, format="json"
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["outcome"] == "REJECT"
        assert data["pass"] is None

    def test_host_decision_endpoint_already_approved_fails(self, client, setup_api_data):
        host, _ = setup_api_data
        now = timezone.now()
        v = Visitor.objects.create(
            full_name="Double Decide",
            phone="9800000003",
            email="dd@test.org",
            id_document_number="DOC-DD",
        )
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Double Meeting",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.APPROVED,
        )
        payload = {"outcome": "APPROVE"}
        res = client.post(
            f"/api/v1/vms/requests/{req.request_id}/decision/", payload, format="json"
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_host_decision_endpoint_invalid_outcome(self, client, setup_api_data):
        _, _ = setup_api_data
        payload = {"outcome": "INVALID_DECISION"}
        res = client.post("/api/v1/vms/requests/REQ-123/decision/", payload, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_gate_validate_endpoint_valid(self, client, setup_api_data):
        host, gate = setup_api_data
        now = timezone.now()
        v = Visitor.objects.create(
            full_name="Gate Visitor",
            phone="9800000004",
            email="g@test.org",
            id_document_number="DOC-G",
        )
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Gate Meeting",
            scheduled_start_time=now - timedelta(minutes=10),
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.APPROVED,
        )
        pass_obj = VisitorPass.objects.create(
            request=req,
            credential_data="token-api-test-01",
            valid_from=now - timedelta(minutes=15),
            valid_until=now + timedelta(hours=2),
            status=PassStatus.ACTIVE,
            permitted_zones=["MAIN_CAMPUS"],
        )
        payload = {
            "credential_data": pass_obj.credential_data,
            "gate_id": gate.gate_id,
        }
        res = client.post("/api/v1/vms/gate/validate/", payload, format="json")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["allowed"] is True

    def test_gate_validate_endpoint_invalid_token(self, client, setup_api_data):
        _, gate = setup_api_data
        payload = {
            "credential_data": "invalid-token-xyz",
            "gate_id": gate.gate_id,
        }
        res = client.post("/api/v1/vms/gate/validate/", payload, format="json")
        assert res.status_code == status.HTTP_403_FORBIDDEN
        data = res.json()
        assert data["allowed"] is False

    def test_gate_validate_endpoint_expired_pass(self, client, setup_api_data):
        host, gate = setup_api_data
        now = timezone.now()
        v = Visitor.objects.create(
            full_name="Expired Visitor",
            phone="9800000005",
            email="exp@test.org",
            id_document_number="DOC-EXP",
        )
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Expired Meeting",
            scheduled_start_time=now - timedelta(hours=5),
            scheduled_end_time=now - timedelta(hours=1),
            status=RequestStatus.APPROVED,
        )
        pass_obj = VisitorPass.objects.create(
            request=req,
            credential_data="token-api-expired",
            valid_from=now - timedelta(hours=5),
            valid_until=now - timedelta(hours=1),
            status=PassStatus.EXPIRED,
            permitted_zones=["MAIN_CAMPUS"],
        )
        payload = {
            "credential_data": pass_obj.credential_data,
            "gate_id": gate.gate_id,
        }
        res = client.post("/api/v1/vms/gate/validate/", payload, format="json")
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert res.json()["allowed"] is False

    def test_gate_validate_endpoint_missing_fields(self, client):
        res = client.post("/api/v1/vms/gate/validate/", {}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_gate_checkout_endpoint_success(self, client, setup_api_data):
        host, gate = setup_api_data
        now = timezone.now()
        v = Visitor.objects.create(
            full_name="Checkout API",
            phone="9800000006",
            email="co_api@test.org",
            id_document_number="DOC-CO-API",
        )
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="CO API Meeting",
            scheduled_start_time=now - timedelta(minutes=10),
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.APPROVED,
        )
        pass_obj = VisitorPass.objects.create(
            request=req,
            credential_data="token-api-co",
            valid_from=now - timedelta(minutes=15),
            valid_until=now + timedelta(hours=2),
            status=PassStatus.ACTIVE,
            permitted_zones=["MAIN_CAMPUS"],
        )
        # Check in first
        client.post(
            "/api/v1/vms/gate/validate/",
            {
                "credential_data": pass_obj.credential_data,
                "gate_id": gate.gate_id,
            },
            format="json",
        )

        # Now checkout
        res = client.post(
            "/api/v1/vms/gate/checkout/",
            {
                "pass_id": pass_obj.pass_id,
                "gate_id": gate.gate_id,
                "verifier_notes": "Checked out smoothly",
            },
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["status"] == "COMPLETED"

    def test_gate_checkout_endpoint_without_checkin_fails(self, client, setup_api_data):
        _, gate = setup_api_data
        res = client.post(
            "/api/v1/vms/gate/checkout/",
            {
                "pass_id": "NON-EXISTENT-PASS",
                "gate_id": gate.gate_id,
            },
            format="json",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_gate_checkout_missing_fields(self, client):
        res = client.post("/api/v1/vms/gate/checkout/", {}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_gate_checkout_double_checkout_fails(self, client, setup_api_data):
        host, gate = setup_api_data
        now = timezone.now()
        v = Visitor.objects.create(
            full_name="Double CO",
            phone="9800000007",
            email="dco@test.org",
            id_document_number="DOC-DCO",
        )
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Double CO Meeting",
            scheduled_start_time=now - timedelta(minutes=10),
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.APPROVED,
        )
        pass_obj = VisitorPass.objects.create(
            request=req,
            credential_data="token-api-dco",
            valid_from=now - timedelta(minutes=15),
            valid_until=now + timedelta(hours=2),
            status=PassStatus.ACTIVE,
            permitted_zones=["MAIN_CAMPUS"],
        )
        client.post(
            "/api/v1/vms/gate/validate/",
            {
                "credential_data": pass_obj.credential_data,
                "gate_id": gate.gate_id,
            },
            format="json",
        )
        # First checkout
        res1 = client.post(
            "/api/v1/vms/gate/checkout/",
            {
                "pass_id": pass_obj.pass_id,
                "gate_id": gate.gate_id,
            },
            format="json",
        )
        assert res1.status_code == status.HTTP_200_OK

        # Second checkout must fail
        res2 = client.post(
            "/api/v1/vms/gate/checkout/",
            {
                "pass_id": pass_obj.pass_id,
                "gate_id": gate.gate_id,
            },
            format="json",
        )
        assert res2.status_code == status.HTTP_400_BAD_REQUEST

    def test_active_passes_endpoint(self, client):
        res = client.get("/api/v1/vms/passes/active/")
        assert res.status_code == status.HTTP_200_OK
        assert isinstance(res.json(), list)

    def test_active_visits_endpoint(self, client):
        res = client.get("/api/v1/vms/visits/active/")
        assert res.status_code == status.HTTP_200_OK
        assert isinstance(res.json(), list)

    def test_campus_gates_endpoint(self, client):
        res = client.get("/api/v1/vms/gates/")
        assert res.status_code == status.HTTP_200_OK
        assert isinstance(res.json(), list)

    def test_campus_gates_endpoint_returns_operational(self, client, setup_api_data):
        _, gate = setup_api_data
        res = client.get("/api/v1/vms/gates/")
        assert res.status_code == status.HTTP_200_OK
        gates = res.json()
        assert any(g["gate_id"] == gate.gate_id for g in gates)

    def test_active_passes_content_structure(self, client, setup_api_data):
        host, _ = setup_api_data
        now = timezone.now()
        v = Visitor.objects.create(
            full_name="Pass Content V",
            phone="9800000008",
            email="pc@test.org",
            id_document_number="DOC-PC",
        )
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Pass Structure",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.APPROVED,
        )
        VisitorPass.objects.create(
            request=req,
            credential_data="token-api-struct",
            valid_from=now,
            valid_until=now + timedelta(hours=2),
            status=PassStatus.ACTIVE,
        )
        res = client.get("/api/v1/vms/passes/active/")
        assert res.status_code == status.HTTP_200_OK
        items = res.json()
        assert len(items) >= 1
        assert "pass_id" in items[0]
        assert "visitor_name" in items[0]

    def test_active_visits_content_structure(self, client, setup_api_data):
        host, gate = setup_api_data
        now = timezone.now()
        v = Visitor.objects.create(
            full_name="Visit Content V",
            phone="9800000009",
            email="vc@test.org",
            id_document_number="DOC-VC",
        )
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Visit Structure",
            scheduled_start_time=now - timedelta(minutes=5),
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.APPROVED,
        )
        pass_obj = VisitorPass.objects.create(
            request=req,
            credential_data="token-api-visit-struct",
            valid_from=now - timedelta(minutes=5),
            valid_until=now + timedelta(hours=2),
            status=PassStatus.ACTIVE,
        )
        client.post(
            "/api/v1/vms/gate/validate/",
            {
                "credential_data": pass_obj.credential_data,
                "gate_id": gate.gate_id,
            },
            format="json",
        )
        res = client.get("/api/v1/vms/visits/active/")
        assert res.status_code == status.HTTP_200_OK
        items = res.json()
        assert len(items) >= 1
        assert "log_id" in items[0]
        assert "entry_gate_name" in items[0]
