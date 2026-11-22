from datetime import date, timedelta
from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models.doctors import Doctor
from modules.phc.models.inventory import InventoryItem
from modules.phc.models.patient_records import PatientVisit, Prescription
from modules.phc.services.doctors import create_doctor

pytestmark = pytest.mark.django_db


def test_doctor_availability_api(stub_iam):
    create_doctor(
        name="K. Raman",
        specialization="Dentistry",
        contact_phone="+91-9123456780",
        is_visiting=True,
    )

    stub_iam(
        make_session(
            user_id=1001,
            modules=("phc",),
            permissions=("phc.doctor_schedule.view",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token tok-123")

    res = c.get("/api/v1/phc/doctors/availability/")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["doctor_name"] == "K. Raman"


def test_reimbursement_student_rejected_by_api(stub_iam):
    stub_iam(
        make_session(
            user_id=1001,
            kind="student",
            roles=("student",),
            active_role="student",
            modules=("phc",),
            permissions=("phc.reimbursement.create",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token tok-123")

    payload = {
        "prescription_id": 999,
        "expense_date": date.today().isoformat(),
        "amount_claimed": "500.00",
    }
    res = c.post("/api/v1/phc/reimbursements/submit/", payload, format="json")
    # Must reject with 403 Forbidden or 400 Ineligible Claimant (BR-04)
    assert res.status_code in (400, 403)


def test_inventory_api_access(stub_iam):
    InventoryItem.objects.create(
        item_code="MED-VIT-C",
        name="Vitamin C 500mg",
        category="Supplements",
        stock_level=50,
        reorder_threshold=10,
        unit="Tablet",
    )

    stub_iam(
        make_session(
            user_id=901,
            kind="staff",
            roles=("phc_staff",),
            active_role="phc_staff",
            modules=("phc",),
            permissions=("phc.inventory.view",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token tok-123")

    res = c.get("/api/v1/phc/inventory/items/")
    assert res.status_code == 200
    data = res.json()
    assert any(it["item_code"] == "MED-VIT-C" for it in data)


def test_reports_api_de_identifies_pii_br12(stub_iam):
    # Setup patient records
    doc = Doctor.objects.create(name="A. Sen", specialization="Physician", is_visiting=False)
    PatientVisit.objects.create(
        patient_user_id=8888,
        doctor=doc,
        visit_date=date.today(),
        symptoms="Fever and Cough",
        diagnosis="Upper Respiratory Infection",
        created_by_user_id=901,
    )

    stub_iam(
        make_session(
            user_id=999,
            kind="staff",
            roles=("phc_admin",),
            active_role="phc_admin",
            modules=("phc",),
            permissions=("phc.report.view",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token tok-123")

    # Demographics / disease report
    res = c.get("/api/v1/phc/reports/?type=demographics")
    assert res.status_code == 200
    data = res.json()
    assert data.get("anonymized") is True
    # Confirm no patient_user_id (PII) is present in report
    content_str = str(data)
    assert "8888" not in content_str
    assert "patient_user_id" not in data


def test_audit_trail_api_access(stub_iam):
    stub_iam(
        make_session(
            user_id=999,
            kind="staff",
            roles=("phc_admin",),
            active_role="phc_admin",
            modules=("phc",),
            permissions=("phc.audit.view",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token tok-123")

    res = c.get("/api/v1/phc/audit/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
