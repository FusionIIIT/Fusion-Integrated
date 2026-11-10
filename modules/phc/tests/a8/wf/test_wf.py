"""WF strategy tests — Specification-Driven AI-Assisted Testing (Assignment 8).

Generated from the frozen WF_DESIGN.json (root). One test function per design
test case; each test_id and source_id is preserved in the function name/docstring.
Production code is NOT modified.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import (
    AuditLog,
    InventoryItem,
    Patient,
    Prescription,
    ReimbursementClaim,
    Requisition,
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


# ---------------- WF-TC-001: BW-PHC-01 approved-and-reimbursed path ----------------


def test_wf_tc_001_bw_phc_01_approved_and_reimbursed(stub_iam, user_ref):
    """WF-TC-001 | BW-PHC-01 approved-and-reimbursed path | Full reimbursement workflow with audit + notification side effects."""
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
    assert resp.json()["state"] == "pending_audit"
    c2 = _client(stub_iam, user_id=1003, kind="audit",
                 permissions=("phc.reimbursement.verify",),
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
    assert AuditLog.objects.count() > before + 3


# ---------------- WF-TC-002: BW-PHC-02 rejected-at-sanction path ----------------


def test_wf_tc_002_bw_phc_02_rejected_at_sanction(stub_iam, user_ref):
    """WF-TC-002 | BW-PHC-02 rejected-at-sanction path | Approving Authority Reject moves claim from Pending Sanction to Rejected."""
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
                 permissions=("phc.reimbursement.verify",),
                 users={1003: user_ref(1003, kind="audit")})
    resp = c2.post(f"/api/v1/phc/audit/claims/{claim.claim_id}/verify", {}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "pending_sanction"
    c3 = _client(stub_iam, user_id=1004, kind="approver",
                 permissions=("phc.reimbursement.sanction",),
                 users={1004: user_ref(1004, kind="approver")})
    resp = c3.post(f"/api/v1/phc/approver/claims/{claim.claim_id}/sanction",
                   {"decision": "reject"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "rejected"
    claim.refresh_from_db()
    assert claim.state == "rejected"


# ---------------- WF-TC-003: BW-PHC-03 approved-and-fulfilled path ----------------


def test_wf_tc_003_bw_phc_03_approved_and_fulfilled(stub_iam, user_ref):
    """WF-TC-003 | BW-PHC-03 approved-and-fulfilled path | Requisition submission -> approval -> fulfillment."""
    item = InventoryItem.objects.create(name="Gloves", unit="boxes", quantity=40,
                                        reorder_threshold=5)
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    _patient2 = Patient.objects.create(user_id=2002, display_name="Bala", kind="staff")
    c = _client(stub_iam, user_id=2001, kind="staff",
                permissions=("phc.inventory.requisition.submit",),
                users={2001: user_ref(2001, kind="staff")})
    resp = c.post("/api/v1/phc/staff/requisitions",
                  {"items": [{"item_id": item.id, "quantity": 100}]}, format="json")
    assert resp.status_code == 201
    assert resp.json()["state"] == "pending_approval"
    req_id = resp.json()["requisition_id"]
    c2 = _client(stub_iam, user_id=1004, kind="approver",
                 permissions=("phc.inventory.requisition.decide",),
                 users={1004: user_ref(1004, kind="approver")})
    resp = c2.post(f"/api/v1/phc/approver/requisitions/{req_id}/decide",
                   {"decision": "approve"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved"
    c3 = _client(stub_iam, user_id=2001, kind="staff",
                 permissions=("phc.inventory.requisition.fulfill",),
                 users={2001: user_ref(2001, kind="staff")})
    resp = c3.post(f"/api/v1/phc/staff/requisitions/{req_id}/fulfill",
                   {}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "fulfilled"
    item.refresh_from_db()
    assert item.quantity == 40


# ---------------- WF-TC-004: BW-PHC-04 rejected path ----------------


def test_wf_tc_004_bw_phc_04_rejected_path(stub_iam, user_ref):
    """WF-TC-004 | BW-PHC-04 rejected path | Reject moves requisition from Pending Approval to Rejected."""
    item = InventoryItem.objects.create(name="Gloves", unit="boxes", quantity=10,
                                        reorder_threshold=5)
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    _patient2 = Patient.objects.create(user_id=2002, display_name="Bala", kind="staff")
    c = _client(stub_iam, user_id=2001, kind="staff",
                permissions=("phc.inventory.requisition.submit",),
                users={2001: user_ref(2001, kind="staff")})
    resp = c.post("/api/v1/phc/staff/requisitions",
                  {"items": [{"item_id": item.id, "quantity": 100}]}, format="json")
    assert resp.status_code == 201
    assert resp.json()["state"] == "pending_approval"
    req_id = resp.json()["requisition_id"]
    c2 = _client(stub_iam, user_id=1004, kind="approver",
                 permissions=("phc.inventory.requisition.decide",),
                 users={1004: user_ref(1004, kind="approver")})
    resp = c2.post(f"/api/v1/phc/approver/requisitions/{req_id}/decide",
                   {"decision": "reject"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "rejected"


# ---------------- WF-TC-005: BW-PHC-01 step 1 guard not satisfied ----------------


def test_wf_tc_005_bw_phc_01_step1_guard_not_satisfied(stub_iam, user_ref):
    """WF-TC-005 | BW-PHC-01 step 1 guard not satisfied | Entry transition fires only when guard satisfied."""
    patient_student = Patient.objects.create(user_id=2001, display_name="S1", kind="student")
    visit_s = Visit.objects.create(patient=patient_student, user_id=patient_student.user_id, recorded_by=1002, notes="v")
    Prescription.objects.create(visit=visit_s, patient=patient_student,
                                         user_id=patient_student.user_id,
                                 medicine="Paracetamol", recorded_by=1002)
    patient_e1 = Patient.objects.create(user_id=2002, display_name="E1", kind="employee")
    patient_e3 = Patient.objects.create(user_id=2003, display_name="E3", kind="employee")
    visit_e2 = Visit.objects.create(patient=patient_e3, user_id=patient_e3.user_id, recorded_by=1002, notes="v2")
    rx_e2 = Prescription.objects.create(visit=visit_e2, patient=patient_e3,
                                         user_id=patient_e3.user_id,
                                        medicine="Drug", recorded_by=1002)
    visit_e1 = Visit.objects.create(patient=patient_e1, user_id=patient_e1.user_id, recorded_by=1002, notes="v3")
    rx_e1 = Prescription.objects.create(visit=visit_e1, patient=patient_e1,
                                         user_id=patient_e1.user_id,
                                        medicine="Paracetamol", recorded_by=1002)
    before = ReimbursementClaim.objects.count()
    # (a) student submits
    c1 = _client(stub_iam, user_id=2001, kind="student",
                 permissions=("phc.reimbursement.submit",),
                 users={2001: user_ref(2001, kind="student")})
    resp = c1.post("/api/v1/phc/claims",
                   {"prescription_id": 1, "expense_date": "2026-11-01",
                    "amount": "1000.00"}, format="json")
    assert resp.status_code == 400
    # (b) employee submits with another's prescription
    c2 = _client(stub_iam, user_id=2002, kind="employee",
                 permissions=("phc.reimbursement.submit",),
                 users={2002: user_ref(2002, kind="employee"),
                        2003: user_ref(2003, kind="employee")})
    resp = c2.post("/api/v1/phc/claims",
                   {"prescription_id": rx_e2.id, "expense_date": "2026-11-01",
                    "amount": "1000.00"}, format="json")
    assert resp.status_code == 400
    # (c) employee submits with out-of-window expense date
    resp = c2.post("/api/v1/phc/claims",
                   {"prescription_id": rx_e1.id, "expense_date": "2020-01-01",
                    "amount": "1000.00"}, format="json")
    assert resp.status_code == 400
    assert ReimbursementClaim.objects.count() == before


# ---------------- WF-TC-006: BW-PHC-03 step 1 guard not satisfied ----------------


def test_wf_tc_006_bw_phc_03_step1_guard_not_satisfied(stub_iam, user_ref):
    """WF-TC-006 | BW-PHC-03 step 1 guard not satisfied | Invalid requisition submission does not enter Pending Approval."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    before = Requisition.objects.filter(state="pending_approval").count()
    c = _client(stub_iam, user_id=2001, kind="staff",
                permissions=("phc.inventory.requisition.submit",),
                users={2001: user_ref(2001, kind="staff")})
    resp = c.post("/api/v1/phc/staff/requisitions", {"items": []}, format="json")
    assert resp.status_code == 400
    assert Requisition.objects.filter(state="pending_approval").count() == before


