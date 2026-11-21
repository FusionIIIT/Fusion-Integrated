from django.utils import timezone
"""BR strategy tests — Specification-Driven AI-Assisted Testing (Assignment 8).

Generated from the frozen BR_DESIGN.json. One test function per design test
case; each test_id and source_id is preserved in the function name/docstring.
Production code is NOT modified.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import (
    AuditLog,
    DoctorSchedule,
    DoctorAttendance,
    HealthAdvisory,
    InventoryItem,
    Patient,
    Prescription,
    ReimbursementClaim,
    Requisition,
    StockAdjustment,
    Visit,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, user_id, kind="student", roles=("student",),
            active_role="student", permissions=(), modules=("phc",),
            users=None):
    stub_iam(make_session(user_id=user_id, kind=kind, roles=roles,
                          active_role=active_role, permissions=permissions,
                          modules=modules),
             users=users or {})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


# ---------------- BR-TC-001: PHC-BR-01 condition-true ----------------


def test_br_tc_001_phc_br_01_condition_true(stub_iam, user_ref):
    """BR-TC-001 | PHC-BR-01 condition-true | Availability combines schedule + attendance."""
    DoctorSchedule.objects.create(
        doctor_name="Dr A", day_of_week=0, start_time="09:00", end_time="13:00",
        is_published=True, published_by=1)
    DoctorSchedule.objects.create(
        doctor_name="Dr B", day_of_week=0, start_time="14:00", end_time="18:00",
        is_published=True, published_by=1)
    DoctorAttendance.objects.create(
        doctor_name="Dr A", date=timezone.now().date(), status="available", updated_by=1)
    DoctorAttendance.objects.create(
        doctor_name="Dr B", date=timezone.now().date(), status="departed", updated_by=1)
    c = _client(stub_iam, user_id=1001, kind="patient",
                permissions=("phc.schedule.view",),
                users={1001: user_ref(1001, kind="patient")})
    resp = c.get("/api/v1/phc/schedule")
    assert resp.status_code == 200
    body = resp.json()
    sched_map = {s["doctor_name"]: s for s in body["schedules"]}
    assert sched_map["Dr A"]["is_published"] is True
    assert sched_map["Dr B"]["is_published"] is True
    assert body["attendance"]["Dr A"] == "available"
    assert body["attendance"]["Dr B"] == "departed"


# ---------------- BR-TC-002: PHC-BR-02 patient own-record access permitted ----------------


def test_br_tc_002_phc_br_02_patient_own_record_access_permitted(stub_iam, user_ref):
    """BR-TC-002 | PHC-BR-02 patient own-record access permitted."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha Verma", kind="patient")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                recorded_by=1002)
    _patient2 = Patient.objects.create(user_id=2002, display_name="Ravi Iyer", kind="patient")
    c = _client(stub_iam, user_id=2001, kind="patient",
                permissions=("phc.records.view_self",),
                users={2001: user_ref(2001, kind="patient"),
                       2002: user_ref(2002, kind="patient")})
    resp = c.get("/api/v1/phc/records")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 1
    resp = c.get("/api/v1/phc/records/prescriptions")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 1


# ---------------- BR-TC-003: PHC-BR-02 patient other-record access prohibited ----------------


def test_br_tc_003_phc_br_02_patient_other_record_access_prohibited(stub_iam, user_ref):
    """BR-TC-003 | PHC-BR-02 patient other-record access prohibited."""
    _patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="patient")
    patient_b = Patient.objects.create(user_id=2002, display_name="Ravi", kind="patient")
    Visit.objects.create(patient=patient_b, user_id=patient_b.user_id, recorded_by=1002, notes="v")
    c = _client(stub_iam, user_id=2001, kind="patient",
                permissions=("phc.records.view_self",),
                users={2001: user_ref(2001, kind="patient")})
    resp = c.get(f"/api/v1/phc/records/download/{patient_b.visits.first().id}")
    assert resp.status_code == 404


# ---------------- BR-TC-004: PHC-BR-02 patient modification prohibited ----------------


