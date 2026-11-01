"""Targeted tests for IWD estimate reviews and supervisory decisions (Increment 5).

Verifies:
- Low-cost approve and reject by IWD Admin (BW-IWD-02 Step 2 / UC-IWD-031 / BR-IWD-004)
- Mid-range committee feasibility recording (BW-IWD-03 Step 2 / UC-IWD-041 / BR-IWD-005)
- Department Head mid-range supervisory decisions: approve, reject, forward (BW-IWD-03 Step 3, BW-IWD-04 Step 1 / BR-IWD-006)
- Director decisions on forwarded mid-range and high-cost estimates (BW-IWD-04 Step 2, BW-IWD-05 Step 2 / BR-IWD-007)
- Mandatory non-blank rejection reasons (AFR-IWD-024, BR-IWD-009)
- Mandatory non-blank committee feasibility findings (BR-IWD-005, AFR-IWD-019)
- Active-role authorization isolation (rejecting dormant roles)
- Strict exclusion of Dean from estimate review authority (BR-IWD-018, AFR-IWD-060)
- Out-of-order and stale state transition rejections (HTTP 409 Conflict)
- Transactional consistency and rollback on failure
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
from modules.iwd.services.reviews import (
    execute_estimate_review,
    record_committee_review,
    review_dept_head_estimate,
    review_director_estimate,
    review_low_cost_estimate,
)

pytestmark = pytest.mark.django_db


# -- Helpers -------------------------------------------------------------------

def make_client_for_session(stub_iam, session):
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-valid-token")
    return client


def create_complaint_in_state(status_val: str, assigned_engineer_id: int = 501, cost: Decimal = Decimal("10000.00")) -> tuple[Complaint, Estimate]:
    complaint = Complaint.objects.create(
        user_id=101,
        category="civil",
        location="Hostel 1, Room 101",
        urgency="medium",
        remarks="Test complaint",
        status=status_val,
        assigned_engineer_id=assigned_engineer_id,
    )
    estimate = Estimate.objects.create(
        complaint=complaint,
        engineer_id=assigned_engineer_id,
        cost_band=CostBand.LOW.value if cost < 25000 else (CostBand.MID.value if cost <= 250000 else CostBand.HIGH.value),
        estimated_cost=cost,
        estimated_time="2 days",
        materials_summary="Plumbing fixtures",
    )
    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=IWDState.ASSESSED.value,
        to_status=status_val,
        actor_user_id=assigned_engineer_id,
        actor_label="Engineer",
        reason=f"Estimate submitted: ₹{cost}",
    )
    return complaint, estimate


# -- 1. Low-Cost Review Service Tests ------------------------------------------

class TestLowCostReviewServices:
    def test_low_cost_approve_success(self):
        complaint, _ = create_complaint_in_state(IWDState.LOW_COST_REVIEW_PENDING.value, cost=Decimal("15000.00"))
        admin_principal = make_session(
            user_id=801,
            permissions=("iwd.estimate.review_low", "iwd.complaint.view"),
            modules=("iwd",),
            active_role="iwd_admin",
            roles=("iwd_admin",),
        )

        updated = review_low_cost_estimate(
            complaint_id=complaint.pk,
            principal=admin_principal,
            action="approve",
            remarks="Scope verified, materials approved.",
        )

        assert updated.status == IWDState.ESTIMATE_APPROVED.value
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.from_status == IWDState.LOW_COST_REVIEW_PENDING.value
        assert trans.to_status == IWDState.ESTIMATE_APPROVED.value
        assert trans.actor_label == "IWD Admin"
        assert trans.actor_user_id == 801
        assert "Scope verified" in trans.reason

    def test_low_cost_reject_success_with_reason(self):
        complaint, _ = create_complaint_in_state(IWDState.LOW_COST_REVIEW_PENDING.value, cost=Decimal("15000.00"))
        admin_principal = make_session(
            user_id=801,
            permissions=("iwd.estimate.review_low",),
            modules=("iwd",),
            active_role="iwd_admin",
            roles=("iwd_admin",),
        )

        updated = review_low_cost_estimate(
            complaint_id=complaint.pk,
            principal=admin_principal,
            action="reject",
            remarks="Cost of pipe fittings exceeds local schedule of rates.",
        )

        assert updated.status == IWDState.REJECTED_LOW.value
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.to_status == IWDState.REJECTED_LOW.value
        assert "exceeds local schedule" in trans.reason

    def test_low_cost_reject_missing_reason_rejected(self):
        complaint, _ = create_complaint_in_state(IWDState.LOW_COST_REVIEW_PENDING.value)
        admin_principal = make_session(
            user_id=801,
            permissions=("iwd.estimate.review_low",),
            modules=("iwd",),
            active_role="iwd_admin",
            roles=("iwd_admin",),
        )

        with pytest.raises(BadRequestError) as exc_info:
            review_low_cost_estimate(
                complaint_id=complaint.pk,
                principal=admin_principal,
                action="reject",
                remarks="   ",
            )
        assert exc_info.value.code == "missing_rejection_reason"

    def test_low_cost_review_dormant_role_denied(self):
        complaint, _ = create_complaint_in_state(IWDState.LOW_COST_REVIEW_PENDING.value)
        dormant_principal = make_session(
            user_id=801,
            permissions=("iwd.estimate.review_low",),
            modules=("iwd",),
            active_role="faculty",
            roles=("faculty", "iwd_admin"),
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            review_low_cost_estimate(
                complaint_id=complaint.pk,
                principal=dormant_principal,
                action="approve",
            )
        assert exc_info.value.code == "active_role_required"

    def test_low_cost_review_wrong_state_conflict(self):
        complaint, _ = create_complaint_in_state(IWDState.SUBMITTED.value)
        admin_principal = make_session(
            user_id=801,
            permissions=("iwd.estimate.review_low",),
            modules=("iwd",),
            active_role="iwd_admin",
            roles=("iwd_admin",),
        )

        with pytest.raises(ConflictError) as exc_info:
            review_low_cost_estimate(
                complaint_id=complaint.pk,
                principal=admin_principal,
                action="approve",
            )
        assert exc_info.value.code == "invalid_state_transition"


# -- 2. Mid-Range Committee & Department Head Services -------------------------

class TestMidRangeReviewServices:
    def test_committee_review_success(self):
        complaint, _ = create_complaint_in_state(IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value, cost=Decimal("75000.00"))
        dept_head_principal = make_session(
            user_id=901,
            permissions=("iwd.estimate.review_committee",),
            modules=("iwd",),
            active_role="Department Head",
            roles=("Department Head",),
        )

        updated = record_committee_review(
            complaint_id=complaint.pk,
            principal=dept_head_principal,
            remarks="Committee inspected electrical panel: repair is essential for safety.",
        )

        assert updated.status == IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.from_status == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value
        assert trans.to_status == IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value
        assert trans.actor_label == "Review Committee"
        assert "essential for safety" in trans.reason

    def test_committee_review_missing_findings_rejected(self):
        complaint, _ = create_complaint_in_state(IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value)
        dept_head_principal = make_session(
            user_id=901,
            permissions=("iwd.estimate.review_committee",),
            modules=("iwd",),
            active_role="Department Head",
            roles=("Department Head",),
        )

        with pytest.raises(BadRequestError) as exc_info:
            record_committee_review(
                complaint_id=complaint.pk,
                principal=dept_head_principal,
                remarks="",
            )
        assert exc_info.value.code == "missing_committee_findings"

    def test_dept_head_approve_success(self):
        complaint, _ = create_complaint_in_state(IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value, cost=Decimal("75000.00"))
        dept_head_principal = make_session(
            user_id=901,
            permissions=("iwd.estimate.review_mid",),
            modules=("iwd",),
            active_role="Department Head",
            roles=("Department Head",),
        )

        updated = review_dept_head_estimate(
            complaint_id=complaint.pk,
            principal=dept_head_principal,
            action="approve",
            remarks="Approved within departmental budget limit.",
        )

        assert updated.status == IWDState.ESTIMATE_APPROVED.value
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.to_status == IWDState.ESTIMATE_APPROVED.value
        assert trans.actor_label == "Department Head"
        assert "departmental budget" in trans.reason

    def test_dept_head_reject_success_with_reason(self):
        complaint, _ = create_complaint_in_state(IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value, cost=Decimal("75000.00"))
        dept_head_principal = make_session(
            user_id=901,
            permissions=("iwd.estimate.review_mid",),
            modules=("iwd",),
            active_role="Department Head",
            roles=("Department Head",),
        )

        updated = review_dept_head_estimate(
            complaint_id=complaint.pk,
            principal=dept_head_principal,
            action="reject",
            remarks="Material specifications redundant; use standard grade wiring.",
        )

        assert updated.status == IWDState.REJECTED_MID.value
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.to_status == IWDState.REJECTED_MID.value
        assert "redundant" in trans.reason

    def test_dept_head_forward_to_director_success(self):
        complaint, _ = create_complaint_in_state(IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value, cost=Decimal("180000.00"))
        dept_head_principal = make_session(
            user_id=901,
            permissions=("iwd.estimate.review_mid",),
            modules=("iwd",),
            active_role="Department Head",
            roles=("Department Head",),
        )

        updated = review_dept_head_estimate(
            complaint_id=complaint.pk,
            principal=dept_head_principal,
            action="forward_to_director",
            remarks="Forwarding to Director: exceeds departmental discretionary threshold.",
        )

        assert updated.status == IWDState.DIRECTOR_REVIEW_PENDING_MID.value
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.to_status == IWDState.DIRECTOR_REVIEW_PENDING_MID.value
        assert "Forwarding to Director" in trans.reason

    def test_dept_head_decision_before_committee_review_denied(self):
        """Cannot perform supervisory decision while still awaiting committee feasibility."""
        complaint, _ = create_complaint_in_state(IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value)
        dept_head_principal = make_session(
            user_id=901,
            permissions=("iwd.estimate.review_mid",),
            modules=("iwd",),
            active_role="Department Head",
            roles=("Department Head",),
        )

        with pytest.raises(ConflictError):
            review_dept_head_estimate(
                complaint_id=complaint.pk,
                principal=dept_head_principal,
                action="approve",
            )


# -- 3. Director Review Services -----------------------------------------------

class TestDirectorReviewServices:
    def test_director_approve_forwarded_mid_range(self):
        complaint, _ = create_complaint_in_state(IWDState.DIRECTOR_REVIEW_PENDING_MID.value, cost=Decimal("180000.00"))
        director_principal = make_session(
            user_id=999,
            permissions=("iwd.estimate.review_director",),
            modules=("iwd",),
            active_role="Director",
            roles=("Director",),
        )

        updated = review_director_estimate(
            complaint_id=complaint.pk,
            principal=director_principal,
            action="approve",
            remarks="Director approved forwarded mid-range expenditure.",
        )

        assert updated.status == IWDState.ESTIMATE_APPROVED.value
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.to_status == IWDState.ESTIMATE_APPROVED.value
        assert trans.actor_label == "Director"

    def test_director_reject_forwarded_mid_range(self):
        complaint, _ = create_complaint_in_state(IWDState.DIRECTOR_REVIEW_PENDING_MID.value, cost=Decimal("180000.00"))
        director_principal = make_session(
            user_id=999,
            permissions=("iwd.estimate.review_director",),
            modules=("iwd",),
            active_role="Director",
            roles=("Director",),
        )

        updated = review_director_estimate(
            complaint_id=complaint.pk,
            principal=director_principal,
            action="reject",
            remarks="Funds not available under campus development head.",
        )

        assert updated.status == IWDState.REJECTED_DIRECTOR.value
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.to_status == IWDState.REJECTED_DIRECTOR.value
        assert "Funds not available" in trans.reason

    def test_director_approve_high_cost_bidding(self):
        complaint, _ = create_complaint_in_state(IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value, cost=Decimal("450000.00"))
        director_principal = make_session(
            user_id=999,
            permissions=("iwd.estimate.review_director",),
            modules=("iwd",),
            active_role="Director",
            roles=("Director",),
        )

        updated = review_director_estimate(
            complaint_id=complaint.pk,
            principal=director_principal,
            action="approve_bidding",
            remarks="External tender approved per procurement rules.",
        )

        assert updated.status == IWDState.BIDDING_AUTHORIZED.value
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.to_status == IWDState.BIDDING_AUTHORIZED.value
        assert trans.actor_label == "Director"

    def test_director_reject_high_cost_bidding(self):
        complaint, _ = create_complaint_in_state(IWDState.DIRECTOR_REVIEW_PENDING_HIGH.value, cost=Decimal("450000.00"))
        director_principal = make_session(
            user_id=999,
            permissions=("iwd.estimate.review_director",),
            modules=("iwd",),
            active_role="Director",
            roles=("Director",),
        )

        updated = review_director_estimate(
            complaint_id=complaint.pk,
            principal=director_principal,
            action="reject_bidding",
            remarks="Major renovation deferred to next fiscal year.",
        )

        assert updated.status == IWDState.REJECTED_DIRECTOR.value
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.to_status == IWDState.REJECTED_DIRECTOR.value
        assert "deferred to next fiscal year" in trans.reason


# -- 4. Authority, Dean & Concurrency Tests ------------------------------------

class TestReviewAuthorizationAndConcurrency:
    def test_dean_denied_all_estimate_reviews(self):
        """Dean has zero estimate review permissions and must be denied with 403."""
        dean_principal = make_session(
            user_id=950,
            permissions=("iwd.complaint.view", "iwd.complaint.create"),
            modules=("iwd",),
            active_role="Dean",
            roles=("Dean",),
        )
        complaint, _ = create_complaint_in_state(IWDState.LOW_COST_REVIEW_PENDING.value)

        with pytest.raises(PermissionDeniedError):
            review_low_cost_estimate(
                complaint_id=complaint.pk,
                principal=dean_principal,
                action="approve",
            )

        with pytest.raises(PermissionDeniedError):
            record_committee_review(
                complaint_id=complaint.pk,
                principal=dean_principal,
                remarks="Findings",
            )

        with pytest.raises(PermissionDeniedError):
            review_dept_head_estimate(
                complaint_id=complaint.pk,
                principal=dean_principal,
                action="approve",
            )

        with pytest.raises(PermissionDeniedError):
            review_director_estimate(
                complaint_id=complaint.pk,
                principal=dean_principal,
                action="approve",
            )

    def test_transactional_rollback_on_review_failure(self):
        complaint, _ = create_complaint_in_state(IWDState.LOW_COST_REVIEW_PENDING.value)
        admin_principal = make_session(
            user_id=801,
            permissions=("iwd.estimate.review_low",),
            modules=("iwd",),
            active_role="iwd_admin",
            roles=("iwd_admin",),
        )

        initial_status = complaint.status
        initial_trans_count = ComplaintTransition.objects.count()

        with patch.object(ComplaintTransition.objects, "create", side_effect=RuntimeError("Audit write failed")):
            with pytest.raises(RuntimeError):
                review_low_cost_estimate(
                    complaint_id=complaint.pk,
                    principal=admin_principal,
                    action="approve",
                )

        complaint.refresh_from_db()
        assert complaint.status == initial_status
        assert ComplaintTransition.objects.count() == initial_trans_count


# -- 5. API Endpoint Tests -----------------------------------------------------

class TestReviewAPI:
    def test_review_api_low_cost_approve_200(self, stub_iam):
        complaint, _ = create_complaint_in_state(IWDState.LOW_COST_REVIEW_PENDING.value)
        session = make_session(
            user_id=801,
            permissions=("iwd.estimate.review_low", "iwd.complaint.view"),
            modules=("iwd",),
            active_role="iwd_admin",
            roles=("iwd_admin",),
        )
        client = make_client_for_session(stub_iam, session)

        payload = {"action": "approve", "remarks": "Approved by IWD Admin"}
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/review-estimate/", payload, format="json")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == complaint.pk
        assert data["status"] == IWDState.ESTIMATE_APPROVED.value

    def test_review_api_reject_missing_remarks_400(self, stub_iam):
        complaint, _ = create_complaint_in_state(IWDState.LOW_COST_REVIEW_PENDING.value)
        session = make_session(
            user_id=801,
            permissions=("iwd.estimate.review_low", "iwd.complaint.view"),
            modules=("iwd",),
            active_role="iwd_admin",
            roles=("iwd_admin",),
        )
        client = make_client_for_session(stub_iam, session)

        payload = {"action": "reject", "remarks": ""}
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/review-estimate/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_review_api_stale_state_conflict_409(self, stub_iam):
        # Complaint already in Estimate Approved cannot be reviewed again
        complaint, _ = create_complaint_in_state(IWDState.ESTIMATE_APPROVED.value)
        session = make_session(
            user_id=801,
            permissions=("iwd.estimate.review_low", "iwd.complaint.view"),
            modules=("iwd",),
            active_role="iwd_admin",
            roles=("iwd_admin",),
        )
        client = make_client_for_session(stub_iam, session)

        payload = {"action": "approve"}
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/review-estimate/", payload, format="json")
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_review_api_dormant_role_denied_403(self, stub_iam):
        complaint, _ = create_complaint_in_state(IWDState.LOW_COST_REVIEW_PENDING.value)
        session = make_session(
            user_id=801,
            permissions=("iwd.estimate.review_low",),
            modules=("iwd",),
            active_role="faculty",
            roles=("faculty", "iwd_admin"),
        )
        client = make_client_for_session(stub_iam, session)

        payload = {"action": "approve"}
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/review-estimate/", payload, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

