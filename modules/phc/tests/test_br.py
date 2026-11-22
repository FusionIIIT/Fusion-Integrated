"""BR strategy: boundary, authorization, privacy and audit rules."""

from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


def test_claim_submit_requires_employee_own_prescription_expense_date(phc_client, prescription):
    student = phc_client(uid=1001, kind="student", permissions=("phc.claim.submit",))
    payload = {"prescription_id": prescription.pk, "amount_claimed": "20.00"}
    assert student.post("/api/v1/phc/claims/submit/", payload, format="json").status_code == 403
    employee = phc_client(uid=1001, kind="faculty", permissions=("phc.claim.submit",))
    assert employee.post("/api/v1/phc/claims/submit/", payload, format="json").status_code == 201
    other = phc_client(uid=2002, kind="staff", permissions=("phc.claim.submit",))
    assert other.post("/api/v1/phc/claims/submit/", payload, format="json").status_code == 409


def test_claimant_only_sees_own_claims_and_status_change_notifies(prescription, phc_client):
    from modules.phc.models import PhcNotification, ReimbursementClaim

    claim = ReimbursementClaim.objects.create(
        user_id=1001, prescription=prescription, amount_claimed=Decimal("12.00")
    )
    staff = phc_client(uid=900, kind="staff", permissions=("phc.claim.review_phc",))
    assert staff.post(f"/api/v1/phc/claims/{claim.pk}/review/").status_code == 200
    assert PhcNotification.objects.filter(
        recipient_user_id=1001, event_type="claim_status_changed"
    ).exists()
    claimant = phc_client(uid=1001, kind="faculty", permissions=("phc.claim.view_self",))
    assert claimant.get(f"/api/v1/phc/claims/my/{claim.pk}/").status_code == 200
    foreign = phc_client(uid=2002, kind="faculty", permissions=("phc.claim.view_self",))
    assert foreign.get(f"/api/v1/phc/claims/my/{claim.pk}/").status_code == 404


def test_submission_window_configuration_is_staff_only(phc_client):
    staff = phc_client(uid=900, kind="staff", permissions=("phc.claim.configure",))
    changed = staff.patch(
        "/api/v1/phc/claims/config/", {"submission_window_days": 30}, format="json"
    )
    assert changed.status_code == 200
    assert changed.json()["submission_window_days"] == 30
    patient = phc_client(uid=1001, permissions=())
    assert patient.get("/api/v1/phc/claims/config/").status_code == 403


def test_inventory_adjustment_audits_and_alerts_below_threshold(phc_client):
    from modules.phc.models import InventoryAudit, InventoryItem, PhcNotification

    item = InventoryItem.objects.create(
        name="Bandage", stock_quantity=Decimal("6"), reorder_threshold=Decimal("5")
    )
    staff = phc_client(uid=900, kind="staff", permissions=("phc.inventory.manage",))
    response = staff.post(
        f"/api/v1/phc/inventory/{item.pk}/adjust/", {"delta": "-2"}, format="json"
    )
    assert response.status_code == 200
    assert InventoryAudit.objects.filter(item=item, quantity_after=Decimal("4")).exists()
    assert PhcNotification.objects.filter(
        recipient_user_id=900, event_type="low_stock_alert"
    ).exists()
    assert (
        staff.post(
            f"/api/v1/phc/inventory/{item.pk}/adjust/", {"delta": "-99"}, format="json"
        ).status_code
        == 409
    )


def test_reports_do_not_expose_patient_identifiers(phc_client, visit):
    staff = phc_client(uid=900, kind="staff", permissions=("phc.report.view",))
    response = staff.get("/api/v1/phc/reports/?type=demographics")
    assert response.status_code == 200
    assert "user_id" not in response.content.decode()
    assert "chief_complaint" not in response.content.decode()


def test_demographics_report_aggregates_visits_by_patient_category(phc_client, monkeypatch):
    from types import SimpleNamespace

    from modules.directory import contracts as directory_contracts
    from modules.phc.models import PatientVisit

    PatientVisit.objects.create(
        user_id=1001,
        visit_date="2026-11-01",
        chief_complaint="A",
        recorded_by_user_id=900,
    )
    PatientVisit.objects.create(
        user_id=1001,
        visit_date="2026-11-02",
        chief_complaint="B",
        recorded_by_user_id=900,
    )
    PatientVisit.objects.create(
        user_id=2002,
        visit_date="2026-11-02",
        chief_complaint="C",
        recorded_by_user_id=900,
    )
    monkeypatch.setattr(
        directory_contracts,
        "get_users",
        lambda user_ids: {
            1001: SimpleNamespace(kind="student"),
            2002: SimpleNamespace(kind="faculty"),
        },
    )
    staff = phc_client(uid=900, kind="staff", permissions=("phc.report.view",))
    response = staff.get("/api/v1/phc/reports/?type=demographics")
    assert response.status_code == 200
    assert response.json()["patient_groups"] == [
        {"category": "employee", "patients": 1, "visits": 1},
        {"category": "student", "patients": 1, "visits": 2},
    ]