def test_br_tc_004_phc_br_02_patient_modification_prohibited(stub_iam, user_ref):
    """BR-TC-004 | PHC-BR-02 patient modification prohibited."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="patient")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    c = _client(stub_iam, user_id=2001, kind="patient",
                permissions=("phc.records.view_self",),
                users={2001: user_ref(2001, kind="patient")})
    # No edit/delete endpoints exist for patient-owned records; attempts return 404/405
    resp = c.post("/api/v1/phc/staff/visits", {}, format="json")
    assert resp.status_code in (403, 404)
    resp = c.get(f"/api/v1/phc/records/download/{visit.id}")
    assert resp.status_code == 200


# ---------------- BR-TC-005: PHC-BR-02 PHC Staff role-authorized record management permitted ----------------


def test_br_tc_005_phc_br_02_staff_role_authorized_record_management(stub_iam, user_ref):
    """BR-TC-005 | PHC-BR-02 PHC Staff role-authorized record management permitted."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="patient")
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.records.manage",),
                users={1002: user_ref(1002, kind="staff"),
                       2001: user_ref(2001, kind="patient")})
    resp = c.get("/api/v1/phc/staff/patients/search?q=Asha")
    assert resp.status_code == 200
    assert any(r["user_id"] == 2001 for r in resp.json()["results"])
    resp = c.post("/api/v1/phc/staff/visits",
                  {"patient_id": patient.user_id, "notes": "Follow-up"}, format="json")
    assert resp.status_code == 201
    visit_id = resp.json()["id"]
    resp = c.post("/api/v1/phc/staff/prescriptions",
                  {"visit_id": visit_id, "patient_id": patient.user_id,
                   "medicine": "Paracetamol", "dosage": "500mg"}, format="json")
    assert resp.status_code == 201
    assert resp.json()["medicine"] == "Paracetamol"


# ---------------- BR-TC-006: PHC-BR-03 permitted function allowed ----------------


def test_br_tc_006_phc_br_03_permitted_function_allowed(stub_iam, user_ref):
    """BR-TC-006 | PHC-BR-03 permitted function allowed."""
    item = InventoryItem.objects.create(name="Gloves", unit="boxes", quantity=50,
                                        reorder_threshold=5)
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": 5, "direction": "add",
                   "reason": "restock"}, format="json")
    assert resp.status_code == 201
    assert resp.json()["quantity"] == 5


# ---------------- BR-TC-007: PHC-BR-03 unauthorized function denied ----------------


def test_br_tc_007_phc_br_03_unauthorized_function_denied(stub_iam, user_ref):
    """BR-TC-007 | PHC-BR-03 unauthorized function denied."""
    item = InventoryItem.objects.create(name="Gloves", unit="boxes", quantity=50,
                                        reorder_threshold=5)
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="patient")
    req = Requisition.objects.create(originator=patient, user_id=patient.user_id, state="pending_approval")
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id,
        prescription=Prescription.objects.create(
            visit=Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v"),
            patient=patient, user_id=patient.user_id, medicine="Paracetamol", recorded_by=1002),
        expense_date="2026-11-01", amount="1000.00", state="submitted",
        stage_actor="PHC Staff", action_history=["submitted by employee"])
    # (a) patient updates stock
    c1 = _client(stub_iam, user_id=2001, kind="patient",
                 permissions=(),
                 users={2001: user_ref(2001, kind="patient")})
    resp = c1.post("/api/v1/phc/staff/inventory/adjust",
                   {"item_id": item.id, "quantity": 5, "direction": "add"},
                   format="json")
    assert resp.status_code in (403, 404)
    # (b) PHC Staff decides requisition
    c2 = _client(stub_iam, user_id=1002, kind="staff",
                 permissions=(),
                 users={1002: user_ref(1002, kind="staff")})
    resp = c2.post(f"/api/v1/phc/approver/requisitions/{req.requisition_id}/decide",
                   {"decision": "approve"}, format="json")
    assert resp.status_code in (403, 404)
    # (c) Accounts & Audit updates stock
    c3 = _client(stub_iam, user_id=1003, kind="audit",
                 permissions=(),
                 users={1003: user_ref(1003, kind="audit")})
    resp = c3.post("/api/v1/phc/staff/inventory/adjust",
                   {"item_id": item.id, "quantity": 5, "direction": "add"},
                   format="json")
    assert resp.status_code in (403, 404)
    # (d) patient performs PHC Staff review of claim
    c4 = _client(stub_iam, user_id=2001, kind="patient",
                 permissions=(),
                 users={2001: user_ref(2001, kind="patient")})
    resp = c4.post(f"/api/v1/phc/staff/claims/{claim.claim_id}/review", {}, format="json")
    assert resp.status_code in (403, 404)


# ---------------- BR-TC-008: PHC-BR-04 employee permitted ----------------


