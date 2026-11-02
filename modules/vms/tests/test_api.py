"""Integration tests for VMS DRF API endpoints."""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone

from modules.vms.models.visitors import Visitor
from modules.vms.models.visits import VisitRequest, VisitPass
from modules.vms.services.visitor_service import register_visitor
from modules.vms.services.pass_service import issue_visit_pass


class VMSAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.visitor = register_visitor(
            full_name="Deepak Joshi",
            phone="9777777777",
            email="deepak@example.com",
            identity_type="aadhaar",
            id_number="9988-7766-5544",
        )

    def test_visitor_registration_api(self):
        url = "/api/v1/vms/visitors/"
        payload = {
            "full_name": "Meera Nair",
            "phone": "9888888888",
            "email": "meera@example.com",
            "identity_type": "pan",
            "id_number": "MNP9988K",
            "organization": "Academic Press",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["full_name"], "Meera Nair")

    def test_walk_in_registration_gate_api(self):
        url = "/api/v1/vms/gate/walk-in/"
        payload = {
            "full_name": "Walkin Visitor",
            "phone": "9999911111",
            "identity_type": "aadhaar",
            "id_number": "1111-2222-3333",
            "purpose": "Admissions Query",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("pass_number", response.data)
        self.assertEqual(response.data["pass_type"], "walk_in")

    def test_host_approval_workflow_api(self):
        # 1. Create request
        visit = VisitRequest.objects.create(
            visitor=self.visitor,
            host_user_id=1005,
            purpose="PhD Viva",
            intended_start=timezone.now(),
            intended_end=timezone.now() + timezone.timedelta(hours=3),
            status="pending",
        )
        decide_url = f"/api/v1/vms/requests/{visit.id}/decide/"
        
        # 2. Approve request
        payload = {
            "decision": "approved",
            "instructions": "Report directly to Conference Room B.",
        }
        response = self.client.post(decide_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        visit.refresh_from_db()
        self.assertEqual(visit.status, "approved")
        self.assertTrue(visit.passes.filter(status="active").exists())

    def test_gate_check_in_and_check_out_api(self):
        now = timezone.now()
        visit = VisitRequest.objects.create(
            visitor=self.visitor,
            host_user_id=1001,
            purpose="Campus Tour",
            intended_start=now,
            intended_end=now + timezone.timedelta(hours=4),
            status="approved",
        )
        pass_record = issue_visit_pass(visit=visit, pass_type="registered_guest")

        # 1. Gate Check-In API
        checkin_url = "/api/v1/vms/gate/check-in/"
        response = self.client.post(checkin_url, {
            "qr_code_hash": pass_record.qr_code_hash,
            "gate_machine_id": "GATE-READER-01",
            "gate_name": "North Gate",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Gate Check-Out API
        checkout_url = "/api/v1/vms/gate/check-out/"
        response = self.client.post(checkout_url, {
            "pass_number": pass_record.pass_number,
            "gate_machine_id": "GATE-READER-01",
            "gate_name": "North Gate",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pass_record.refresh_from_db()
        self.assertEqual(pass_record.status, "completed")
