from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from modules.iwd.domain.models import CostBand, determine_cost_band
from modules.iwd.models import Complaint, Estimate, FinalBill


@pytest.mark.django_db
def test_br_001_active_role_authorization():
    """
    Test ID: test_br_001_active_role_authorization
    Source ID: BR-IWD-001 active-role
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="Civil", category="CIVIL",
        title="Crack repair", description="Wall cracks appearing.", location="Lobby"
    )
    est = Estimate.objects.create(
        complaint=c, engineer_id="eng_01", time_days=2,
        material_cost=Decimal("5000.00"), labor_cost=Decimal("2000.00")
    )
    # Employee cannot approve estimate
    res = client.post(f"/api/iwd/estimates/{est.id}/approve/", HTTP_X_ROLE="employee")
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_br_003_cost_band_thresholds():
    """
    Test ID: test_br_003_cost_band_thresholds
    Source ID: BR-IWD-003 cost-band-routing
    """
    assert determine_cost_band(Decimal("24999.99")) == CostBand.LOW
    assert determine_cost_band(Decimal("25000.00")) == CostBand.MID
    assert determine_cost_band(Decimal("250000.00")) == CostBand.MID
    assert determine_cost_band(Decimal("250000.01")) == CostBand.HIGH

@pytest.mark.django_db
def test_br_004_low_cost_admin_approval():
    """
    Test ID: test_br_004_low_cost_admin_approval
    Source ID: BR-IWD-004 condition-true
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="Admin", category="ELECTRICAL",
        title="Tube light", description="Replace 2 tube lights in corridor.", location="Floor 1"
    )
    est = Estimate.objects.create(
        complaint=c, engineer_id="eng_01", time_days=1,
        material_cost=Decimal("2000.00"), labor_cost=Decimal("500.00")
    )
    res = client.post(f"/api/iwd/estimates/{est.id}/approve/", HTTP_X_ROLE="admin", HTTP_X_USER_ID="admin_01")
    assert res.status_code == status.HTTP_200_OK
    est.refresh_from_db()
    assert est.status == "APPROVED"

@pytest.mark.django_db
def test_br_005_mid_range_committee_required():
    """
    Test ID: test_br_005_mid_range_committee_required
    Source ID: BR-IWD-005 condition-unreviewed
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="Physics", category="CIVIL",
        title="Dark room partition", description="Install acoustic partition boards.", location="Darkroom"
    )
    est = Estimate.objects.create(
        complaint=c, engineer_id="eng_01", time_days=7,
        material_cost=Decimal("60000.00"), labor_cost=Decimal("20000.00"),
        committee_reviewed=False
    )
    res = client.post(f"/api/iwd/estimates/{est.id}/approve/", HTTP_X_ROLE="hod")
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

@pytest.mark.django_db
def test_br_007_high_cost_director_approval_required():
    """
    Test ID: test_br_007_high_cost_director_approval_required
    Source ID: BR-IWD-007 condition-high-cost
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="Sports", category="CIVIL",
        title="Gymnasium Extension", description="Construct steel truss extension for indoor court.", location="Gym"
    )
    est = Estimate.objects.create(
        complaint=c, engineer_id="eng_01", time_days=60,
        material_cost=Decimal("2000000.00"), labor_cost=Decimal("800000.00")
    )
    # HOD cannot approve high-cost
    res_hod = client.post(f"/api/iwd/estimates/{est.id}/approve/", HTTP_X_ROLE="hod")
    assert res_hod.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Director can approve high-cost
    res_dir = client.post(f"/api/iwd/estimates/{est.id}/approve/", HTTP_X_ROLE="director", HTTP_X_USER_ID="director_01")
    assert res_dir.status_code == status.HTTP_200_OK
    est.refresh_from_db()
    assert est.status == "APPROVED"

@pytest.mark.django_db
def test_br_009_rejection_reason_mandatory():
    """
    Test ID: test_br_009_rejection_reason_mandatory
    Source ID: BR-IWD-009 rejection-reason
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="Civil", category="CIVIL",
        title="Repaint fence", description="Repaint campus external boundary fence.", location="Perimeter"
    )
    est = Estimate.objects.create(
        complaint=c, engineer_id="eng_01", time_days=10,
        material_cost=Decimal("40000.00"), labor_cost=Decimal("15000.00"), committee_reviewed=True
    )
    res = client.post(f"/api/iwd/estimates/{est.id}/reject/", {"reason": ""}, format="json", HTTP_X_ROLE="hod")
    assert res.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_br_014_verify_before_resolution():
    """
    Test ID: test_br_014_verify_before_resolution
    Source ID: BR-IWD-014 verification-guard
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="CSE", category="CIVIL",
        title="Door replacement", description="Replace damaged wooden door.", location="Lab 1",
        status="IN_PROGRESS"
    )
    # Fails physical verification
    res = client.post(f"/api/iwd/complaints/{c.id}/verify/", {"passed": False, "remarks": "Alignment uneven"}, format="json", HTTP_X_ROLE="hod")
    assert res.status_code == status.HTTP_200_OK
    c.refresh_from_db()
    assert c.status == "IN_PROGRESS"

@pytest.mark.django_db
def test_br_016_settlement_sequence_guard():
    """
    Test ID: test_br_016_settlement_sequence_guard
    Source ID: BR-IWD-016 settlement-sequence
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="CSE", category="CIVIL",
        title="Flooring", description="Flooring repaired.", location="Room 2",
        status="RESOLVED"
    )
    bill = FinalBill.objects.create(
        complaint=c, bill_number="BILL-2026-001", submitted_by_id="eng_01",
        total_amount=Decimal("15000.00"), auditor_verified=False, director_approved=False
    )
    # Settlement without auditor verification refused
    res = client.post(f"/api/iwd/bills/{bill.id}/settle/", HTTP_X_ROLE="accounts")
    assert res.status_code == status.HTTP_409_CONFLICT

@pytest.mark.django_db
def test_br_018_dean_hod_separation():
    """
    Test ID: test_br_018_dean_hod_separation
    Source ID: BR-IWD-018 role-separation
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="Chem", category="ELECTRICAL",
        title="Fume hood wiring", description="Rewire fume hood power circuitry.", location="Chem Lab",
    )
    est = Estimate.objects.create(
        complaint=c, engineer_id="eng_01", time_days=4,
        material_cost=Decimal("30000.00"), labor_cost=Decimal("10000.00"),
        committee_reviewed=True
    )
    # Dean cannot approve mid-range without explicit role
    res = client.post(f"/api/iwd/estimates/{est.id}/approve/", HTTP_X_ROLE="dean")
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