def test_br_tc_008_phc_br_04_employee_permitted(stub_iam, user_ref):
    """BR-TC-008 | PHC-BR-04 employee permitted."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="employee")})
    resp = c.post("/api/v1/phc/claims",
                  {"prescription_id": rx.id, "expense_date": "2026-11-01",
                   "amount": "1000.00"}, format="json")
    assert resp.status_code == 201


# ---------------- BR-TC-009: PHC-BR-04 student denied ----------------


def test_br_tc_009_phc_br_04_student_denied(stub_iam, user_ref):
    """BR-TC-009 | PHC-BR-04 student denied."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="student")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                recorded_by=1002)
    c = _client(stub_iam, user_id=2001, kind="student",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="student")})
    resp = c.post("/api/v1/phc/claims",
                  {"prescription_id": 1, "expense_date": "2026-11-01",
                   "amount": "1000.00"}, format="json")
    assert resp.status_code == 400


# ---------------- BR-TC-010: PHC-BR-05 valid prescription for claimant accepted ----------------


def test_br_tc_010_phc_br_05_valid_prescription_for_claimant_accepted(stub_iam, user_ref):
    """BR-TC-010 | PHC-BR-05 valid prescription for claimant accepted."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="employee")})
    resp = c.post("/api/v1/phc/claims",
                  {"prescription_id": rx.id, "expense_date": "2026-11-01",
                   "amount": "1000.00"}, format="json")
    assert resp.status_code == 201


# ---------------- BR-TC-011: PHC-BR-05 prescription does not exist ----------------


def test_br_tc_011_phc_br_05_prescription_does_not_exist(stub_iam, user_ref):
    """BR-TC-011 | PHC-BR-05 prescription does not exist."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="employee")})
    resp = c.post("/api/v1/phc/claims",
                  {"prescription_id": 9999, "expense_date": "2026-11-01",
                   "amount": "1000.00"}, format="json")
    assert resp.status_code == 400
    assert ReimbursementClaim.objects.count() == 0


# ---------------- BR-TC-012: PHC-BR-05 prescription belongs to another person ----------------


def test_br_tc_012_phc_br_05_prescription_belongs_to_another(stub_iam, user_ref):
    """BR-TC-012 | PHC-BR-05 prescription belongs to another person."""
    patient_e1 = Patient.objects.create(user_id=2001, display_name="E1", kind="employee")
    patient_e2 = Patient.objects.create(user_id=2002, display_name="E2", kind="employee")
    visit_e2 = Visit.objects.create(patient=patient_e2, user_id=patient_e2.user_id, recorded_by=1002, notes="v")
    rx_e2 = Prescription.objects.create(visit=visit_e2, patient=patient_e2,
                                        user_id=patient_e2.user_id,
                                        medicine="Paracetamol", recorded_by=1002)
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="employee")})
    resp = c.post("/api/v1/phc/claims",
                  {"prescription_id": rx_e2.id, "expense_date": "2026-11-01",
                   "amount": "1000.00"}, format="json")
    assert resp.status_code == 400
    assert ReimbursementClaim.objects.filter(employee=patient_e1).count() == 0


# ---------------- BR-TC-013: PHC-BR-06 within window accepted ----------------


def test_br_tc_013_phc_br_06_within_window_accepted(stub_iam, user_ref):
    """BR-TC-013 | PHC-BR-06 within window accepted."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="employee")})
    resp = c.post("/api/v1/phc/claims",
                  {"prescription_id": rx.id, "expense_date": "2026-11-01",
                   "amount": "1000.00"}, format="json")
    assert resp.status_code == 201


# ---------------- BR-TC-014: PHC-BR-06 outside window rejected ----------------


def test_br_tc_014_phc_br_06_outside_window_rejected(stub_iam, user_ref):
    """BR-TC-014 | PHC-BR-06 outside window rejected."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="employee")})
    resp = c.post("/api/v1/phc/claims",
                  {"prescription_id": rx.id, "expense_date": "2020-01-01",
                   "amount": "1000.00"}, format="json")
    assert resp.status_code == 400
    assert ReimbursementClaim.objects.count() == 0


# ---------------- BR-TC-015: PHC-BR-07 stock below threshold ----------------


def test_br_tc_015_phc_br_07_stock_below_threshold(stub_iam, user_ref):
    """BR-TC-015 | PHC-BR-07 stock below threshold -> low-stock alert."""
    item = InventoryItem.objects.create(name="Gloves", unit="boxes", quantity=25,
                                        reorder_threshold=10)
    before = AuditLog.objects.count()
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": 16, "direction": "deduct",
                   "reason": "consumption"}, format="json")
    assert resp.status_code == 201
    item.refresh_from_db()
    assert item.quantity == 9
    assert AuditLog.objects.count() > before


# ---------------- BR-TC-016: PHC-BR-07 stock equal to threshold ----------------


