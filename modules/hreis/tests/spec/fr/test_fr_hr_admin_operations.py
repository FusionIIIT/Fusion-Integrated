import pytest
from datetime import date
from decimal import Decimal
from modules.hreis.models import (
    AppraisalSubmission,
    EmployeeServiceRecord,
    HrAuditLog,
    LtcRequest,
)

pytestmark = pytest.mark.django_db


def test_fr_024_hr_admin_manage_service_records(auth_client_factory):
    """TEST-FR-024 [HR-AFR-010]: Verify HR-EIS allows HR Administrator to manage employee master and service records."""
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    payload = {
        "user_id": 150,
        "employee_id": "EMP0150",
        "department": "CSE",
        "designation": "Assistant Professor",
        "category": "faculty",
        "appointment_date": "2024-01-15",
        "leave_balances": {"casual": 8, "medical": 10},
    }
    resp = client_admin.post("/api/v1/hreis/service-records/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["employee_id"] == "EMP0150"


def test_fr_025_hr_admin_verify_hr_requests(auth_client_factory):
    """TEST-FR-025 [HR-AFR-011]: Verify HR-EIS allows HR Administrator to verify HR requests."""
    ltc = LtcRequest.objects.create(
        user_id=151,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("15000.00"),
        status="submitted",
    )
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    resp = client_admin.post(
        f"/api/v1/hreis/ltc/{ltc.id}/verify/",
        {"verdict": "verified", "remarks": "Documents in order"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["verification_status"] == "verified"


def test_fr_026_hr_admin_configure_workflows(auth_client_factory):
    """TEST-FR-026 [HR-AFR-012]: Verify HR-EIS allows HR Administrator to configure HR workflows within HR-EIS scope."""
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    payload = {
        "setting_key": "appraisal_window",
        "setting_value": {
            "active": True,
            "academic_year": "2026-2027",
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
        },
        "description": "Appraisal window for 2026-2027",
    }
    resp = client_admin.put("/api/v1/hreis/workflows/settings/", payload, format="json")
    assert resp.status_code == 200
    assert resp.data["setting_value"]["academic_year"] == "2026-2027"


def test_fr_027_hr_admin_assign_appraisal_reviewers(auth_client_factory):
    """TEST-FR-027 [HR-AFR-013]: Verify HR-EIS allows HR Administrator to assign appraisal reviewers."""
    appraisal = AppraisalSubmission.objects.create(
        user_id=152,
        academic_year="2025-2026",
        content={"teaching": "Full load"},
        status="submitted",
    )
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    resp = client_admin.post(
        f"/api/v1/hreis/appraisals/{appraisal.id}/assign-reviewers/",
        {"reviewer_ids": [301, 302]},
        format="json",
    )
    assert resp.status_code == 200
    assert 301 in resp.data["assigned_reviewers"]
    assert 302 in resp.data["assigned_reviewers"]


def test_fr_028_hr_admin_monitor_compliance_and_audits(auth_client_factory):
    """TEST-FR-028 [HR-AFR-014]: Verify HR-EIS allows HR Administrator to monitor compliance and audits."""
    HrAuditLog.objects.create(
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
        action="test_compliance_action",
        entity_type="service_record",
        entity_id="1",
        details={"info": "audit monitoring"},
    )
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    resp = client_admin.get("/api/v1/hreis/audit-logs/")
    assert resp.status_code == 200
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert len(results) >= 1
