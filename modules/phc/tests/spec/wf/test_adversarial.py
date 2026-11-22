"""Adversarial WF checks: conflicts, double-clicks and immutable history."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import (
    AuditLog,
    Patient,
    Prescription,
    ReimbursementClaim,
    Requisition,
    Visit,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, user_id, kind, permissions, users=None):
    stub_iam(make_session(user_id=user_id, kind=kind, roles=(kind,),
                          active_role=kind, permissions=permissions,
                          modules=("phc",)),
             users=users or {})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _claim(state="submitted"):
    patient = Patient.objects.create(user_id=2001, display_name="Asha",
                                     kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=2001,
                                 recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=2001,
                                     medicine="Paracetamol", recorded_by=1002)
    return ReimbursementClaim.objects.create(
        employee=patient, prescription=rx, user_id=2001,
        expense_date=timezone.localdate(), amount="100.00", state=state,
        stage_actor="PHC Staff", action_history=["submitted by employee"])


def test_wf_adv_stale_version_is_409(stub_iam, user_ref):
    claim = _claim()
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.reimbursement.review",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post(f"/api/v1/phc/staff/claims/{claim.pk}/review",
                  {"expected_updated_at": "2000-01-01T00:00:00Z"}, format="json")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"
    assert "already completed" in resp.json()["error"]["message"]
    claim.refresh_from_db()
    assert claim.state == "submitted"


def test_wf_adv_double_click_is_409(stub_iam, user_ref):
    claim = _claim()
    stale = str(claim.updated_at)
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.reimbursement.review",),
                users={1002: user_ref(1002, kind="staff")})
    url = f"/api/v1/phc/staff/claims/{claim.pk}/review"
    assert c.post(url, {"expected_updated_at": stale}, format="json").status_code == 200
    second = c.post(url, {"expected_updated_at": stale}, format="json")
    assert second.status_code == 409
    claim.refresh_from_db()
    assert claim.state == "pending_audit"
    assert AuditLog.objects.filter(action="claim.review", target_id=claim.pk).count() == 1


def test_wf_adv_wrong_stage_is_404_with_next_step_message(stub_iam, user_ref):
    claim = _claim()
    c = _client(stub_iam, user_id=1003, kind="audit",
                permissions=("phc.reimbursement.verify",),
                users={1003: user_ref(1003, kind="audit")})
    resp = c.post(f"/api/v1/phc/audit/claims/{claim.pk}/verify", {}, format="json")
    assert resp.status_code == 404
    assert "earlier stage" in resp.json()["error"]["message"]


def test_wf_adv_rejected_claim_is_immutable(stub_iam, user_ref):
    claim = _claim(state="pending_sanction")
    approver = _client(stub_iam, user_id=1004, kind="approver",
                       permissions=("phc.reimbursement.sanction",),
                       users={1004: user_ref(1004, kind="approver")})
    rejected = approver.post(f"/api/v1/phc/approver/claims/{claim.pk}/sanction",
                             {"decision": "reject", "note": "duplicate"},
                             format="json")
    assert rejected.status_code == 200
    assert rejected.json()["state"] == "rejected"

    payer = _client(stub_iam, user_id=1005, kind="audit",
                    permissions=("phc.reimbursement.payment",),
                    users={1005: user_ref(1005, kind="audit")})
    assert payer.post(f"/api/v1/phc/audit/claims/{claim.pk}/payment", {},
                      format="json").status_code == 404
    claim.refresh_from_db()
    assert claim.state == "rejected"
    assert "Note: duplicate" in claim.action_history
    assert len(claim.action_history) == 3


def test_wf_adv_requisition_double_decision_is_409(stub_iam, user_ref):
    patient = Patient.objects.create(user_id=2001, display_name="Asha",
                                     kind="staff")
    requisition = Requisition.objects.create(originator=patient, user_id=2001,
                                             state="pending_approval")
    stale = str(requisition.updated_at)
    c = _client(stub_iam, user_id=1004, kind="approver",
                permissions=("phc.requisition.decide",),
                users={1004: user_ref(1004, kind="approver")})
    url = f"/api/v1/phc/approver/requisitions/{requisition.pk}/decide"
    assert c.post(url, {"decision": "approve",
                        "expected_updated_at": stale}, format="json").status_code == 200
    assert c.post(url, {"decision": "reject",
                        "expected_updated_at": stale}, format="json").status_code == 409
    requisition.refresh_from_db()
    assert requisition.state == "approved"


def test_wf_adv_record_pdf_has_bytes_and_own_content(stub_iam, user_ref):
    patient = Patient.objects.create(user_id=2001, display_name="Asha",
                                     kind="patient")
    visit = Visit.objects.create(patient=patient, user_id=2001,
                                 recorded_by=1002, notes="reviewed")
    Prescription.objects.create(visit=visit, patient=patient, user_id=2001,
                                medicine="Ibuprofen", recorded_by=1002)
    c = _client(stub_iam, user_id=2001, kind="patient",
                permissions=("phc.records.view_self",),
                users={2001: user_ref(2001, kind="patient")})
    resp = c.get(f"/api/v1/phc/records/download/{visit.pk}")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-1.4")
    assert b"Ibuprofen" in resp.content
    assert b"reviewed" in resp.content
    assert b"%%EOF" in resp.content