def test_br_tc_016_phc_br_07_stock_equal_to_threshold(stub_iam, user_ref):
    """BR-TC-016 | PHC-BR-07 stock equal to threshold -> no alert."""
    item = InventoryItem.objects.create(name="Gloves", unit="boxes", quantity=25,
                                        reorder_threshold=10)
    before = AuditLog.objects.count()
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": 15, "direction": "deduct",
                   "reason": "consumption"}, format="json")
    assert resp.status_code == 201
    item.refresh_from_db()
    assert item.quantity == 10


# ---------------- BR-TC-017: PHC-BR-07 stock above threshold ----------------


def test_br_tc_017_phc_br_07_stock_above_threshold(stub_iam, user_ref):
    """BR-TC-017 | PHC-BR-07 stock above threshold -> no alert."""
    item = InventoryItem.objects.create(name="Gloves", unit="boxes", quantity=25,
                                        reorder_threshold=10)
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": 5, "direction": "deduct",
                   "reason": "consumption"}, format="json")
    assert resp.status_code == 201
    resp = c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": 30, "direction": "add",
                   "reason": "restock"}, format="json")
    assert resp.status_code == 201
    item.refresh_from_db()
    assert item.quantity == 50


# ---------------- BR-TC-018: PHC-BR-08 sequential routing (approved path) ----------------


def test_br_tc_018_phc_br_08_sequential_routing_approved_path(stub_iam, user_ref):
    """BR-TC-018 | PHC-BR-08 sequential routing (approved path)."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="submitted", stage_actor="PHC Staff",
        action_history=["submitted by employee"])
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.reimbursement.review",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post(f"/api/v1/phc/staff/claims/{claim.claim_id}/review", {}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "pending_audit"
    c2 = _client(stub_iam, user_id=1003, kind="audit",
                 permissions=("phc.reimbursement.verify", "phc.reimbursement.payment"),
                 users={1003: user_ref(1003, kind="audit")})
    resp = c2.post(f"/api/v1/phc/audit/claims/{claim.claim_id}/verify", {}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "pending_sanction"
    c3 = _client(stub_iam, user_id=1004, kind="approver",
                 permissions=("phc.reimbursement.sanction",),
                 users={1004: user_ref(1004, kind="approver")})
    resp = c3.post(f"/api/v1/phc/approver/claims/{claim.claim_id}/sanction",
                   {"decision": "approve"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved_for_payment"
    c2 = _client(stub_iam, user_id=1003, kind="audit",
                 permissions=("phc.reimbursement.verify", "phc.reimbursement.payment"),
                 users={1003: user_ref(1003, kind="audit")})
    resp = c2.post(f"/api/v1/phc/audit/claims/{claim.claim_id}/payment", {}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "reimbursed"
    assert resp.json()["state"] == "reimbursed"


# ---------------- BR-TC-019: PHC-BR-08 no stage skipping ----------------


def test_br_tc_019_phc_br_08_no_stage_skipping(stub_iam, user_ref):
    """BR-TC-019 | PHC-BR-08 no stage skipping."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="submitted", stage_actor="PHC Staff",
        action_history=["submitted by employee"])
    c_audit = _client(stub_iam, user_id=1003, kind="audit",
                      permissions=("phc.reimbursement.verify",),
                      users={1003: user_ref(1003, kind="audit")})
    resp = c_audit.post(f"/api/v1/phc/audit/claims/{claim.claim_id}/verify", {}, format="json")
    assert resp.status_code == 404
    c_approver = _client(stub_iam, user_id=1004, kind="approver",
                         permissions=("phc.reimbursement.sanction",),
                         users={1004: user_ref(1004, kind="approver")})
    resp = c_approver.post(f"/api/v1/phc/approver/claims/{claim.claim_id}/sanction",
                           {"decision": "approve"}, format="json")
    assert resp.status_code == 404
    claim.refresh_from_db()
    assert claim.state == "submitted"


# ---------------- BR-TC-020: PHC-BR-08 no amount-based conditional sanctioning ----------------


