import pytest
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient

from modules.iaa.models import (
    ExpenseRequest,
    TravelAllowanceClaim,
    DepartmentBudget,
    AnomalyRecord,
    AuditObservation,
    ApprovalAction,
)

@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def sample_budget(db):
    return DepartmentBudget.objects.create(
        department="Computer Science & Engineering",
        financial_year="2026-27",
        allocated_amount=Decimal("500000.00"),
        committed_amount=Decimal("50000.00"),
        spent_amount=Decimal("100000.00"),
    )

@pytest.mark.django_db
class TestIAABusinessRules:

    def test_submission_completeness_and_record_lock(self, client):
        """IAA-BR-101 & IAA-BR-104: Incomplete requests fail submission; complete requests lock."""
        # Create incomplete draft (amount 0)
        req = ExpenseRequest.objects.create(
            creator_user_id=101,
            department="CSE",
            title="Office Equipment",
            description="",
            request_type="reimbursement",
            amount=Decimal("0.00"),
            status="draft",
            is_locked=False,
        )

        # Attempt submit -> should fail completeness
        res = client.post(f"/api/v1/iaa/expenses/{req.id}/submit/", format="json")
        assert res.status_code == 400
        req.refresh_from_db()
        assert req.status == "draft"
        assert req.is_locked is False

        # Fix completeness
        req.description = "Mechanical Keyboards for Lab"
        req.amount = Decimal("25000.00")
        req.save()

        # Submit -> should succeed and lock
        res = client.post(f"/api/v1/iaa/expenses/{req.id}/submit/", {"notes": "Submitted with bills"}, format="json")
        assert res.status_code == 200
        req.refresh_from_db()
        assert req.status == "submitted"
        assert req.is_locked is True

        # Second submit attempt fails because record is locked
        res2 = client.post(f"/api/v1/iaa/expenses/{req.id}/submit/", format="json")
        assert res2.status_code == 400

    def test_configured_approval_routing_by_amount(self, client, sample_budget):
        """IAA-BR-002: Routing by monetary thresholds (<=50k HOD, <=200k Dean, >200k Director)."""
        # Case A: Amount <= 50,000 -> routes to HOD
        req_hod = ExpenseRequest.objects.create(
            creator_user_id=101,
            department=sample_budget.department,
            title="Consumables",
            description="Paper & Cartridges",
            request_type="reimbursement",
            amount=Decimal("45000.00"),
            status="submitted",
            is_locked=True,
        )
        res_a = client.post(f"/api/v1/iaa/expenses/{req_hod.id}/finance_review/", {"actor_user_id": 999}, format="json")
        assert res_a.status_code == 200
        req_hod.refresh_from_db()
        assert req_hod.current_authority_role == "hod"
        assert req_hod.status == "pending_approval"

        # Case B: Amount 50,001 - 2,00,000 -> routes to Dean
        req_dean = ExpenseRequest.objects.create(
            creator_user_id=102,
            department=sample_budget.department,
            title="Server RAM Upgrade",
            description="32GB ECC DDR5 Modules",
            request_type="vendor_payment",
            amount=Decimal("120000.00"),
            status="submitted",
            is_locked=True,
        )
        res_b = client.post(f"/api/v1/iaa/expenses/{req_dean.id}/finance_review/", {"actor_user_id": 999}, format="json")
        assert res_b.status_code == 200
        req_dean.refresh_from_db()
        assert req_dean.current_authority_role == "dean"

        # Case C: Amount > 2,00,000 -> routes to Director
        req_dir = ExpenseRequest.objects.create(
            creator_user_id=103,
            department=sample_budget.department,
            title="GPU Cluster Node",
            description="NVIDIA AI Workstation",
            request_type="vendor_payment",
            amount=Decimal("450000.00"),
            status="submitted",
            is_locked=True,
        )
        res_c = client.post(f"/api/v1/iaa/expenses/{req_dir.id}/finance_review/", {"actor_user_id": 999}, format="json")
        assert res_c.status_code == 200
        req_dir.refresh_from_db()
        assert req_dir.current_authority_role == "director"

    def test_segregation_of_duties_blocks_creator_approval(self, client):
        """IAA-BR-001: Creator cannot approve their own request."""
        req = ExpenseRequest.objects.create(
            creator_user_id=205,
            department="Electrical Engineering",
            title="Oscilloscope Probes",
            description="Lab replacement",
            request_type="reimbursement",
            amount=Decimal("15000.00"),
            status="pending_approval",
            current_authority_role="hod",
            is_locked=True,
        )

        # Attempt to approve where actor_user_id == creator_user_id (205)
        res = client.post(
            f"/api/v1/iaa/expenses/{req.id}/decision/",
            {"action": "approve", "remarks": "Self approval", "actor_user_id": 205},
            format="json",
        )
        assert res.status_code == 403
        assert "Segregation of duties" in res.data["detail"]
        req.refresh_from_db()
        assert req.status == "pending_approval"

    def test_approval_decision_requires_mandatory_remarks(self, client):
        """IAA-BR-005: Remarks are mandatory for all approval/rejection decisions."""
        req = ExpenseRequest.objects.create(
            creator_user_id=301,
            department="CSE",
            title="Conference Registration",
            description="IEEE Conference",
            request_type="reimbursement",
            amount=Decimal("12000.00"),
            status="pending_approval",
            current_authority_role="hod",
            is_locked=True,
        )

        # Decision without remarks -> should fail with 400
        res = client.post(
            f"/api/v1/iaa/expenses/{req.id}/decision/",
            {"action": "approve", "remarks": "", "actor_user_id": 302},
            format="json",
        )
        assert res.status_code == 400

        # Decision with remarks -> succeeds
        res_ok = client.post(
            f"/api/v1/iaa/expenses/{req.id}/decision/",
            {"action": "approve", "remarks": "Approved as per institute research policy.", "actor_user_id": 302},
            format="json",
        )
        assert res_ok.status_code == 200
        req.refresh_from_db()
        assert req.status == "approved"

    def test_budget_sufficiency_and_anomaly_trigger(self, client, sample_budget):
        """IAA-BR-102 & IAA-BR-103: Budget shortfall creates AnomalyRecord without hard rejection."""
        # Budget available: 500k - 50k - 100k = 350,000
        # Request amount: 400,000 (> 350k available)
        req = ExpenseRequest.objects.create(
            creator_user_id=401,
            department=sample_budget.department,
            title="High Performance Workstation",
            description="Compute Lab Expansion",
            request_type="vendor_payment",
            amount=Decimal("400000.00"),
            status="submitted",
            is_locked=True,
        )

        res = client.post(f"/api/v1/iaa/expenses/{req.id}/finance_review/", {"actor_user_id": 999}, format="json")
        assert res.status_code == 200

        # Verify AnomalyRecord was automatically flagged
        anomaly = AnomalyRecord.objects.filter(related_expense=req).first()
        assert anomaly is not None
        assert anomaly.anomaly_category == "budget_insufficiency"
        assert anomaly.status == "open"
        assert anomaly.flagged_by_role == "finance"

        # Verify request proceeded to pending approval (not rejected)
        req.refresh_from_db()
        assert req.status == "pending_approval"

    def test_non_monetary_internal_completion(self, client, sample_budget):
        """IAA-BR-006: Internal processing records governance completion without real monetary dispatch."""
        req = ExpenseRequest.objects.create(
            creator_user_id=501,
            department=sample_budget.department,
            title="Software License Renewal",
            description="MATLAB Campus License",
            request_type="vendor_payment",
            amount=Decimal("30000.00"),
            status="approved",
            is_locked=True,
        )
        # Commit budget
        sample_budget.committed_amount += Decimal("30000.00")
        sample_budget.save()

        initial_spent = sample_budget.spent_amount

        # Execute internal completion
        res = client.post(f"/api/v1/iaa/expenses/{req.id}/internal_complete/", {"actor_user_id": 999}, format="json")
        assert res.status_code == 200
        req.refresh_from_db()
        assert req.status == "internal_completed"

        sample_budget.refresh_from_db()
        assert sample_budget.spent_amount == initial_spent + Decimal("30000.00")

    def test_clarification_cycle_locks_and_unlocks(self, client):
        """CFR-IAA-02: Clarification request unlocks record; response re-locks record."""
        req = ExpenseRequest.objects.create(
            creator_user_id=601,
            department="CSE",
            title="Travel Advance",
            description="Trip for keynote",
            request_type="advance",
            amount=Decimal("20000.00"),
            status="submitted",
            is_locked=True,
        )

        # Finance requests clarification
        res_q = client.post(
            f"/api/v1/iaa/expenses/{req.id}/request_clarification/",
            {"query": "Please attach official invitation letter."},
            format="json",
        )
        assert res_q.status_code == 200
        req.refresh_from_db()
        assert req.status == "clarification_requested"
        assert req.is_locked is False  # Unlocked for creator to respond

        # Creator responds
        res_r = client.post(
            f"/api/v1/iaa/expenses/{req.id}/respond_clarification/",
            {"response": "Attached invitation letter from IEEE conference chairs."},
            format="json",
        )
        assert res_r.status_code == 200
        req.refresh_from_db()
        assert req.status == "clarification_responded"
        assert req.is_locked is True  # Re-locked

    def test_travel_allowance_high_value_flag(self, client):
        """IAA-BR-202: TA Claims >= 50,000 flagged as High-Value and routed to Dean."""
        # Claim with 65,000 >= 50,000
        claim = TravelAllowanceClaim.objects.create(
            claimant_user_id=701,
            department="CSE",
            purpose="International Symposium Presentation",
            departure_place="Jabalpur",
            destination_place="Singapore",
            start_date="2026-12-01",
            end_date="2026-12-05",
            claimed_amount=Decimal("65000.00"),
            is_high_value=True,
            status="submitted",
            is_locked=True,
        )

        res = client.post(f"/api/v1/iaa/ta-claims/{claim.id}/finance_review/", {"actor_user_id": 999}, format="json")
        assert res.status_code == 200
        claim.refresh_from_db()
        assert claim.is_high_value is True
        assert claim.current_authority_role == "dean"
        assert claim.status == "pending_approval"

    def test_audit_observation_lifecycle_and_closure(self, client):
        """IAA-BR-301 & IAA-BR-302: Audit observation lifecycle and closure verification by Auditor."""
        obs = AuditObservation.objects.create(
            observation_code="AUDIT-2026-001",
            auditor_user_id=801,
            target_department="CSE",
            subject="Inventory Discrepancy",
            query_details="Physical count of lab monitors differs by 2 units.",
            status="draft",
        )

        # Raise observation
        client.post(f"/api/v1/iaa/audit-observations/{obs.id}/raise_observation/", format="json")
        obs.refresh_from_db()
        assert obs.status == "raised"

        # Department responds
        client.post(
            f"/api/v1/iaa/audit-observations/{obs.id}/respond/",
            {"department_response": "Monitors were moved to Seminar Hall for workshop; now returned."},
            format="json",
        )
        obs.refresh_from_db()
        assert obs.status == "response_submitted"

        # Auditor verifies and closes
        res_close = client.post(
            f"/api/v1/iaa/audit-observations/{obs.id}/verify_close/",
            {"closure_remarks": "Physically verified in lab. Observation resolved."},
            format="json",
        )
        assert res_close.status_code == 200
        obs.refresh_from_db()
        assert obs.status == "verified_closed"
        assert obs.verified_by_auditor is True

    def test_approval_timeout_escalation(self, client):
        """IAA-BR-401: Overdue approval escalated to next authority level."""
        req = ExpenseRequest.objects.create(
            creator_user_id=901,
            department="CSE",
            title="Urgent Network Patch",
            description="Ethernet Switches",
            request_type="petty_cash",
            amount=Decimal("10000.00"),
            status="pending_approval",
            current_authority_role="hod",
            is_locked=True,
        )

        res = client.post(f"/api/v1/iaa/expenses/{req.id}/escalate/", format="json")
        assert res.status_code == 200
        req.refresh_from_db()
        assert req.status == "escalated"
        assert req.current_authority_role == "dean"  # HOD escalated to Dean

    def test_anomaly_resolution_and_escalation(self, client):
        """CFR-IAA-07: Track each anomaly through designated resolution or escalation."""
        anomaly = AnomalyRecord.objects.create(
            anomaly_category="documentation_gap",
            severity="medium",
            description="Missing original GST receipt invoice",
            status="open",
        )

        # Resolver resolves anomaly
        res = client.post(
            f"/api/v1/iaa/anomalies/{anomaly.id}/resolve/",
            {"resolution": "resolve", "remarks": "Digital signed copy verified", "resolver_user_id": 555},
            format="json",
        )
        assert res.status_code == 200
        anomaly.refresh_from_db()
        assert anomaly.status == "resolved"
        assert anomaly.resolution_remarks == "Digital signed copy verified"
        assert anomaly.resolved_at is not None

    def test_api_expense_list_and_create(self, client):
        """API: Create draft expense request and list."""
        data = {
            "title": "Lab Hardware",
            "description": "Sensors and breadboards",
            "department": "CSE",
            "request_type": "reimbursement",
            "amount": "8500.00",
            "creator_user_id": 111,
        }
        res = client.post("/api/v1/iaa/expenses/", data, format="json")
        assert res.status_code == 201
        assert res.data["status"] == "draft"
        assert res.data["is_locked"] is False

        # List expenses
        res_list = client.get("/api/v1/iaa/expenses/")
        assert res_list.status_code == 200
        assert len(res_list.data) >= 1

    def test_api_ta_claim_list_and_create(self, client):
        """API: Create draft TA claim and list."""
        data = {
            "claimant_user_id": 222,
            "department": "ECE",
            "purpose": "Faculty Development Workshop",
            "departure_place": "Jabalpur",
            "destination_place": "Delhi",
            "start_date": "2026-11-15",
            "end_date": "2026-11-18",
            "claimed_amount": "14200.00",
        }
        res = client.post("/api/v1/iaa/ta-claims/", data, format="json")
        assert res.status_code == 201
        assert res.data["is_high_value"] is False
        assert res.data["status"] == "draft"

    def test_department_budget_available_calculation(self, client):
        """CFR-IAA-06: Accurate calculation of departmental available budget."""
        budget = DepartmentBudget.objects.create(
            department="Mechanical Engineering",
            financial_year="2026-27",
            allocated_amount=Decimal("1000000.00"),
            committed_amount=Decimal("200000.00"),
            spent_amount=Decimal("300000.00"),
        )
        assert budget.available_budget == Decimal("500000.00")

        res = client.get(f"/api/v1/iaa/budgets/{budget.id}/")
        assert res.status_code == 200
        assert Decimal(res.data["available_budget"]) == Decimal("500000.00")