# ---------------- WF-TC-007: BW-PHC-02 step 4 Rejected is terminal ----------------


def test_wf_tc_007_bw_phc_02_rejected_terminal(stub_iam, user_ref):
    """WF-TC-007 | BW-PHC-02 step 4 Rejected is terminal | No transition leaves Rejected state."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="rejected", stage_actor="Approving Authority",
        action_history=["submitted by employee", "PHC review forwarded",
                        "A&A verified", "Sanction rejected (terminal)"])
    before_count = AuditLog.objects.count()
    before_history = len(claim.action_history)
    c_audit = _client(stub_iam, user_id=1003, kind="audit",
                      permissions=("phc.reimbursement.payment",),
                      users={1003: user_ref(1003, kind="audit")})
    resp = c_audit.post(f"/api/v1/phc/audit/claims/{claim.claim_id}/payment", {}, format="json")
    assert resp.status_code == 404
    c_approver = _client(stub_iam, user_id=1004, kind="approver",
                         permissions=("phc.reimbursement.sanction",),
                         users={1004: user_ref(1004, kind="approver")})
    resp = c_approver.post(f"/api/v1/phc/approver/claims/{claim.claim_id}/sanction",
                           {"decision": "approve"}, format="json")
    assert resp.status_code == 404
    c_staff = _client(stub_iam, user_id=1002, kind="staff",
                      permissions=("phc.reimbursement.review",),
                      users={1002: user_ref(1002, kind="staff")})
    resp = c_staff.post(f"/api/v1/phc/staff/claims/{claim.claim_id}/review", {}, format="json")
    assert resp.status_code == 404
    claim.refresh_from_db()
    assert claim.state == "rejected"
    assert len(claim.action_history) == before_history
    assert AuditLog.objects.count() == before_count


# ---------------- WF-TC-008: BW-PHC-02 step 4 / CW-PHC-01 step 4B reapplication after rejection ----------------


def test_wf_tc_008_bw_phc_02_reapplication_after_rejection(stub_iam, user_ref):
    """WF-TC-008 | BW-PHC-02 step 4 / CW-PHC-01 step 4B | Reapplication after rejection starts new claim instance."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="rejected", stage_actor="Approving Authority",
        action_history=["submitted by employee", "Sanction rejected (terminal)"])
    before_count = ReimbursementClaim.objects.filter(employee=patient).count()
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
    assert ReimbursementClaim.objects.filter(employee=patient).count() == before_count + 1