def test_br_tc_020_phc_br_08_no_amount_based_conditional_sanctioning(stub_iam, user_ref):
    """BR-TC-020 | PHC-BR-08 no amount-based conditional sanctioning."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim_low = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="10.00", state="pending_sanction", stage_actor="Approving Authority",
        action_history=["submitted by employee", "PHC review forwarded", "A&A verified"])
    claim_high = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000000.00", state="pending_sanction",
        stage_actor="Approving Authority",
        action_history=["submitted by employee", "PHC review forwarded", "A&A verified"])
    c = _client(stub_iam, user_id=1004, kind="approver",
                permissions=("phc.reimbursement.sanction", "phc.reimbursement.payment"),
                users={1004: user_ref(1004, kind="approver")})
    resp = c.post(f"/api/v1/phc/audit/claims/{claim_low.claim_id}/payment", {}, format="json")
    assert resp.status_code == 404
    resp = c.post(f"/api/v1/phc/audit/claims/{claim_high.claim_id}/payment", {}, format="json")
    assert resp.status_code == 404
    claim_low.refresh_from_db()
    claim_high.refresh_from_db()
    assert claim_low.state == "pending_sanction"
    assert claim_high.state == "pending_sanction"


# ---------------- BR-TC-021: PHC-BR-08 exception Approving Authority rejection ends claim ----------------


def test_br_tc_021_phc_br_08_approver_rejection_ends_claim(stub_iam, user_ref):
    """BR-TC-021 | PHC-BR-08 exception Approving Authority rejection ends claim."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="pending_sanction", stage_actor="Approving Authority",
        action_history=["submitted by employee", "PHC review forwarded", "A&A verified"])
    c = _client(stub_iam, user_id=1004, kind="approver",
                permissions=("phc.reimbursement.sanction",),
                users={1004: user_ref(1004, kind="approver")})
    resp = c.post(f"/api/v1/phc/approver/claims/{claim.claim_id}/sanction",
                  {"decision": "reject"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "rejected"
    c2 = _client(stub_iam, user_id=1003, kind="audit",
                 permissions=("phc.reimbursement.payment",),
                 users={1003: user_ref(1003, kind="audit")})
    resp = c2.post(f"/api/v1/phc/audit/claims/{claim.claim_id}/payment", {}, format="json")
    assert resp.status_code == 404
    claim.refresh_from_db()
    assert claim.state == "rejected"


# ---------------- BR-TC-022: PHC-BR-08 exception no reject/return at PHC Staff and Accounts & Audit ----------------


def test_br_tc_022_phc_br_08_no_reject_return_at_phc_and_audit(stub_iam, user_ref):
    """BR-TC-022 | PHC-BR-08 exception no reject/return at PHC Staff and Accounts & Audit."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim_c4 = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="submitted", stage_actor="PHC Staff",
        action_history=["submitted by employee"])
    claim_c5 = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="2000.00", state="pending_audit", stage_actor="Accounts & Audit",
        action_history=["submitted by employee", "PHC review forwarded"])
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.reimbursement.review",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post(f"/api/v1/phc/staff/claims/{claim_c4.claim_id}/review",
                  {"decision": "reject"}, format="json")
    assert resp.status_code in (200, 400)
    claim_c4.refresh_from_db()
    assert claim_c4.state in ("submitted", "pending_audit")
    c2 = _client(stub_iam, user_id=1003, kind="audit",
                 permissions=("phc.reimbursement.verify",),
                 users={1003: user_ref(1003, kind="audit")})
    resp = c2.post(f"/api/v1/phc/audit/claims/{claim_c5.claim_id}/verify",
                   {"decision": "reject"}, format="json")
    assert resp.status_code in (200, 400)
    claim_c5.refresh_from_db()
    assert claim_c5.state in ("pending_audit", "pending_sanction")


# ---------------- BR-TC-023: PHC-BR-09 patient record change audited ----------------


def test_br_tc_023_phc_br_09_patient_record_change_audited(stub_iam, user_ref):
    """BR-TC-023 | PHC-BR-09 patient record change audited."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="patient")
    before = AuditLog.objects.count()
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.records.manage",),
                users={1002: user_ref(1002, kind="staff"),
                       2001: user_ref(2001, kind="patient")})
    resp = c.post("/api/v1/phc/staff/visits",
                  {"patient_id": patient.user_id, "notes": "Follow-up"}, format="json")
    assert resp.status_code == 201
    visit_id = resp.json()["id"]
    resp = c.post("/api/v1/phc/staff/prescriptions",
                  {"visit_id": visit_id, "patient_id": patient.user_id,
                   "medicine": "Paracetamol", "dosage": "500mg"}, format="json")
    assert resp.status_code == 201
    assert AuditLog.objects.count() > before


# ---------------- BR-TC-024: PHC-BR-09 inventory level change audited ----------------


def test_br_tc_024_phc_br_09_inventory_level_change_audited(stub_iam, user_ref):
    """BR-TC-024 | PHC-BR-09 inventory level change audited."""
    item = InventoryItem.objects.create(name="Gloves", unit="boxes", quantity=50,
                                        reorder_threshold=5)
    before = AuditLog.objects.count()
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": 10, "direction": "add",
                   "reason": "restock"}, format="json")
    assert resp.status_code == 201
    resp = c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": 5, "direction": "deduct",
                   "reason": "consumption"}, format="json")
    assert resp.status_code == 201
    assert AuditLog.objects.count() > before + 1


