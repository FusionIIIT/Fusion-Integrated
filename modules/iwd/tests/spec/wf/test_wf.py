import pytest
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient
from modules.iwd.models import Complaint, Estimate, FinalBill

@pytest.mark.django_db
def test_wf_01_complaint_intake_and_assessment():
    """
    Test ID: test_wf_01_complaint_intake_and_assessment
    Source ID: BW-IWD-01 intake-assess
    """
    client = APIClient()
    res = client.post("/api/iwd/complaints/", {
        "title": "Window pane broken",
        "description": "Glass pane shattered in windstorm.",
        "category": "CIVIL",
        "location": "Library 2nd Floor"
    }, format="json", HTTP_X_ROLE="employee")
    c_id = res.json()["id"]
    complaint = Complaint.objects.get(id=c_id)
    assert complaint.status == "ASSIGNED"

@pytest.mark.django_db
def test_wf_09_work_execution_verification_success():
    """
    Test ID: test_wf_09_work_execution_verification_success
    Source ID: BW-IWD-09 execution-verification
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="Maths", category="CIVIL",
        title="Blackboard polish", description="Polishing classroom blackboard.", location="Hall 2",
        status="IN_PROGRESS"
    )
    res = client.post(f"/api/iwd/complaints/{c.id}/verify/", {"passed": True, "remarks": "Excellent finish"}, format="json", HTTP_X_ROLE="hod")
    assert res.status_code == status.HTTP_200_OK
    c.refresh_from_db()
    assert c.status == "RESOLVED"

@pytest.mark.django_db
def test_wf_10_rework_one_traversal():
    """
    Test ID: test_wf_10_rework_one_traversal
    Source ID: BW-IWD-10 rework-traversal
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="Maths", category="CIVIL",
        title="Desk varnish", description="Varnish exam desks.", location="Hall 1",
        status="IN_PROGRESS"
    )
    # First verification fails
    res1 = client.post(f"/api/iwd/complaints/{c.id}/verify/", {"passed": False, "remarks": "Coating uneven"}, format="json", HTTP_X_ROLE="hod")
    assert res1.json()["rework_count"] == 1
    c.refresh_from_db()
    assert c.status == "IN_PROGRESS"

    # Second verification passes
    res2 = client.post(f"/api/iwd/complaints/{c.id}/verify/", {"passed": True, "remarks": "Fixed properly"}, format="json", HTTP_X_ROLE="hod")
    c.refresh_from_db()
    assert c.status == "RESOLVED"

@pytest.mark.django_db
def test_wf_11_billing_audit_settlement():
    """
    Test ID: test_wf_11_billing_audit_settlement
    Source ID: BW-IWD-11 settlement-flow
    """
    client = APIClient()
    c = Complaint.objects.create(
        requester_id="emp_01", department="Physics", category="CIVIL",
        title="Optics bench mount", description="Concrete mounting for optics table.", location="Optics Lab",
        status="RESOLVED"
    )
    bill = FinalBill.objects.create(
        complaint=c, bill_number="BILL-WF-11", submitted_by_id="eng_01", total_amount=Decimal("18000.00")
    )

    # 1. Auditor verifies
    res_aud = client.post(f"/api/iwd/bills/{bill.id}/audit-verify/", HTTP_X_ROLE="auditor", HTTP_X_USER_ID="aud_01")
    assert res_aud.status_code == status.HTTP_200_OK

    # 2. Director approves
    res_dir = client.post(f"/api/iwd/bills/{bill.id}/director-approve/", HTTP_X_ROLE="director", HTTP_X_USER_ID="dir_01")
    assert res_dir.status_code == status.HTTP_200_OK

    # 3. Accounts settles
    res_acc = client.post(f"/api/iwd/bills/{bill.id}/settle/", HTTP_X_ROLE="accounts", HTTP_X_USER_ID="acc_01")
    assert res_acc.status_code == status.HTTP_200_OK
    bill.refresh_from_db()
    assert bill.settlement_status == "SETTLED_BY_ACCOUNTS"
    c.refresh_from_db()
    assert c.status == "CLOSED"
