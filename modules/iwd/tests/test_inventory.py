"""Targeted tests for IWD inventory verification, stock shortage procurement, and material issuance (Increment 7).

Verifies:
- BW-IWD-06: Direct stock issuance (ESTIMATE_APPROVED -> MATERIALS_ISSUED)
- BW-IWD-07: Low-cost shortage procurement lifecycle:
    • ESTIMATE_APPROVED -> PROCUREMENT_NEEDED_LOW -> MATERIALS_AVAILABLE -> MATERIALS_ISSUED
- BW-IWD-08: Mid-range shortage procurement lifecycle:
    • ESTIMATE_APPROVED -> PROCUREMENT_NEEDED_MID -> MATERIALS_AVAILABLE -> MATERIALS_ISSUED
- Exact cost-band shortage boundary thresholds:
    • ₹24,999.99 -> PROCUREMENT_NEEDED_LOW
    • ₹25,000.00 -> PROCUREMENT_NEEDED_MID
    • ₹250,000.00 -> PROCUREMENT_NEEDED_MID
    • ₹250,000.01 -> High-cost bidding isolation (HTTP 409 Conflict)
- High-cost BIDDING_AUTHORIZED rejection from inventory actions (HTTP 409 Conflict)
- Active-role authorization isolation (rejecting dormant iwd_admin roles)
- Role separation (denying Engineer, Department Head, and Dean)
- State guards, duplicate issuance prevention, and invalid-state transitions (HTTP 409 Conflict)
- Empty materials summary validation (HTTP 400 Bad Request)
- Transactional atomicity and rollback on audit failure
- Output serialization of MaterialIssue records in ComplaintDetailSerializer
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
from modules.iwd.models import Complaint, ComplaintTransition, Estimate, MaterialIssue
from modules.iwd.services.inventory import (
    complete_procurement,
    execute_inventory_action,
    issue_procured_material,
    issue_stock_material,
    record_stock_shortage,
)

pytestmark = pytest.mark.django_db


# -- Helpers -------------------------------------------------------------------

def make_client_for_session(stub_iam, session):
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-valid-token")
    return client


def make_admin_principal(
    user_id: int = 801,
    active_role: str = "iwd_admin",
    roles: tuple[str, ...] = ("iwd_admin",),
    permissions: tuple[str, ...] = ("iwd.inventory.manage", "iwd.complaint.view"),
):
    return make_session(
        user_id=user_id,
        permissions=permissions,
        modules=("iwd",),
        active_role=active_role,
        roles=roles,
    )


def create_approved_complaint(
    estimated_cost: Decimal = Decimal("15000.00"),
    status_value: str = IWDState.ESTIMATE_APPROVED.value,
    assigned_engineer_id: int = 501,
    complainant_id: int = 101,
) -> tuple[Complaint, Estimate]:
    complaint = Complaint.objects.create(
        user_id=complainant_id,
        category="civil",
        location="Hostel 3, Room 104",
        urgency="medium",
        remarks="Damaged water pipe and seepage",
        status=status_value,
        assigned_engineer_id=assigned_engineer_id,
        assessment_details="Cracked PVC joint and wall seepage",
    )
    cost_band = (
        CostBand.LOW.value
        if estimated_cost < Decimal("25000.00")
        else (CostBand.MID.value if estimated_cost <= Decimal("250000.00") else CostBand.HIGH.value)
    )
    estimate = Estimate.objects.create(
        complaint=complaint,
        engineer_id=assigned_engineer_id,
        cost_band=cost_band,
        estimated_cost=estimated_cost,
        estimated_time="3 days",
        materials_summary="PVC pipes, solvent cement, joint couplers",
        supporting_details="Standard schedule of rates",
    )
    ComplaintTransition.objects.create(
        complaint=complaint,
        from_status=IWDState.LOW_COST_REVIEW_PENDING.value if cost_band == CostBand.LOW.value else IWDState.DEPARTMENT_HEAD_REVIEW_PENDING.value,
        to_status=status_value,
        actor_user_id=801,
        actor_label="IWD Admin" if cost_band == CostBand.LOW.value else "Department Head",
        reason="Estimate approved for execution",
    )
    return complaint, estimate


# -- 1. Workflow Tests (BW-IWD-06, BW-IWD-07, BW-IWD-08, CW-IWD-02) -----------

class TestInventoryWorkflows:
    def test_bw06_direct_stock_issuance_success(self):
        """Estimate Approved + issue_stock -> Materials Issued with MaterialIssue record (BW-IWD-06)."""
        complaint, _ = create_approved_complaint(estimated_cost=Decimal("12000.00"))
        admin = make_admin_principal(user_id=801)

        updated_complaint, issue = issue_stock_material(
            complaint_id=complaint.pk,
            principal=admin,
            materials_summary="2 PVC pipes (10ft), 4 couplers, 1 solvent can",
            remarks="Issued from Central Store",
        )

        assert updated_complaint.status == IWDState.MATERIALS_ISSUED.value
        assert issue.complaint_id == complaint.pk
        assert issue.admin_user_id == 801
        assert issue.source == "stock"
        assert issue.materials_summary == "2 PVC pipes (10ft), 4 couplers, 1 solvent can"
        assert issue.remarks == "Issued from Central Store"

        # Audit transition recorded
        trans = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert trans.from_status == IWDState.ESTIMATE_APPROVED.value
        assert trans.to_status == IWDState.MATERIALS_ISSUED.value
        assert trans.actor_user_id == 801
        assert trans.actor_label == "IWD Admin"
        assert "Stock materials issued" in trans.reason

    def test_bw07_low_cost_shortage_procurement_lifecycle(self):
        """Low-cost estimate shortage goes to Procurement Needed (Low) -> Materials Available -> Materials Issued (BW-IWD-07)."""
        complaint, _ = create_approved_complaint(estimated_cost=Decimal("18000.00"))
        admin = make_admin_principal(user_id=801)

        # Step 1: Stock unavailable -> Procurement Needed (Low)
        c1 = record_stock_shortage(complaint_id=complaint.pk, principal=admin, remarks="Pipes out of stock")
        assert c1.status == IWDState.PROCUREMENT_NEEDED_LOW.value

        t1 = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert t1.from_status == IWDState.ESTIMATE_APPROVED.value
        assert t1.to_status == IWDState.PROCUREMENT_NEEDED_LOW.value
        assert t1.actor_label == "IWD Admin"

        # Step 2: Procurement complete -> Materials Available
        c2 = complete_procurement(complaint_id=complaint.pk, principal=admin, remarks="Internal quotation PO #1042")
        assert c2.status == IWDState.MATERIALS_AVAILABLE.value

        t2 = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert t2.from_status == IWDState.PROCUREMENT_NEEDED_LOW.value
        assert t2.to_status == IWDState.MATERIALS_AVAILABLE.value

        # Step 3: Issue procured materials -> Materials Issued
        c3, issue = issue_procured_material(
            complaint_id=complaint.pk,
            principal=admin,
            materials_summary="3 PVC pipes (10ft), 6 couplers",
            remarks="Procured via internal quotation",
        )
        assert c3.status == IWDState.MATERIALS_ISSUED.value
        assert issue.source == "procurement"
        assert issue.materials_summary == "3 PVC pipes (10ft), 6 couplers"

        t3 = ComplaintTransition.objects.filter(complaint=complaint).order_by("-created_at").first()
        assert t3.from_status == IWDState.MATERIALS_AVAILABLE.value
        assert t3.to_status == IWDState.MATERIALS_ISSUED.value

    def test_bw08_mid_range_shortage_procurement_lifecycle(self):
        """Mid-range estimate shortage goes to Procurement Needed (Mid) -> Materials Available -> Materials Issued (BW-IWD-08)."""
        complaint, _ = create_approved_complaint(estimated_cost=Decimal("75000.00"))
        admin = make_admin_principal(user_id=801)

        # Step 1: Stock unavailable -> Procurement Needed (Mid)
        c1 = record_stock_shortage(complaint_id=complaint.pk, principal=admin, remarks="Mid-range materials shortage")
        assert c1.status == IWDState.PROCUREMENT_NEEDED_MID.value

        # Step 2: Procurement complete -> Materials Available
        c2 = complete_procurement(complaint_id=complaint.pk, principal=admin, remarks="Institutional procurement complete")
        assert c2.status == IWDState.MATERIALS_AVAILABLE.value

        # Step 3: Issue procured materials -> Materials Issued
        c3, issue = issue_procured_material(
            complaint_id=complaint.pk,
            principal=admin,
            materials_summary="Mid-range ceramic tiles and bonding mortar",
        )
        assert c3.status == IWDState.MATERIALS_ISSUED.value
        assert issue.source == "procurement"


# -- 2. Four Exact Cost-Band Boundaries Tests -----------------------------------

class TestCostBandShortageBoundaries:
    def test_boundary_shortage_routing_24999_99_routes_to_low(self):
        """Estimate of exactly ₹24,999.99 routes to Procurement Needed (Low) (BW-IWD-07)."""
        complaint, _ = create_approved_complaint(estimated_cost=Decimal("24999.99"))
        admin = make_admin_principal(user_id=801)

        updated = record_stock_shortage(complaint_id=complaint.pk, principal=admin)
        assert updated.status == IWDState.PROCUREMENT_NEEDED_LOW.value

    def test_boundary_shortage_routing_25000_00_routes_to_mid(self):
        """Estimate of exactly ₹25,000.00 routes to Procurement Needed (Mid) (BW-IWD-08)."""
        complaint, _ = create_approved_complaint(estimated_cost=Decimal("25000.00"))
        admin = make_admin_principal(user_id=801)

        updated = record_stock_shortage(complaint_id=complaint.pk, principal=admin)
        assert updated.status == IWDState.PROCUREMENT_NEEDED_MID.value

    def test_boundary_shortage_routing_250000_00_routes_to_mid(self):
        """Estimate of exactly ₹250,000.00 routes to Procurement Needed (Mid) (BW-IWD-08)."""
        complaint, _ = create_approved_complaint(estimated_cost=Decimal("250000.00"))
        admin = make_admin_principal(user_id=801)

        updated = record_stock_shortage(complaint_id=complaint.pk, principal=admin)
        assert updated.status == IWDState.PROCUREMENT_NEEDED_MID.value

    def test_boundary_high_cost_250000_01_rejected_from_inventory_actions_409(self):
        """High-cost work (> ₹2.5L) in Bidding Authorized is rejected from warehouse inventory actions (HTTP 409)."""
        complaint, _ = create_approved_complaint(
            estimated_cost=Decimal("250000.01"),
            status_value=IWDState.BIDDING_AUTHORIZED.value,
        )
        admin = make_admin_principal(user_id=801)

        with pytest.raises(ConflictError) as exc_info:
            issue_stock_material(
                complaint_id=complaint.pk,
                principal=admin,
                materials_summary="High cost steel girders",
            )
        assert exc_info.value.code == "invalid_state_transition"

        with pytest.raises(ConflictError) as exc_shortage:
            record_stock_shortage(complaint_id=complaint.pk, principal=admin)
        assert exc_shortage.value.code == "invalid_state_transition"


# -- 3. Active-Role Authorization and Role Separation Tests ---------------------

class TestInventoryAuthorizationAndRoles:
    def test_dormant_admin_role_rejected_403(self):
        """User with iwd_admin in roles but active_role='faculty' is rejected with HTTP 403."""
        complaint, _ = create_approved_complaint()
        dormant_admin = make_admin_principal(
            user_id=801,
            active_role="faculty",
            roles=("faculty", "iwd_admin"),
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            issue_stock_material(
                complaint_id=complaint.pk,
                principal=dormant_admin,
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "active_role_required"

    def test_engineer_denied_inventory_actions_403(self):
        """Engineer role cannot perform inventory actions (HTTP 403)."""
        complaint, _ = create_approved_complaint()
        engineer = make_session(
            user_id=501,
            permissions=("iwd.complaint.assess", "iwd.complaint.view"),
            modules=("iwd",),
            active_role="iwd_engineer",
            roles=("iwd_engineer",),
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            issue_stock_material(
                complaint_id=complaint.pk,
                principal=engineer,
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "active_role_required"

    def test_dept_head_denied_inventory_actions_403(self):
        """Department Head role cannot perform inventory actions (HTTP 403)."""
        complaint, _ = create_approved_complaint()
        dept_head = make_session(
            user_id=701,
            permissions=("iwd.estimate.review_mid", "iwd.complaint.view"),
            modules=("iwd",),
            active_role="Department Head",
            roles=("Department Head",),
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            record_stock_shortage(complaint_id=complaint.pk, principal=dept_head)
        assert exc_info.value.code == "active_role_required"

    def test_dean_denied_inventory_actions_403(self):
        """Dean role has no inventory permissions and is denied (HTTP 403, BR-IWD-018)."""
        complaint, _ = create_approved_complaint()
        dean = make_session(
            user_id=901,
            permissions=("iwd.complaint.view",),
            modules=("iwd",),
            active_role="Dean",
            roles=("Dean",),
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            issue_stock_material(
                complaint_id=complaint.pk,
                principal=dean,
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "active_role_required"

    def test_missing_inventory_permission_denied_403(self):
        """Active iwd_admin lacking iwd.inventory.manage permission is denied (HTTP 403)."""
        complaint, _ = create_approved_complaint()
        admin_no_perm = make_session(
            user_id=801,
            permissions=("iwd.complaint.view",),
            modules=("iwd",),
            active_role="iwd_admin",
            roles=("iwd_admin",),
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            issue_stock_material(
                complaint_id=complaint.pk,
                principal=admin_no_perm,
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "permission_denied"


# -- 4. State Guards, Duplicate Prevention & Invalid Transitions ---------------

class TestInventoryStateGuardsAndConcurrency:
    @pytest.mark.parametrize("invalid_state", [
        IWDState.SUBMITTED.value,
        IWDState.ASSIGNED.value,
        IWDState.ASSESSED.value,
        IWDState.LOW_COST_REVIEW_PENDING.value,
        IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING.value,
        IWDState.MATERIALS_ISSUED.value,
        IWDState.BIDDING_AUTHORIZED.value,
    ])
    def test_issue_stock_from_unapproved_state_raises_conflict_409(self, invalid_state):
        """Attempting to issue stock for complaints not in Estimate Approved raises ConflictError (HTTP 409)."""
        complaint, _ = create_approved_complaint(status_value=invalid_state)
        admin = make_admin_principal(user_id=801)

        with pytest.raises(ConflictError) as exc_info:
            issue_stock_material(
                complaint_id=complaint.pk,
                principal=admin,
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "invalid_state_transition"

    def test_procurement_complete_from_invalid_state_raises_conflict_409(self):
        """Calling procurement_complete from ESTIMATE_APPROVED raises ConflictError (HTTP 409)."""
        complaint, _ = create_approved_complaint(status_value=IWDState.ESTIMATE_APPROVED.value)
        admin = make_admin_principal(user_id=801)

        with pytest.raises(ConflictError) as exc_info:
            complete_procurement(complaint_id=complaint.pk, principal=admin)
        assert exc_info.value.code == "invalid_state_transition"

    def test_issue_procured_from_invalid_state_raises_conflict_409(self):
        """Calling issue_procured from PROCUREMENT_NEEDED_LOW raises ConflictError (HTTP 409)."""
        complaint, _ = create_approved_complaint(status_value=IWDState.PROCUREMENT_NEEDED_LOW.value)
        admin = make_admin_principal(user_id=801)

        with pytest.raises(ConflictError) as exc_info:
            issue_procured_material(
                complaint_id=complaint.pk,
                principal=admin,
                materials_summary="Pipes",
            )
        assert exc_info.value.code == "invalid_state_transition"

    def test_duplicate_stock_issuance_prevented_409(self):
        """After stock is issued, the complaint status is MATERIALS_ISSUED; second call raises ConflictError."""
        complaint, _ = create_approved_complaint()
        admin = make_admin_principal(user_id=801)

        # Call 1 succeeds
        issue_stock_material(
            complaint_id=complaint.pk,
            principal=admin,
            materials_summary="Pipes and valves",
        )

        # Call 2 immediately fails with ConflictError (HTTP 409)
        with pytest.raises(ConflictError) as exc_info:
            issue_stock_material(
                complaint_id=complaint.pk,
                principal=admin,
                materials_summary="Pipes and valves",
            )
        assert exc_info.value.code == "invalid_state_transition"


# -- 5. Input Validation, Rollback & Detail Contract Tests ----------------------

class TestInventoryValidationAndRollback:
    def test_blank_materials_summary_raises_bad_request_400(self):
        """Issuing stock or procured materials without a materials summary raises BadRequestError (HTTP 400)."""
        complaint, _ = create_approved_complaint()
        admin = make_admin_principal(user_id=801)

        for empty_val in ("", "   ", None):
            with pytest.raises(BadRequestError) as exc_info:
                issue_stock_material(
                    complaint_id=complaint.pk,
                    principal=admin,
                    materials_summary=empty_val,
                )
            assert exc_info.value.code == "missing_materials_summary"

    def test_transactional_rollback_on_audit_failure(self):
        """If writing the ComplaintTransition audit log fails, MaterialIssue creation and complaint status roll back."""
        complaint, _ = create_approved_complaint()
        admin = make_admin_principal(user_id=801)

        initial_status = complaint.status
        initial_mat_count = MaterialIssue.objects.count()
        initial_trans_count = ComplaintTransition.objects.count()

        with patch.object(ComplaintTransition.objects, "create", side_effect=RuntimeError("DB audit failure")):
            with pytest.raises(RuntimeError):
                issue_stock_material(
                    complaint_id=complaint.pk,
                    principal=admin,
                    materials_summary="10 bags cement",
                )

        complaint.refresh_from_db()
        assert complaint.status == initial_status
        assert MaterialIssue.objects.count() == initial_mat_count
        assert ComplaintTransition.objects.count() == initial_trans_count

    def test_complaint_detail_includes_material_issues(self):
        """ComplaintDetailSerializer exposes MaterialIssue history with correct details."""
        complaint, _ = create_approved_complaint()
        admin = make_admin_principal(user_id=801)

        _, issue = issue_stock_material(
            complaint_id=complaint.pk,
            principal=admin,
            materials_summary="10 bags Portland cement, 2 cubic meters sand",
            remarks="Direct warehouse issue",
        )

        from modules.iwd.api.serializers import ComplaintDetailSerializer
        serializer = ComplaintDetailSerializer(complaint)
        data = serializer.data

        assert "material_issues" in data
        assert len(data["material_issues"]) == 1
        mat_data = data["material_issues"][0]
        assert mat_data["id"] == issue.id
        assert mat_data["admin_user_id"] == 801
        assert mat_data["source"] == "stock"
        assert mat_data["materials_summary"] == "10 bags Portland cement, 2 cubic meters sand"
        assert mat_data["remarks"] == "Direct warehouse issue"
        assert "issued_at" in mat_data


# -- 6. API Endpoint Tests -----------------------------------------------------

class TestInventoryAPI:
    def test_api_issue_stock_success_200(self, stub_iam):
        complaint, _ = create_approved_complaint(estimated_cost=Decimal("15000.00"))
        session = make_admin_principal(user_id=801)
        client = make_client_for_session(stub_iam, session)

        payload = {
            "action": "issue_stock",
            "materials_summary": "4 meters copper pipe and solder wire",
            "remarks": "Warehouse Bay 3",
        }
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/inventory-action/", payload, format="json")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == complaint.pk
        assert data["status"] == IWDState.MATERIALS_ISSUED.value
        assert len(data["material_issues"]) == 1
        assert data["material_issues"][0]["source"] == "stock"
        assert data["material_issues"][0]["materials_summary"] == "4 meters copper pipe and solder wire"

    def test_api_shortage_procurement_flow_200(self, stub_iam):
        complaint, _ = create_approved_complaint(estimated_cost=Decimal("18000.00"))
        session = make_admin_principal(user_id=801)
        client = make_client_for_session(stub_iam, session)

        # 1. Stock unavailable
        r1 = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/inventory-action/", {"action": "stock_unavailable"}, format="json")
        assert r1.status_code == status.HTTP_200_OK
        assert r1.json()["status"] == IWDState.PROCUREMENT_NEEDED_LOW.value

        # 2. Procurement complete
        r2 = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/inventory-action/", {"action": "procurement_complete"}, format="json")
        assert r2.status_code == status.HTTP_200_OK
        assert r2.json()["status"] == IWDState.MATERIALS_AVAILABLE.value

        # 3. Issue procured material
        r3 = client.post(
            f"/api/v1/iwd/complaints/{complaint.pk}/inventory-action/",
            {"action": "issue_material", "materials_summary": "Procured copper pipe"},
            format="json",
        )
        assert r3.status_code == status.HTTP_200_OK
        assert r3.json()["status"] == IWDState.MATERIALS_ISSUED.value
        assert len(r3.json()["material_issues"]) == 1
        assert r3.json()["material_issues"][0]["source"] == "procurement"

    def test_api_dormant_role_denied_403(self, stub_iam):
        complaint, _ = create_approved_complaint()
        session = make_admin_principal(user_id=801, active_role="student", roles=("student", "iwd_admin"))
        client = make_client_for_session(stub_iam, session)

        payload = {"action": "issue_stock", "materials_summary": "Pipes"}
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/inventory-action/", payload, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_api_invalid_state_conflict_409(self, stub_iam):
        complaint, _ = create_approved_complaint(status_value=IWDState.ASSESSED.value)
        session = make_admin_principal(user_id=801)
        client = make_client_for_session(stub_iam, session)

        payload = {"action": "issue_stock", "materials_summary": "Pipes"}
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/inventory-action/", payload, format="json")
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_api_missing_materials_summary_bad_request_400(self, stub_iam):
        complaint, _ = create_approved_complaint()
        session = make_admin_principal(user_id=801)
        client = make_client_for_session(stub_iam, session)

        payload = {"action": "issue_stock", "materials_summary": "   "}
        resp = client.post(f"/api/v1/iwd/complaints/{complaint.pk}/inventory-action/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