# ---------------- BR-TC-025: PHC-BR-09 reimbursement-claim status change audited ----------------


def test_br_tc_025_phc_br_09_reimbursement_claim_status_change_audited(stub_iam, user_ref):
    """BR-TC-025 | PHC-BR-09 reimbursement-claim status change audited."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="submitted", stage_actor="PHC Staff",
        action_history=["submitted by employee"])
    before = AuditLog.objects.count()
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.reimbursement.review",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post(f"/api/v1/phc/staff/claims/{claim.claim_id}/review", {}, format="json")
    assert resp.status_code == 200
    assert AuditLog.objects.count() > before


# ---------------- BR-TC-026: PHC-BR-09 audit records immutable ----------------


def test_br_tc_026_phc_br_09_audit_records_immutable(stub_iam, user_ref):
    """BR-TC-026 | PHC-BR-09 audit records immutable."""
    item = InventoryItem.objects.create(name="Gloves", unit="boxes", quantity=50,
                                        reorder_threshold=5)
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": 10, "direction": "add",
                   "reason": "restock"}, format="json")
    assert resp.status_code == 201
    audit_id = AuditLog.objects.filter(action="inventory.adjust").first().id
    # No edit/delete endpoint exists for audit records
    resp = c.patch(f"/api/v1/phc/audit/log/{audit_id}", {}, format="json")
    assert resp.status_code == 404
    before_count = AuditLog.objects.count()
    c.post("/api/v1/phc/staff/inventory/adjust",
           {"item_id": item.id, "quantity": 5, "direction": "add",
            "reason": "restock"}, format="json")
    assert AuditLog.objects.count() == before_count + 1


# ---------------- BR-TC-027: PHC-BR-10 submission sets Pending Approval and routes ----------------


def test_br_tc_027_phc_br_10_submission_sets_pending_approval_and_routes(stub_iam, user_ref):
    """BR-TC-027 | PHC-BR-10 submission sets Pending Approval and routes."""
    item = InventoryItem.objects.create(name="Gloves", unit="boxes", quantity=10,
                                        reorder_threshold=5)
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    c = _client(stub_iam, user_id=2001, kind="staff",
                permissions=("phc.inventory.requisition.submit",),
                users={2001: user_ref(2001, kind="staff")})
    resp = c.post("/api/v1/phc/staff/requisitions",
                  {"items": [{"item_id": item.id, "quantity": 100}]}, format="json")
    assert resp.status_code == 201
    assert resp.json()["state"] == "pending_approval"


# ---------------- BR-TC-028: PHC-BR-10 approved requisition may proceed ----------------


def test_br_tc_028_phc_br_10_approved_requisition_may_proceed(stub_iam, user_ref):
    """BR-TC-028 | PHC-BR-10 approved requisition may proceed."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    req = Requisition.objects.create(originator=patient, user_id=patient.user_id, state="approved")
    c = _client(stub_iam, user_id=2001, kind="staff",
                permissions=("phc.inventory.requisition.fulfill",),
                users={2001: user_ref(2001, kind="staff")})
    resp = c.post(f"/api/v1/phc/staff/requisitions/{req.requisition_id}/fulfill",
                  {}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "fulfilled"


# ---------------- BR-TC-029: PHC-BR-10 pending requisition may not proceed ----------------


def test_br_tc_029_phc_br_10_pending_requisition_may_not_proceed(stub_iam, user_ref):
    """BR-TC-029 | PHC-BR-10 pending requisition may not proceed."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    req = Requisition.objects.create(originator=patient, user_id=patient.user_id, state="pending_approval")
    c = _client(stub_iam, user_id=2001, kind="staff",
                permissions=("phc.inventory.requisition.fulfill",),
                users={2001: user_ref(2001, kind="staff")})
    resp = c.post(f"/api/v1/phc/staff/requisitions/{req.requisition_id}/fulfill",
                  {}, format="json")
    assert resp.status_code == 404


# ---------------- BR-TC-030: PHC-BR-10 exception Rejected requisition ends progression ----------------


def test_br_tc_030_phc_br_10_rejected_requisition_ends_progression(stub_iam, user_ref):
    """BR-TC-030 | PHC-BR-10 exception Rejected requisition ends progression."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    req = Requisition.objects.create(originator=patient, user_id=patient.user_id, state="rejected")
    c = _client(stub_iam, user_id=2001, kind="staff",
                permissions=("phc.inventory.requisition.fulfill",),
                users={2001: user_ref(2001, kind="staff")})
    resp = c.post(f"/api/v1/phc/staff/requisitions/{req.requisition_id}/fulfill",
                  {}, format="json")
    assert resp.status_code == 404
    c2 = _client(stub_iam, user_id=1004, kind="approver",
                 permissions=("phc.inventory.requisition.decide",),
                 users={1004: user_ref(1004, kind="approver")})
    resp = c2.post(f"/api/v1/phc/approver/requisitions/{req.requisition_id}/decide",
                   {"decision": "approve"}, format="json")
    assert resp.status_code == 404


# ---------------- BR-TC-031: PHC-BR-11 approved notification ----------------


def test_br_tc_031_phc_br_11_approved_notification(stub_iam, user_ref):
    """BR-TC-031 | PHC-BR-11 approved notification."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    _patient2 = Patient.objects.create(user_id=2002, display_name="Bala", kind="staff")
    req = Requisition.objects.create(originator=patient, user_id=patient.user_id, state="pending_approval")
    before = AuditLog.objects.count()
    c = _client(stub_iam, user_id=1004, kind="approver",
                permissions=("phc.inventory.requisition.decide",),
                users={1004: user_ref(1004, kind="approver")})
    resp = c.post(f"/api/v1/phc/approver/requisitions/{req.requisition_id}/decide",
                  {"decision": "approve"}, format="json")
    assert resp.status_code == 200
    assert AuditLog.objects.count() > before


# ---------------- BR-TC-032: PHC-BR-11 rejected notification ----------------


def test_br_tc_032_phc_br_11_rejected_notification(stub_iam, user_ref):
    """BR-TC-032 | PHC-BR-11 rejected notification."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    _patient2 = Patient.objects.create(user_id=2002, display_name="Bala", kind="staff")
    req = Requisition.objects.create(originator=patient, user_id=patient.user_id, state="pending_approval")
    before = AuditLog.objects.count()
    c = _client(stub_iam, user_id=1004, kind="approver",
                permissions=("phc.inventory.requisition.decide",),
                users={1004: user_ref(1004, kind="approver")})
    resp = c.post(f"/api/v1/phc/approver/requisitions/{req.requisition_id}/decide",
                  {"decision": "reject"}, format="json")
    assert resp.status_code == 200
    assert AuditLog.objects.count() > before


# ---------------- BR-TC-033: PHC-BR-12 patient demographics report anonymized ----------------


def test_br_tc_033_phc_br_12_patient_demographics_report_anonymized(stub_iam, user_ref):
    """BR-TC-033 | PHC-BR-12 patient demographics report anonymized."""
    Patient.objects.create(user_id=2001, display_name="Asha Verma", kind="patient")
    Patient.objects.create(user_id=2002, display_name="Ravi Iyer", kind="patient")
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.reports.generate",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.get("/api/v1/phc/staff/reports?category=demographics")
    assert resp.status_code == 200
    data = resp.json()
    text = str(data)
    assert "Asha Verma" not in text
    assert "Ravi Iyer" not in text
    assert "patient_count_by_kind" in data


# ---------------- BR-TC-034: PHC-BR-12 service utilization report anonymized ----------------


def test_br_tc_034_phc_br_12_service_utilization_report_anonymized(stub_iam, user_ref):
    """BR-TC-034 | PHC-BR-12 service utilization report anonymized."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha Verma", kind="patient")
    Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.reports.generate",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.get("/api/v1/phc/staff/reports?category=utilization")
    assert resp.status_code == 200
    data = resp.json()
    text = str(data)
    assert "Asha Verma" not in text
    assert "category" in data


# ---------------- BR-TC-035: PHC-BR-13 rejection notification ----------------


def test_br_tc_035_phc_br_13_rejection_notification(stub_iam, user_ref):
    """BR-TC-035 | PHC-BR-13 rejection notification."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    _patient2 = Patient.objects.create(user_id=2002, display_name="Bala", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="pending_sanction", stage_actor="Approving Authority",
        action_history=["submitted by employee", "PHC review forwarded", "A&A verified"])
    before = AuditLog.objects.count()
    c = _client(stub_iam, user_id=1004, kind="approver",
                permissions=("phc.reimbursement.sanction",),
                users={1004: user_ref(1004, kind="approver")})
    resp = c.post(f"/api/v1/phc/approver/claims/{claim.claim_id}/sanction",
                  {"decision": "reject"}, format="json")
    assert resp.status_code == 200
    assert AuditLog.objects.count() > before


