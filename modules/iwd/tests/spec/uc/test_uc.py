import pytest
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient
from modules.iwd.models import Complaint, Estimate

@pytest.mark.django_db
def test_uc_001_submit_maintenance_complaint_main_flow():
    """
    Test ID: test_uc_001_submit_maintenance_complaint_main_flow
    Source ID: UC-IWD-001 Main Flow
    """
    client = APIClient()
    res = client.post("/api/iwd/complaints/", {
        "title": "Ceiling fan not working",
        "description": "Regulator and fan unresponsive in classroom 101.",
        "category": "ELECTRICAL",
        "location": "Classroom 101",
        "urgency": "NORMAL"
    }, format="json", HTTP_X_ROLE="employee", HTTP_X_USER_ID="emp_42")
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["status"] == "ASSIGNED"

@pytest.mark.django_db
def test_uc_015_estimate_preparation_main_flow():
    """
    Test ID: test_uc_015_estimate_preparation_main_flow
    Source ID: UC-IWD-015 Main Flow
    """
    c = Complaint.objects.create(
        requester_id="emp_01", department="ECE", category="CIVIL",
        title="Roof leak", description="Severe roof leak during rain.", location="Roof"
    )
    est = Estimate.objects.create(
        complaint=c, engineer_id="eng_civil_01", time_days=5,
        material_cost=Decimal("15000.00"), labor_cost=Decimal("5000.00"), other_cost=Decimal("2000.00")
    )
    assert est.total_cost == Decimal("22000.00")
    assert est.cost_band == "LOW"

@pytest.mark.django_db
def test_uc_041_mid_range_hod_approval_flow():
    """
    Test ID: test_uc_041_mid_range_hod_approval_flow
    Source ID: UC-IWD-041 Main Flow
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="ME", category="CIVIL",
        title="Workshop floor", description="Workshop concrete floor resurfacing.", location="WS-1"
    )
    est = Estimate.objects.create(
        complaint=c, engineer_id="eng_civil_01", time_days=10,
        material_cost=Decimal("50000.00"), labor_cost=Decimal("20000.00"), other_cost=Decimal("5000.00"),
        committee_reviewed=True
    )
    res = client.post(f"/api/iwd/estimates/{est.id}/approve/", HTTP_X_ROLE="hod", HTTP_X_USER_ID="hod_civil")
    assert res.status_code == status.HTTP_200_OK
    est.refresh_from_db()
    assert est.status == "APPROVED"

@pytest.mark.django_db
def test_uc_041_hod_rejection_alternative_flow():
    """
    Test ID: test_uc_041_hod_rejection_alternative_flow
    Source ID: UC-IWD-041 Alternative A1
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="ME", category="CIVIL",
        title="Excessive tiling", description="Requesting luxury granite flooring.", location="Office"
    )
    est = Estimate.objects.create(
        complaint=c, engineer_id="eng_civil_01", time_days=10,
        material_cost=Decimal("60000.00"), labor_cost=Decimal("20000.00"), other_cost=Decimal("5000.00"),
        committee_reviewed=True
    )
    res = client.post(f"/api/iwd/estimates/{est.id}/reject/", {"reason": "Material exceeds departmental standards"}, format="json", HTTP_X_ROLE="hod")
    assert res.status_code == status.HTTP_200_OK
    est.refresh_from_db()
    assert est.status == "REJECTED"
    assert est.rejection_reason == "Material exceeds departmental standards"
