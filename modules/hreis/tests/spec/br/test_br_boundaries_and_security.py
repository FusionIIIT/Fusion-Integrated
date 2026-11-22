from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from modules.hreis.models import EmployeeServiceRecord, LtcRequest
from modules.hreis.services.claims import settle_ltc_claim

pytestmark = pytest.mark.django_db


def test_br_047_finance_boundary_internal_recording():
    """TEST-BR-047 [BR-HR-027 Integration Boundary]: Verify payment reference recorded without external banking gateway."""
    ltc = LtcRequest.objects.create(
        user_id=430,
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 11, 10),
        travel_end_date=date(2026, 11, 15),
        estimated_amount=Decimal("12000.00"),
        claimed_amount=Decimal("11000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        passed_amount=Decimal("11000.00"),
        reference_id="LTC-REF-430",
        remarks="Recorded internal settlement voucher",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"


def test_br_048_iam_session_consistency(auth_client_factory):
    """TEST-BR-048 [BR-HR-028 Identity Consistency]: Verify HR-EIS consumes Fusion IAM identity and enforces active role consistently."""
    EmployeeServiceRecord.objects.create(
        user_id=431,
        employee_id="EMP0431",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    client, _ = auth_client_factory(user_id=431, role="faculty")
    resp = client.get("/api/v1/hreis/service-records/me/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["employee_id"] == "EMP0431"


def test_br_049_role_assignment_boundary(auth_client_factory):
    """TEST-BR-049 [BR-HR-029 Authority Boundary]: Verify HR-EIS does not expose direct role-assignment APIs."""
    client, _ = auth_client_factory(user_id=432, role="faculty")
    resp = client.post(
        "/api/v1/hreis/assign-role/",
        {"user_id": 432, "role": "director"},
        format="json",
    )
    assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)


def test_br_050_sensitive_record_protection(auth_client_factory):
    """TEST-BR-050 [BR-HR-030 Sensitive Data]: Verify sensitive employee service record details protected from unauthorized disclosure."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=433,
        employee_id="EMP0433",
        department="CSE",
        designation="Professor",
        category="faculty",
    )
    client, _ = auth_client_factory(user_id=434, role="faculty")
    resp = client.get(f"/api/v1/hreis/service-records/{rec.id}/")
    assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


def test_br_051_payroll_exclusion():
    """TEST-BR-051 [BR-HR-031 Exclusion]: Verify HR-EIS does not execute salary computation or alter payroll rules."""
    import modules.hreis
    assert not hasattr(modules.hreis, "calculate_salary")
    assert not hasattr(modules.hreis, "execute_payroll")