# ---------------- WF-TC-009: BW-PHC-01 steps 2-5 from-state sequencing ----------------


def test_wf_tc_009_bw_phc_01_from_state_sequencing(stub_iam, user_ref):
    """WF-TC-009 | BW-PHC-01 steps 2-5 from-state sequencing | Later transition cannot be applied to claim in earlier state."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=patient.user_id, recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=patient.user_id, medicine="Paracetamol",
                                     recorded_by=1002)
    claim = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="1000.00", state="submitted", stage_actor="PHC Staff",
        action_history=["submitted by employee"])
    before_count = AuditLog.objects.count()
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
    c_audit = _client(stub_iam, user_id=1003, kind="audit",
                      permissions=("phc.reimbursement.verify", "phc.reimbursement.payment"),
                      users={1003: user_ref(1003, kind="audit")})
    resp = c_audit.post(f"/api/v1/phc/audit/claims/{claim.claim_id}/payment", {}, format="json")
    assert resp.status_code == 404
    claim.refresh_from_db()
    assert claim.state == "submitted"
    assert AuditLog.objects.count() == before_count


# ---------------- WF-TC-010: BW-PHC-01 steps 2-5 actor column ----------------


def test_wf_tc_010_bw_phc_01_actor_column(stub_iam, user_ref):
    """WF-TC-010 | BW-PHC-01 steps 2-5 actor column | Each transition performed only by its defined actor."""
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
    claim_c6 = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="3000.00", state="pending_sanction", stage_actor="Approving Authority",
        action_history=["submitted by employee", "PHC review forwarded", "A&A verified"])
    claim_c7 = ReimbursementClaim.objects.create(
        employee=patient, user_id=patient.user_id, prescription=rx, expense_date="2026-11-01",
        amount="4000.00", state="approved_for_payment", stage_actor="Accounts & Audit",
        action_history=["submitted by employee", "PHC review forwarded",
                        "A&A verified", "Sanction approved"])
    before_count = AuditLog.objects.count()
    # Accounts & Audit forwards C4 (step 2 - wrong actor)
    c_audit = _client(stub_iam, user_id=1003, kind="audit",
                      permissions=(),
                      users={1003: user_ref(1003, kind="audit")})
    resp = c_audit.post(f"/api/v1/phc/staff/claims/{claim_c4.claim_id}/review", {}, format="json")
    assert resp.status_code in (403, 404)
    # PHC Staff verifies C5 (step 3 - wrong actor)
    c_staff = _client(stub_iam, user_id=1002, kind="staff",
                      permissions=(),
                      users={1002: user_ref(1002, kind="staff")})
    resp = c_staff.post(f"/api/v1/phc/audit/claims/{claim_c5.claim_id}/verify", {}, format="json")
    assert resp.status_code in (403, 404)
    # PHC Staff selects Approve on C6 (step 4 - wrong actor)
    resp = c_staff.post(f"/api/v1/phc/approver/claims/{claim_c6.claim_id}/sanction",
                        {"decision": "approve"}, format="json")
    assert resp.status_code in (403, 404)
    # Approving Authority processes payment of C7 (step 5 - wrong actor)
    c_approver = _client(stub_iam, user_id=1004, kind="approver",
                         permissions=(),
                         users={1004: user_ref(1004, kind="approver")})
    resp = c_approver.post(f"/api/v1/phc/audit/claims/{claim_c7.claim_id}/payment", {}, format="json")
    assert resp.status_code in (403, 404)
    claim_c4.refresh_from_db()
    claim_c5.refresh_from_db()
    claim_c6.refresh_from_db()
    claim_c7.refresh_from_db()
    assert claim_c4.state == "submitted"
    assert claim_c5.state == "pending_audit"
    assert claim_c6.state == "pending_sanction"
    assert claim_c7.state == "approved_for_payment"
    assert AuditLog.objects.count() == before_count


# ---------------- WF-TC-011: BW-PHC-03 step 2 / BW-PHC-04 step 2 actor column ----------------


def test_wf_tc_011_bw_phc_03_04_step2_actor_column(stub_iam, user_ref):
    """WF-TC-011 | BW-PHC-03 step 2 / BW-PHC-04 step 2 actor column | Approve/Reject decision only by Approving Authority."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    req = Requisition.objects.create(originator=patient, user_id=patient.user_id, state="pending_approval")
    before_count = AuditLog.objects.count()
    # PHC Staff S1 attempts to Approve R3
    c_staff = _client(stub_iam, user_id=2001, kind="staff",
                      permissions=(),
                      users={2001: user_ref(2001, kind="staff")})
    resp = c_staff.post(f"/api/v1/phc/approver/requisitions/{req.requisition_id}/decide",
                        {"decision": "approve"}, format="json")
    assert resp.status_code in (403, 404)
    # Accounts & Audit user attempts to Reject R3
    c_audit = _client(stub_iam, user_id=1003, kind="audit",
                      permissions=(),
                      users={1003: user_ref(1003, kind="audit")})
    resp = c_audit.post(f"/api/v1/phc/approver/requisitions/{req.requisition_id}/decide",
                        {"decision": "reject"}, format="json")
    assert resp.status_code in (403, 404)
    req.refresh_from_db()
    assert req.state == "pending_approval"
    assert AuditLog.objects.count() == before_count


