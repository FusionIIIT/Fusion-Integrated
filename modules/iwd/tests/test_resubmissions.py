"""Targeted tests for IWD rejected estimate modification and resubmission (Increment 6).

Verifies:
- Dynamic cost-band routing from all three rejected states:
    • REJECTED_LOW -> Low-Cost, Mid-Range, or High-Cost
    • REJECTED_MID -> Low-Cost, Mid-Range, or High-Cost
    • REJECTED_DIRECTOR -> Low-Cost, Mid-Range, or High-Cost
    • Exact boundary thresholds (₹24,999.99, ₹25,000.00, ₹250,000.00, ₹250,000.01)
- Estimate versioning (historical rejected estimates preserved, new estimates appended)
- Retention of rejection transitions, reasons, and original assessment findings
- Multiple rejection/resubmission cycles
- Active-role authorization isolation (rejecting dormant iwd_engineer roles)
- Assignment ownership isolation (peer engineers denied)
- Strict exclusion of Dean and non-engineers (HTTP 403)
- Rejection of non-rejected states (HTTP 409 Conflict)
- Sequential duplicate prevention (second call fails with HTTP 409 Conflict)
- Input validation (zero/negative cost, missing fields)
- Transactional atomicity and rollback on failure
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
from modules.iwd.services.estimates import resubmit_complaint_estimate

pytestmark = pytest.mark.django_db


# -- Helpers -------------------------------------------------------------------

def make_client_for_session(stub_iam, session):
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-valid-token")
    return client


def make_engineer_principal(
    user_id: int = 501,
    active_role: str = "iwd_engineer",
    roles: tuple[str, ...] = ("iwd_engineer",),
    permissions: tuple[str, ...] = ("iwd.complaint.assess", "iwd.complaint.view"),
):
    return make_session(
        user_id=user_id,
        permissions=permissions,
        modules=("iwd",),
        active_role=active_role,
        roles=roles,
    )


def create_rejected_complaint(
    rejected_state: str,
    assigned_engineer_id: int = 501,
    complainant_id: int = 101,
    original_cost: Decimal = Decimal("20000.00"),
    rejection_reason: str = "Original estimate cost too high",
) -> tuple[Complaint, Estimate]:
    complaint = Complaint.objects.create(
        user_id=complainant_id,
        category="civil",
        location="Hostel 2, Room 305",
        urgency="medium",
        remarks="Original complaint issue",
        status=rejected_state,
        assigned_engineer_id=assigned_engineer_id,
        assessment_details="Cracked lintel and fallen plaster",
    )
    estimate = Estimate.objects.create(
        complaint=complaint,
        engineer_id=assigned_engineer_id,
        cost_band=CostBand.LOW.value if original_cost < 25000 else (CostBand.MID.value if original_cost <= 250000 else CostBand.HIGH.value),
        estimated_cost=original_cost,
        estimated_time="3 days",
        materials_summary="Plaster, cement, sand",
        supporting_details="Initial quote from local vendor",
    )
    # Log assessment transition
    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=IWDState.ASSIGNED.value,
        to_status=IWDState.ASSESSED.value,
        actor_user_id=assigned_engineer_id,
        actor_label="Engineer",
        reason="Technical assessment recorded",
    )
    # Log rejection transition
    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status="Review Pending",
        to_status=rejected_state,
        actor_user_id=801,
        actor_label="IWD Admin",
        reason=rejection_reason,
    )
    return complaint, estimate


# -- 1. Dynamic Routing Service Tests ------------------------------------------

class TestResubmissionDynamicRouting:
    @pytest.mark.parametrize("initial_state", [
        IWDState.REJECTED_LOW.value,
        IWDState.REJECTED_MID.value,
        IWDState.REJECTED_DIRECTOR.value,
    ])
    def test_resubmit_routes_to_low_cost(self, initial_state):
        """Resubmission with cost < ₹25,000 routes to Low-Cost Review Pending regardless of prior rejected state."""
        complaint, _ = create_rejected_complaint(initial_state)
        principal = make_engineer_principal(user_id=501)

        updated, est = resubmit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("15000.00"),
            estimated_time="2 days",
            materials_summary="Revised low-cost mortar mix",
            supporting_details="Optimized scope",
        )

        assert updated.status == IWDState.LOW_COST_REVIEW_PENDING.value
        assert est.cost_band == CostBand.LOW.value
        assert est.estimated_cost == Decimal("15000.00")

    @pytest.mark.parametrize("initial_state", [
        IWDState.REJECTED_LOW.value,
        IWDState.REJECTED_MID.value,
        IWDState.REJECTED_DIRECTOR.value,
    ])
    def test_resubmit_routes_to_mid_range(self, initial_state):
        """Resubmission with ₹25,000 <= cost <= ₹250,000 routes to Mid-Range Committee Review Pending."""
        complaint, _ = create_rejected_complaint(initial_state)
        principal = make_engineer_principal(user_id=501)

        updated, est = resubmit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("85000.00"),
            estimated_time="2 weeks",
            materials_summary="Structural steel reinforcement and formwork",
        )

        assert updated.status == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value
        assert est.cost_band == CostBand.MID.value
        assert est.estimated_cost == Decimal("85000.00")

    @pytest.mark.parametrize("initial_state", [
        IWDState.REJECTED_LOW.value,
        IWDState.REJECTED_MID.value,
        IWDState.REJECTED_DIRECTOR.value,
    ])
    def test_resubmit_routes_to_high_cost(self, initial_state):
        """Resubmission with cost > ₹250,000 routes to Director Review Pending (High-Cost)."""
        complaint, _ = create_rejected_complaint(initial_state)
        principal = make_engineer_principal(user_id=501)

        updated, est = resubmit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("350000.00"),
            estimated_time="2 months",
            materials_summary="Complete lintel replacement across entire facade",
        )

        assert updated.status == IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value
        assert est.cost_band == CostBand.HIGH.value
        assert est.estimated_cost == Decimal("350000.00")

    def test_exact_boundary_thresholds_on_resubmission(self):
        """Verify exact boundary routing on resubmission: 24,999.99, 25,000.00, 250,000.00, 250,000.01."""
        principal = make_engineer_principal(user_id=501)

        # Boundary 1: ₹24,999.99 -> Low-Cost
        c1, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        u1, _ = resubmit_complaint_estimate(
            complaint_id=c1.pk,
            principal=principal,
            estimated_cost=Decimal("24999.99"),
            estimated_time="2 days",
            materials_summary="Materials",
        )
        assert u1.status == IWDState.LOW_COST_REVIEW_PENDING.value

        # Boundary 2: ₹25,000.00 -> Mid-Range
        c2, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        u2, _ = resubmit_complaint_estimate(
            complaint_id=c2.pk,
            principal=principal,
            estimated_cost=Decimal("25000.00"),
            estimated_time="2 days",
            materials_summary="Materials",
        )
        assert u2.status == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value

        # Boundary 3: ₹250,000.00 -> Mid-Range
        c3, _ = create_rejected_complaint(IWDState.REJECTED_DIRECTOR.value)
        u3, _ = resubmit_complaint_estimate(
            complaint_id=c3.pk,
            principal=principal,
            estimated_cost=Decimal("250000.00"),
            estimated_time="1 month",
            materials_summary="Materials",
        )
        assert u3.status == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value

        # Boundary 4: ₹250,000.01 -> High-Cost
        c4, _ = create_rejected_complaint(IWDState.REJECTED_MID.value)
        u4, _ = resubmit_complaint_estimate(
            complaint_id=c4.pk,
            principal=principal,
            estimated_cost=Decimal("250000.01"),
            estimated_time="2 months",
            materials_summary="Materials",
        )
        assert u4.status == IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value


# -- 2. Version History and Audit Trail Tests -----------------------------------

class TestVersionHistoryAndAudit:
    def test_versioning_preserves_old_estimate_and_appends_new(self):
        """Original rejected estimate remains intact while a new Estimate entity is created."""
        complaint, orig_est = create_rejected_complaint(
            IWDState.REJECTED_LOW.value,
            original_cost=Decimal("22000.00"),
            rejection_reason="Excessive contractor labor cost",
        )
        principal = make_engineer_principal(user_id=501)

        updated_complaint, new_est = resubmit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("17000.00"),
            estimated_time="2 days",
            materials_summary="Revised labor rate with in-house masonry",
            supporting_details="Negotiated rates",
        )

        # 1. Total estimates under complaint is now 2
        assert complaint.estimates.count() == 2

        # 2. Original estimate is completely unchanged
        orig_est.refresh_from_db()
        assert orig_est.estimated_cost == Decimal("22000.00")
        assert orig_est.materials_summary == "Plaster, cement, sand"

        # 3. New estimate has new values
        assert new_est.pk != orig_est.pk
        assert new_est.estimated_cost == Decimal("17000.00")
        assert new_est.materials_summary == "Revised labor rate with in-house masonry"

        # 4. Assessment details on complaint remain intact
        assert updated_complaint.assessment_details == "Cracked lintel and fallen plaster"

        # 5. Audit transition records resubmission
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.from_status == IWDState.REJECTED_LOW.value
        assert trans.to_status == IWDState.LOW_COST_REVIEW_PENDING.value
        assert trans.actor_user_id == 501
        assert trans.actor_label == "Engineer"
        assert "17000.00" in trans.reason

    def test_multiple_rejection_resubmission_cycles(self):
        """A complaint can undergo multiple cycles of rejection and resubmission, preserving every estimate."""
        complaint, est1 = create_rejected_complaint(IWDState.REJECTED_LOW.value, original_cost=Decimal("20000.00"))
        principal = make_engineer_principal(user_id=501)

        # First resubmission -> Low-Cost Review Pending
        _, est2 = resubmit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("18000.00"),
            estimated_time="2 days",
            materials_summary="Revision 1",
        )
        assert complaint.estimates.count() == 2

        # Admin rejects again -> Rejected - Low-Cost
        complaint.status = IWDState.REJECTED_LOW.value
        complaint.save(update_fields=["status"])
        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=IWDState.LOW_COST_REVIEW_PENDING.value,
            to_status=IWDState.REJECTED_LOW.value,
            actor_user_id=801,
            actor_label="IWD Admin",
            reason="Still too expensive",
        )

        # Second resubmission -> Low-Cost Review Pending
        _, est3 = resubmit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("14000.00"),
            estimated_time="1 day",
            materials_summary="Revision 2",
        )
        assert complaint.estimates.count() == 3

        # All 3 estimates exist and retain distinct amounts
        all_costs = list(complaint.estimates.order_by("created_at").values_list("estimated_cost", flat=True))
        assert all_costs == [Decimal("20000.00"), Decimal("18000.00"), Decimal("14000.00")]


# -- 3. Authorization and State Guard Tests -------------------------------------

class TestResubmissionAuthorizationAndGuards:
    def test_dormant_role_denied_resubmission(self):
        """User with iwd_engineer in roles but active_role='faculty' is denied (HTTP 403)."""
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        dormant_principal = make_engineer_principal(
            user_id=501,
            active_role="faculty",
            roles=("faculty", "iwd_engineer"),
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            resubmit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=dormant_principal,
                estimated_cost=Decimal("15000.00"),
                estimated_time="1 day",
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "active_role_required"

    def test_peer_engineer_denied_resubmission(self):
        """Engineer 502 cannot resubmit an estimate for complaint assigned to Engineer 501."""
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value, assigned_engineer_id=501)
        peer_principal = make_engineer_principal(user_id=502)

        with pytest.raises(PermissionDeniedError) as exc_info:
            resubmit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=peer_principal,
                estimated_cost=Decimal("15000.00"),
                estimated_time="1 day",
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "complaint_not_assigned_to_caller"

    def test_dean_denied_resubmission(self):
        """Dean role has no estimate permissions and is denied."""
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        dean_principal = make_session(
            user_id=950,
            permissions=("iwd.complaint.view", "iwd.complaint.create"),
            modules=("iwd",),
            active_role="Dean",
            roles=("Dean",),
        )

        with pytest.raises(PermissionDeniedError):
            resubmit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=dean_principal,
                estimated_cost=Decimal("15000.00"),
                estimated_time="1 day",
                materials_summary="Pipes",
            )

    @pytest.mark.parametrize("non_rejected_state", [
        IWDState.SUBMITTED.value,
        IWDState.ASSIGNED.value,
        IWDState.ASSESSED.value,
        IWDState.LOW_COST_REVIEW_PENDING.value,
        IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value,
        IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value,
        IWDState.DIRECTOR_REVIEW_PENDING_MID.value,
        IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value,
        IWDState.ESTIMATE_APPROVED.value,
        IWDState.BIDDING_AUTHORIZED.value,
    ])
    def test_resubmission_on_non_rejected_states_raises_conflict(self, non_rejected_state):
        """Attempting to resubmit from any non-rejected state is rejected with ConflictError (HTTP 409)."""
        complaint = Complaint.objects.create(
            user_id=101,
            category="civil",
            location="Room 101",
            status=non_rejected_state,
            assigned_engineer_id=501,
        )
        principal = make_engineer_principal(user_id=501)

        with pytest.raises(ConflictError) as exc_info:
            resubmit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=principal,
                estimated_cost=Decimal("15000.00"),
                estimated_time="1 day",
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "not_in_rejected_state"

    def test_sequential_requests_prevent_duplicate_resubmission(self):
        """After the first resubmission succeeds, the complaint is no longer in a rejected state; second call raises ConflictError."""
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        principal = make_engineer_principal(user_id=501)

        # Call 1 succeeds
        resubmit_complaint_estimate(
            complaint_id=complaint.pk,
            principal=principal,
            estimated_cost=Decimal("15000.00"),
            estimated_time="1 day",
            materials_summary="Pipes",
        )

        # Call 2 immediately fails with ConflictError (HTTP 409)
        with pytest.raises(ConflictError) as exc_info:
            resubmit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=principal,
                estimated_cost=Decimal("16000.00"),
                estimated_time="1 day",
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "not_in_rejected_state"


# -- 4. Input Validation and Rollback Tests -------------------------------------

class TestResubmissionValidationAndRollback:
    def test_invalid_cost_raises_bad_request(self):
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        principal = make_engineer_principal(user_id=501)

        for bad_cost in (Decimal("0.00"), Decimal("-100.00"), "not-a-number"):
            with pytest.raises(BadRequestError):
                resubmit_complaint_estimate(
                    complaint_id=complaint.pk,
                    principal=principal,
                    estimated_cost=bad_cost,
                    estimated_time="1 day",
                    materials_summary="Pipes",
                )

    def test_blank_time_or_materials_raises_bad_request(self):
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        principal = make_engineer_principal(user_id=501)

        with pytest.raises(BadRequestError) as exc_time:
            resubmit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=principal,
                estimated_cost=Decimal("10000.00"),
                estimated_time="   ",
                materials_summary="Pipes",
            )
        assert exc_time.value.code == "missing_estimated_time"

        with pytest.raises(BadRequestError) as exc_mat:
            resubmit_complaint_estimate(
                complaint_id=complaint.pk,
                principal=principal,
                estimated_cost=Decimal("10000.00"),
                estimated_time="2 days",
                materials_summary="   ",
            )
        assert exc_mat.value.code == "missing_materials_summary"

    def test_transactional_rollback_on_failure(self):
        """If writing the audit transition fails, new Estimate creation and complaint status update roll back."""
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        principal = make_engineer_principal(user_id=501)

        initial_status = complaint.status
        initial_est_count = complaint.estimates.count()
        initial_trans_count = ComplaintTransition.objects.count()

        with patch.object(ComplaintTransition.objects, "create", side_effect=RuntimeError("DB failure")):
            with pytest.raises(RuntimeError):
                resubmit_complaint_estimate(
                    complaint_id=complaint.pk,
                    principal=principal,
                    estimated_cost=Decimal("12000.00"),
                    estimated_time="1 day",
                    materials_summary="Pipes",
                )

        complaint.refresh_from_db()
        assert complaint.status == initial_status
        assert complaint.estimates.count() == initial_est_count
        assert ComplaintTransition.objects.count() == initial_trans_count


# -- 5. API Endpoint Tests -----------------------------------------------------

class TestResubmissionAPI:
    def test_resubmit_api_success_201(self, stub_iam):
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "16500.00",
            "estimated_time": "2 days",
            "materials_summary": "Revised mortar mix and sealants",
            "supporting_details": "Vendor discount applied",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/resubmit-estimate/", payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["id"] == complaint.pk
        assert data["status"] == IWDState.LOW_COST_REVIEW_PENDING.value
        assert len(data["estimates"]) == 2
        costs = {e["estimated_cost"]: e for e in data["estimates"]}
        assert "20000.00" in costs
        assert "16500.00" in costs
        assert costs["16500.00"]["cost_band"] == CostBand.LOW.value

    def test_resubmit_api_unauthenticated_401(self):
        client = APIClient()
        resp = client.post("/api/v1/iwd/complaints/1/resubmit-estimate/", {"estimated_cost": "10000.00"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_resubmit_api_dormant_role_403(self, stub_iam):
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        session = make_engineer_principal(user_id=501, active_role="faculty", roles=("faculty", "iwd_engineer"))
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "16500.00",
            "estimated_time": "2 days",
            "materials_summary": "Revised mortar mix",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/resubmit-estimate/", payload, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_resubmit_api_peer_engineer_403(self, stub_iam):
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value, assigned_engineer_id=501)
        session = make_engineer_principal(user_id=502)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "16500.00",
            "estimated_time": "2 days",
            "materials_summary": "Revised mortar mix",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/resubmit-estimate/", payload, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_resubmit_api_non_rejected_state_conflict_409(self, stub_iam):
        complaint = Complaint.objects.create(
            user_id=101, category="civil", location="Room A", status=IWDState.ASSESSED.value, assigned_engineer_id=501
        )
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "16500.00",
            "estimated_time": "2 days",
            "materials_summary": "Revised mortar mix",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/resubmit-estimate/", payload, format="json")
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_resubmit_api_invalid_cost_400(self, stub_iam):
        complaint, _ = create_rejected_complaint(IWDState.REJECTED_LOW.value)
        session = make_engineer_principal(user_id=501)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "estimated_cost": "-500.00",
            "estimated_time": "2 days",
            "materials_summary": "Revised mortar mix",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/resubmit-estimate/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