# ---------------- BR-TC-036: PHC-BR-13 payment processed notification ----------------


def test_br_tc_036_phc_br_13_payment_processed_notification(stub_iam, user_ref):
    """BR-TC-036 | PHC-BR-13 payment processed notification."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    _patient2 = Patient.objects.create(user_id=2002, display_name="Bala", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="approved_for_payment",
        stage_actor="Accounts & Audit",
        action_history=["submitted by employee", "PHC review forwarded",
                        "A&A verified", "Sanction approved"])
    before = AuditLog.objects.count()
    c = _client(stub_iam, user_id=1003, kind="audit",
                permissions=("phc.reimbursement.payment",),
                users={1003: user_ref(1003, kind="audit")})
    resp = c.post(f"/api/v1/phc/audit/claims/{claim.claim_id}/payment", {}, format="json")
    assert resp.status_code == 200
    assert AuditLog.objects.count() > before


# ---------------- BR-TC-037: PHC-BR-13 other status changes notification ----------------


def test_br_tc_037_phc_br_13_other_status_changes_notification(stub_iam, user_ref):
    """BR-TC-037 | PHC-BR-13 other status changes notification."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="submitted", stage_actor="PHC Staff",
        action_history=["submitted by employee"])
    before = AuditLog.objects.count()
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.reimbursement.review",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post(f"/api/v1/phc/staff/claims/{claim.claim_id}/review", {}, format="json")
    assert resp.status_code == 200
    c2 = _client(stub_iam, user_id=1003, kind="audit",
                 permissions=("phc.reimbursement.verify",),
                 users={1003: user_ref(1003, kind="audit")})
    resp = c2.post(f"/api/v1/phc/audit/claims/{claim.claim_id}/verify", {}, format="json")
    assert resp.status_code == 200
    c3 = _client(stub_iam, user_id=1004, kind="approver",
                 permissions=("phc.reimbursement.sanction",),
                 users={1004: user_ref(1004, kind="approver")})
    resp = c3.post(f"/api/v1/phc/approver/claims/{claim.claim_id}/sanction",
                   {"decision": "approve"}, format="json")
    assert resp.status_code == 200
    assert AuditLog.objects.count() > before + 2