# ---------------- WF-TC-012: BW-PHC-03 step 3 from-state Approved ----------------


def test_wf_tc_012_bw_phc_03_step3_from_state_approved(stub_iam, user_ref):
    """WF-TC-012 | BW-PHC-03 step 3 from-state Approved | Approved to Fulfilled fires only from Approved."""
    patient = Patient.objects.create(user_id=2001, display_name="Asha", kind="staff")
    req_pending = Requisition.objects.create(originator=patient, user_id=patient.user_id, state="pending_approval")
    req_rejected = Requisition.objects.create(originator=patient, user_id=patient.user_id, state="rejected")
    c = _client(stub_iam, user_id=2001, kind="staff",
                permissions=("phc.inventory.requisition.fulfill",),
                users={2001: user_ref(2001, kind="staff")})
    resp = c.post(f"/api/v1/phc/staff/requisitions/{req_pending.requisition_id}/fulfill",
                  {}, format="json")
    assert resp.status_code == 404
    resp = c.post(f"/api/v1/phc/staff/requisitions/{req_rejected.requisition_id}/fulfill",
                  {}, format="json")
    assert resp.status_code == 404
    req_pending.refresh_from_db()
    req_rejected.refresh_from_db()
    assert req_pending.state == "pending_approval"
    assert req_rejected.state == "rejected"
