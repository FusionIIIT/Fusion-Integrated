"""Adversarial BR checks: notification side effects, scoping and role switches."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import (
    AuditLog,
    InventoryItem,
    NotificationOutbox,
    Patient,
    Prescription,
    ReimbursementClaim,
    Requisition,
    Visit,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, user_id, kind, permissions, modules=("phc",),
            roles=None, active_role=None, users=None):
    roles = roles or (kind,)
    stub_iam(make_session(user_id=user_id, kind=kind, roles=roles,
                          active_role=active_role or kind,
                          permissions=permissions, modules=modules),
             users=users or {})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _patient_and_prescription(user_id=2001, kind="employee"):
    patient = Patient.objects.create(user_id=user_id, display_name="Asha",
                                     kind=kind)
    visit = Visit.objects.create(patient=patient, user_id=user_id,
                                 recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=user_id,
                                     medicine="Paracetamol", recorded_by=1002)
    return patient, rx


def _claim(user_id=2001, state="submitted"):
    patient, rx = _patient_and_prescription(user_id)
    claim = ReimbursementClaim.objects.create(
        employee=patient, prescription=rx, user_id=user_id,
        expense_date=timezone.localdate(), amount="100.00", state=state,
        stage_actor="PHC Staff", action_history=["submitted by employee"])
    return patient, claim


def test_br_adv_claim_submission_writes_notification_and_audit(stub_iam, user_ref):
    _, rx = _patient_and_prescription()
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="employee")})
    resp = c.post("/api/v1/phc/claims",
                  {"prescription_id": rx.id,
                   "expense_date": timezone.localdate().isoformat(),
                   "amount": "100.00"}, format="json")
    assert resp.status_code == 201
    claim_id = resp.json()["claim_id"]
    notice = NotificationOutbox.objects.get(topic="claim.status_changed")
    assert notice.recipient_user_id == 2001
    assert notice.recipient_role == ""
    assert notice.subject == f"Reimbursement claim {claim_id} submitted"
    assert str(claim_id) in notice.body
    assert "My Reimbursement Claims" in notice.body
    assert notice.payload == {"claim_id": claim_id, "state": "submitted",
                              "action": "submit"}
    assert notice.status == "pending"
    assert AuditLog.objects.filter(action="claim.submit", target_id=claim_id).exists()


def test_br_adv_claim_status_change_notifies_claimant(stub_iam, user_ref):
    patient, claim = _claim()
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.reimbursement.review",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post(f"/api/v1/phc/staff/claims/{claim.pk}/review", {}, format="json")
    assert resp.status_code == 200
    notice = NotificationOutbox.objects.get(topic="claim.status_changed")
    assert notice.recipient_user_id == patient.user_id
    assert notice.subject.endswith("sent for verification")
    assert "verification" in notice.body
    assert notice.payload["state"] == "pending_audit"
    assert notice.payload["action"] == "review"
    assert AuditLog.objects.filter(action="claim.review", target_id=claim.pk).exists()


def test_br_adv_requisition_decision_notifies_originator(stub_iam, user_ref):
    originator = Patient.objects.create(user_id=2001, display_name="Asha",
                                        kind="staff")
    requisition = Requisition.objects.create(originator=originator, user_id=2001,
                                             state="pending_approval")
    c = _client(stub_iam, user_id=1004, kind="approver",
                permissions=("phc.requisition.decide",),
                users={1004: user_ref(1004, kind="approver")})
    resp = c.post(f"/api/v1/phc/approver/requisitions/{requisition.pk}/decide",
                  {"decision": "approve"}, format="json")
    assert resp.status_code == 200
    notice = NotificationOutbox.objects.get(topic="requisition.decided")
    assert notice.recipient_user_id == 2001
    assert notice.subject.endswith("approved")
    assert "Procurement Requisitions" in notice.body
    assert notice.payload == {"requisition_id": requisition.pk,
                              "state": "approved"}
    assert AuditLog.objects.filter(action="requisition.approve",
                                   target_id=requisition.pk).exists()


def test_br_adv_low_stock_notifies_staff_role(stub_iam, user_ref):
    item = InventoryItem.objects.create(name="Gloves", quantity=10,
                                        reorder_threshold=5)
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": 6, "direction": "deduct",
                   "reason": "routine use"}, format="json")
    assert resp.status_code == 201
    notice = NotificationOutbox.objects.get(topic="inventory.low_stock")
    assert notice.recipient_user_id is None
    assert notice.recipient_role == "phc_staff"
    assert notice.subject == "Low stock: Gloves"
    assert "below its reorder threshold of 5" in notice.body
    assert notice.payload == {"item_id": item.id, "quantity": 4}
    assert AuditLog.objects.filter(action="inventory.adjust",
                                   target_id=item.id).exists()


def test_br_adv_patient_cannot_reach_another_patients_record(stub_iam, user_ref):
    b = Patient.objects.create(user_id=2002, display_name="Bala", kind="patient")
    visit_b = Visit.objects.create(patient=b, user_id=2002, recorded_by=1002,
                                   notes="secret")
    c = _client(stub_iam, user_id=2001, kind="patient",
                permissions=("phc.records.view_self",),
                users={2001: user_ref(2001, kind="patient")})
    assert c.get(f"/api/v1/phc/records/download/{visit_b.pk}").status_code == 404


def test_br_adv_patient_cannot_reach_staff_or_audit_routes(stub_iam, user_ref):
    c = _client(stub_iam, user_id=2001, kind="patient",
                permissions=("phc.records.view_self",),
                users={2001: user_ref(2001, kind="patient")})
    assert c.get("/api/v1/phc/audit/log").status_code == 403
    assert c.post("/api/v1/phc/staff/visits",
                  {"patient_id": 2001, "notes": "x"}, format="json").status_code == 403


def test_br_adv_role_switch_changes_capability(stub_iam, user_ref):
    _, claim = _claim(state="pending_sanction")
    staff = _client(stub_iam, user_id=1002, kind="staff",
                    permissions=("phc.reimbursement.review",),
                    roles=("phc_staff", "approver"), active_role="phc_staff",
                    users={1002: user_ref(1002, kind="staff")})
    staff_resp = staff.post(f"/api/v1/phc/staff/claims/{claim.pk}/review", {},
                            format="json")
    assert staff_resp.status_code == 404

    approver = _client(stub_iam, user_id=1002, kind="staff",
                       permissions=("phc.reimbursement.sanction",),
                       roles=("phc_staff", "approver"), active_role="approver",
                       users={1002: user_ref(1002, kind="staff")})
    resp = approver.post(f"/api/v1/phc/approver/claims/{claim.pk}/sanction",
                         {"decision": "approve"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["state"] == "approved_for_payment"

    patient = _client(stub_iam, user_id=1002, kind="staff",
                      permissions=(), roles=("patient",), active_role="patient",
                      users={1002: user_ref(1002, kind="staff")})
    assert patient.get("/api/v1/phc/audit/log").status_code == 403