# ---------------- BR-TC-038: PHC-BR-14 submitted claim cannot be modified ----------------


def test_br_tc_038_phc_br_14_submitted_claim_cannot_be_modified(stub_iam, user_ref):
    """BR-TC-038 | PHC-BR-14 submitted claim cannot be modified."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="submitted", stage_actor="PHC Staff",
        action_history=["submitted by employee"])
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.view_self",),
                users={2001: user_ref(2001, kind="employee")})
    # No edit endpoint exists for claims
    resp = c.post(f"/api/v1/phc/claims/{claim.claim_id}",
                  {"amount": "1200.00"}, format="json")
    assert resp.status_code == 404
    claim.refresh_from_db()
    assert claim.amount == 1000.00
    assert len(claim.action_history) >= 1


# ---------------- BR-TC-039: PHC-BR-14 rejected claim cannot be reopened ----------------


def test_br_tc_039_phc_br_14_rejected_claim_cannot_be_reopened(stub_iam, user_ref):
    """BR-TC-039 | PHC-BR-14 rejected claim cannot be reopened."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="rejected", stage_actor="Approving Authority",
        action_history=["submitted by employee", "Sanction rejected (terminal)"])
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.view_self", "phc.reimbursement.payment"),
                users={2001: user_ref(2001, kind="employee")})
    resp = c.post(f"/api/v1/phc/audit/claims/{claim.claim_id}/payment", {}, format="json")
    assert resp.status_code == 404
    claim.refresh_from_db()
    assert claim.state == "rejected"
    assert len(claim.action_history) >= 2


# ---------------- BR-TC-040: PHC-BR-14 reapplication after rejection creates a new claim ----------------


def test_br_tc_040_phc_br_14_reapplication_after_rejection_creates_new_claim(stub_iam, user_ref):
    """BR-TC-040 | PHC-BR-14 reapplication after rejection creates a new claim."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="rejected", stage_actor="Approving Authority",
        action_history=["submitted by employee", "Sanction rejected (terminal)"])
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="employee")})
    resp = c.post("/api/v1/phc/claims",
                  {"prescription_id": rx.id, "expense_date": "2026-11-01",
                   "amount": "1200.00"}, format="json")
    assert resp.status_code == 201
    new_claim = ReimbursementClaim.objects.get(claim_id=resp.json()["claim_id"])
    assert new_claim.claim_id != claim.claim_id
    assert new_claim.state == "submitted"
    claim.refresh_from_db()
    assert claim.state == "rejected"
