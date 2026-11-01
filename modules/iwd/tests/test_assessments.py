"""Targeted tests for IWD technical assessment and estimate initiation (Increment 4).

Verifies:
- Assessment recording (UC-IWD-015, BW-IWD-01 Step 3): Assigned -> Assessed
- Estimate preparation & submission (UC-IWD-021, BW-IWD-02/03/05 Step 1; CW-IWD-01)
- Exact cost-band boundary routing:
    • Decimal("24999.99") -> Low-Cost Review Pending
    • Decimal("25000.00") -> Mid-Range Committee Review Pending
    • Decimal("250000.00") -> Mid-Range Committee Review Pending
    • Decimal("250000.01") -> Director Review Pending (High-Cost)
- Active-role authorization isolation (rejecting dormant iwd_engineer roles)
- Assignment ownership isolation (rejecting peer engineer assessment/estimate)
- Rejection of invalid transitions and out-of-order attempts
- Transactional consistency and audit logging
- API backward-compatibility on complaint detail endpoint
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.iwd.domain.cost_bands import CostBand
from modules.iwd.domain.state_machine import IWDState
from modules.iwd.models import Complaint, ComplaintTransition, Estimate
from modules.iwd.services.assessments import record_complaint_assessment
from modules.iwd.services.estimates import submit_complaint_estimate

pytestmark = pytest.mark.django_db


# -- Helpers -------------------------------------------------------------------

def make_client_for_session(stub_iam, session):
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-valid-token")
    return client


def make_engineer_principal(user_id: int = 501, active_role: str = "iwd_engineer", roles: tuple[str, ...] = ("iwd_engineer",), permissions: tuple[str, ...] = ("iwd.complaint.assess", "iwd.complaint.view")):
    return make_session(
        user_id=user_id,
        permissions=permissions,
        modules=("iwd",),
        active_role=active_role,
        roles=roles,
    )


def create_assigned_complaint(assigned_engineer_id: int = 501, complainant_id: int = 101) -> Complaint:
    complaint = Complaint.objects.create(
        user_id=complainant_id,
        category="civil",
        location="Hostel 4, Room 202",
        urgency="medium",
        remarks="Door hinge broken",
        status=IWDState.ASSIGNED.value,
        assigned_engineer_id=assigned_engineer_id,
    )
    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=IWDState.SUBMITTED.value,
        to_status=IWDState.ASSIGNED.value,
        actor_user_id=None,
        actor_label="System",
        reason="Auto-assigned",
    )
    return complaint


def create_assessed_complaint(assigned_engineer_id: int = 501, complainant_id: int = 101) -> Complaint:
    complaint = create_assigned_complaint(assigned_engineer_id, complainant_id)
    complaint.status = IWDState.ASSESSED.value
    complaint.assessment_details = "Door hinge worn out, requires replacement and alignment"
    complaint.save(update_fields=["status", "assessment_details", "updated_at"])
    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=IWDState.ASSIGNED.value,
        to_status=IWDState.ASSESSED.value,
        actor_user_id=assigned_engineer_id,
        actor_label="Engineer",
        reason="Technical assessment recorded",
    )
    return complaint


# -- 1. Assessment Service Tests -----------------------------------------------

class TestAssessmentServices:
    def test_record_assessment_success(self):
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        principal = make_engineer_principal(user_id=501)

        updated = record_complaint_assessment(
            complaint_id=complaint.pk,
            principal=principal,
            assessment_details="Replaced hydraulic door closer and aligned lock frame.",
        )

        assert updated.status == IWDState.ASSESSED.value
        assert updated.assessment_details == "Replaced hydraulic door closer and aligned lock frame."
        assert updated.assessed_at is not None

        # Verify transition row
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.from_status == IWDState.ASSIGNED.value
        assert trans.to_status == IWDState.ASSESSED.value
        assert trans.actor_user_id == 501
        assert trans.actor_label == "Engineer"

    def test_record_assessment_blank_findings_raises_bad_request(self):
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        principal = make_engineer_principal(user_id=501)

        with pytest.raises(BadRequestError) as exc_info:
            record_complaint_assessment(
                complaint_id=complaint.pk,
                principal=principal,
                assessment_details="   \n  ",
            )
        assert exc_info.value.code == "blank_assessment"

    def test_record_assessment_invalid_state_raises_conflict(self):
        # Complaint in Submitted state cannot be assessed directly
        complaint = Complaint.objects.create(
            user_id=101,
            category="civil",
            location="Room A",
            status=IWDState.SUBMITTED.value,
            assigned_engineer_id=501,
        )
        principal = make_engineer_principal(user_id=501)

        with pytest.raises(ConflictError) as exc_info:
            record_complaint_assessment(
                complaint_id=complaint.pk,
                principal=principal,
                assessment_details="Valid findings",
            )
        assert exc_info.value.code == "invalid_state_transition"

    def test_record_assessment_dormant_engineer_role_denied(self):
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        # Principal has iwd_engineer in dormant roles, but active_role is faculty
        dormant_principal = make_engineer_principal(
            user_id=501,
            active_role="faculty",
            roles=("faculty", "iwd_engineer"),
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            record_complaint_assessment(
                complaint_id=complaint.pk,
                principal=dormant_principal,
                assessment_details="Valid findings",
            )
        assert exc_info.value.code == "active_role_required"

    def test_record_assessment_missing_permission_denied(self):
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        principal = make_session(
            user_id=501,
            permissions=("iwd.complaint.view",),  # missing iwd.complaint.assess
            modules=("iwd",),
            active_role="iwd_engineer",
            roles=("iwd_engineer",),
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            record_complaint_assessment(
                complaint_id=complaint.pk,
                principal=principal,
                assessment_details="Valid findings",
            )
        assert exc_info.value.code == "permission_denied"

    def test_record_assessment_peer_complaint_denied(self):
        # Complaint is assigned to engineer 501, engineer 502 attempts to assess
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        peer_principal = make_engineer_principal(user_id=502)

        with pytest.raises(PermissionDeniedError) as exc_info:
            record_complaint_assessment(
                complaint_id=complaint.pk,
                principal=peer_principal,
                assessment_details="Valid findings",
            )
        assert exc_info.value.code == "complaint_not_assigned_to_caller"

    def test_record_assessment_nonexistent_complaint_raises_not_found(self):
        principal = make_engineer_principal(user_id=501)

        with pytest.raises(NotFoundError):
            record_complaint_assessment(
                complaint_id=999999,
                principal=principal,
                assessment_details="Valid findings",
            )


# -- 2. Estimate Service Tests -------------------------------------------------

class TestEstimateServices:
    def test_submit_estimate_low_cost_boundary(self):
        """₹24,999.99 routes to Low-Cost Review Pending (BW-IWD-02)."""
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        principal = make_engineer_principal(user_id=501)

        updated_complaint, estimate = submit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("24999.99"),
            estimated_time="2 days",
            materials_summary="2x Door hinges, 1x hydraulic closer, mounting screws",
            supporting_details="Standard replacement parts",
        )

        assert updated_complaint.status == IWDState.LOW_COST_REVIEW_PENDING.value
        assert estimate.cost_band == CostBand.LOW.value
        assert estimate.estimated_cost == Decimal("24999.99")
        assert estimate.engineer_id == 501

        # Check audit trail
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.from_status == IWDState.ASSESSED.value
        assert trans.to_status == IWDState.LOW_COST_REVIEW_PENDING.value
        assert "24999.99" in trans.reason

    def test_submit_estimate_mid_range_lower_boundary(self):
        """₹25,000.00 routes to Mid-Range Committee Review Pending (BW-IWD-03)."""
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        principal = make_engineer_principal(user_id=501)

        updated_complaint, estimate = submit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("25000.00"),
            estimated_time="1 week",
            materials_summary="Sub-distribution panel and MCBs",
        )

        assert updated_complaint.status == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value
        assert estimate.cost_band == CostBand.MID.value
        assert estimate.estimated_cost == Decimal("25000.00")

    def test_submit_estimate_mid_range_upper_boundary(self):
        """₹250,000.00 routes to Mid-Range Committee Review Pending (BW-IWD-03)."""
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        principal = make_engineer_principal(user_id=501)

        updated_complaint, estimate = submit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("250000.00"),
            estimated_time="3 weeks",
            materials_summary="Laboratory HVAC ducting and compressor repair",
        )

        assert updated_complaint.status == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value
        assert estimate.cost_band == CostBand.MID.value
        assert estimate.estimated_cost == Decimal("250000.00")

    def test_submit_estimate_high_cost_boundary(self):
        """₹250,000.01 routes to Director Review Pending (High-Cost) (BW-IWD-05)."""
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        principal = make_engineer_principal(user_id=501)

        updated_complaint, estimate = submit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("250000.01"),
            estimated_time="2 months",
            materials_summary="Complete building rewiring and transformer replacement",
        )

        assert updated_complaint.status == IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value
        assert estimate.cost_band == CostBand.HIGH.value
        assert estimate.estimated_cost == Decimal("250000.01")

    def test_submit_estimate_before_assessment_denied(self):
        """Attempting to submit an estimate on an Assigned complaint is rejected."""
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        principal = make_engineer_principal(user_id=501)

        with pytest.raises(ConflictError) as exc_info:
            submit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=principal,
                estimated_cost=Decimal("15000.00"),
                estimated_time="1 day",
                materials_summary="Pipes and fittings",
            )
        assert exc_info.value.code == "invalid_state_transition"

    def test_submit_estimate_dormant_role_denied(self):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        dormant_principal = make_engineer_principal(
            user_id=501,
            active_role="faculty",
            roles=("faculty", "iwd_engineer"),
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            submit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=dormant_principal,
                estimated_cost=Decimal("15000.00"),
                estimated_time="1 day",
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "active_role_required"

    def test_submit_estimate_peer_complaint_denied(self):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        peer_principal = make_engineer_principal(user_id=502)

        with pytest.raises(PermissionDeniedError) as exc_info:
            submit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=peer_principal,
                estimated_cost=Decimal("15000.00"),
                estimated_time="1 day",
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "complaint_not_assigned_to_caller"

    def test_submit_estimate_invalid_cost_raises_bad_request(self):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        principal = make_engineer_principal(user_id=501)

        for bad_cost in (Decimal("0.00"), Decimal("-500.00")):
            with pytest.raises(BadRequestError):
                submit_complaint_estimate(
                    complaint_id=complaint.pk,
                    principal=principal,
                    estimated_cost=bad_cost,
                    estimated_time="1 day",
                    materials_summary="Pipes",
                )

    def test_submit_estimate_missing_time_or_materials_raises_bad_request(self):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        principal = make_engineer_principal(user_id=501)

        with pytest.raises(BadRequestError) as exc_time:
            submit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=principal,
                estimated_cost=Decimal("5000.00"),
                estimated_time="  ",
                materials_summary="Pipes",
            )
        assert exc_time.value.code == "missing_estimated_time"

        with pytest.raises(BadRequestError) as exc_mat:
            submit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=principal,
                estimated_cost=Decimal("5000.00"),
                estimated_time="2 days",
                materials_summary="  ",
            )
        assert exc_mat.value.code == "missing_materials_summary"

    def test_transactional_rollback_on_failure(self):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        principal = make_engineer_principal(user_id=501)

        initial_status = complaint.status
        initial_estimates_count = Estimate.objects.count()
        initial_transitions_count = ComplaintTransition.objects.count()

        # Simulate unexpected failure during ComplaintTransition.objects.create
        with patch.object(ComplaintTransition.objects, "create", side_effect=RuntimeError("Database write error")):
            with pytest.raises(RuntimeError):
                submit_complaint_estimate(
                    complaint_id=complaint.pk,
                    principal=principal,
                    estimated_cost=Decimal("12000.00"),
                    estimated_time="1 day",
                    materials_summary="Wire coils",
                )

        complaint.refresh_from_db()
        assert complaint.status == initial_status
        assert Estimate.objects.count() == initial_estimates_count
        assert ComplaintTransition.objects.count() == initial_transitions_count


# -- 3. API Endpoint Tests -----------------------------------------------------

class TestAssessmentAndEstimateAPI:
    def test_assess_api_success_200(self, stub_iam):
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        payload = {"assessment_details": "Inspected laboratory ceiling, plaster damaged due to roof leak."}
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/assess/", payload, format="json")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == complaint.pk
        assert data["status"] == IWDState.ASSESSED.value
        assert data["assessment_details"] == payload["assessment_details"]
        assert data["assessed_at"] is not None

    def test_assess_api_unauthenticated_401(self):
        client = APIClient()
        resp = client.post("/api/v1/iwd/complaints/1/assess/", {"assessment_details": "Findings"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_assess_api_dormant_role_403(self, stub_iam):
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=501, active_role="faculty", roles=("faculty", "iwd_engineer"))
        client = make_client_for_session(stub_iam, session)

        resp = client.post(
            f"/api/v1/iwd/complaints/{complaint.pk}/assess/",
            {"assessment_details": "Findings"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_assess_api_peer_complaint_403(self, stub_iam):
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=502)
        client = make_client_for_session(stub_iam, session)

        resp = client.post(
            f"/api/v1/iwd/complaints/{complaint.pk}/assess/",
            {"assessment_details": "Findings"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_assess_api_invalid_state_409(self, stub_iam):
        complaint = Complaint.objects.create(
            user_id=101, category="civil", location="Lab", status=IWDState.SUBMITTED.value, assigned_engineer_id=501
        )
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        resp = client.post(
            f"/api/v1/iwd/complaints/{complaint.pk}/assess/",
            {"assessment_details": "Findings"},
            format="json",
        )
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_assess_api_blank_findings_400(self, stub_iam):
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        resp = client.post(
            f"/api/v1/iwd/complaints/{complaint.pk}/assess/",
            {"assessment_details": ""},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_estimate_api_success_201_low_cost(self, stub_iam):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "18500.00",
            "estimated_time": "3 days",
            "materials_summary": "Plaster cement, waterproof sealant, paint",
            "supporting_details": "Low-cost local purchase",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/estimates/", payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["id"] == complaint.pk
        assert data["status"] == IWDState.LOW_COST_REVIEW_PENDING.value
        assert len(data["estimates"]) == 1
        est = data["estimates"][0]
        assert est["estimated_cost"] == "18500.00"
        assert est["cost_band"] == CostBand.LOW.value

    def test_estimate_api_success_201_mid_range(self, stub_iam):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "45000.00",
            "estimated_time": "2 weeks",
            "materials_summary": "High-capacity water pump motor and wiring",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/estimates/", payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["status"] == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value
        assert data["estimates"][0]["cost_band"] == CostBand.MID.value

    def test_estimate_api_success_201_high_cost(self, stub_iam):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "320000.00",
            "estimated_time": "1 month",
            "materials_summary": "Substation transformer rewinding and cabling",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/estimates/", payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["status"] == IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value
        assert data["estimates"][0]["cost_band"] == CostBand.HIGH.value

    def test_estimate_api_unassessed_complaint_409(self, stub_iam):
        complaint = create_assigned_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "10000.00",
            "estimated_time": "1 day",
            "materials_summary": "Plumbing tape",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/estimates/", payload, format="json")
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_estimate_api_dormant_role_403(self, stub_iam):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=501, active_role="staff", roles=("staff", "iwd_engineer"))
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "10000.00",
            "estimated_time": "1 day",
            "materials_summary": "Plumbing tape",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/estimates/", payload, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_estimate_api_peer_complaint_403(self, stub_iam):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=502)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "10000.00",
            "estimated_time": "1 day",
            "materials_summary": "Plumbing tape",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/estimates/", payload, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_estimate_api_negative_cost_400(self, stub_iam):
        complaint = create_assessed_complaint(assigned_engineer_id=501)
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "-500.00",
            "estimated_time": "1 day",
            "materials_summary": "Tape",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/estimates/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_detail_complaint_contract_compatibility(self, stub_iam):
        """Detail endpoint returns all original fields plus new assessment/estimate fields."""
        complaint = create_assessed_complaint(assigned_engineer_id=501, complainant_id=101)
        Estimate.objects.create(
            complaint=complaint,
            engineer_id=501,
            cost_band=CostBand.LOW.value,
            estimated_cost=Decimal("12000.00"),
            estimated_time="2 days",
            materials_summary="Tiles and grout",
        )

        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        resp = client.get(f"/api/v1/iwd/complaints/{complaint.pk}/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        # Original fields
        for field in ("id", "user_id", "category", "location", "urgency", "remarks", "status", "assigned_engineer_id", "assigned_at", "created_at", "updated_at", "transitions"):
            assert field in data, f"Missing original field {field}"

        # New fields
        assert "assessment_details" in data
        assert "assessed_at" in data
        assert "estimates" in data
        assert len(data["estimates"]) == 1
        assert data["estimates"][0]["estimated_cost"] == "12000.00"

