from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.phc.models import (
    NotificationOutbox,
    PatientVisit,
    PHCAuditEvent,
    Prescription,
    ReimbursementAction,
    ReimbursementPolicy,
)

pytestmark = pytest.mark.django_db


def _as(stub_iam, user_id, role, permissions, kind="staff"):
    stub_iam(make_session(user_id=user_id, kind=kind, modules=("phc",),
                          permissions=permissions, roles=(role,), active_role=role))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token phc-journey")
    return client


def _employee(user_id):
    UserRef.objects.create(user_id=user_id, username=f"phc{user_id}",
                           display_name=f"Employee {user_id}", kind="faculty")


# PHC-BR-08; PHC-BR-13; PHC-UC-04; PHC-UC-05; PHC-UC-15; PHC-UC-19; PHC-UC-20; PHC-UC-21; BW-PHC-01; CW-PHC-01; CFR-PHC-004; CFR-PHC-005; AFR-PHC-017; AFR-PHC-018; AFR-PHC-019; AFR-PHC-020; AFR-PHC-021; AFR-PHC-022; AFR-PHC-023.
def test_phc_br_13_uc_04_uc_05_uc_15_uc_19_uc_20_uc_21_bw_phc_01_cw_phc_01_claim_journey(
        stub_iam):
    _employee(1001)
    visit = PatientVisit.objects.create(
        patient_user_id=1001, visited_on=date.today(), notes="Consultation",
        recorded_by_user_id=2001)
    prescription = Prescription.objects.create(
        visit=visit, details="Prescribed treatment", issued_on=date.today(),
        issued_by_user_id=2001)
    assert ReimbursementPolicy.objects.filter(
        effective_period__contains=date.today(), submission_window_days=30).exists()
    employee = _as(stub_iam, 1001, "faculty", [
        "phc.reimbursement.create", "phc.reimbursement.view", "phc.patient_record.view",
    ], kind="faculty")
    submitted = employee.post("/api/v1/phc/reimbursements", {
        "prescription_id": prescription.pk,
        "claim_amount": "1200.00",
        "expense_date": date.today().isoformat(),
        "bill_reference": "TEST-BILL",
        "remarks": "Consultation charge",
    }, format="json")
    assert submitted.status_code == 201
    claim_id = submitted.json()["id"]
    assert submitted.json()["state"] == "pending_phc_review"
    assert employee.get("/api/v1/phc/reimbursements").json()["results"][0]["id"] == claim_id
    assert NotificationOutbox.objects.filter(
        event_key=f"claim:{claim_id}:pending_phc_review").exists()

    phc = _as(stub_iam, 2001, "Compounder", [
        "phc.reimbursement.view", "phc.reimbursement.review",
    ])
    assert phc.post(f"/api/v1/phc/reimbursements/{claim_id}/review", {},
                    format="json").json()["state"] == "pending_accounts_verification"
    accounts = _as(stub_iam, 3001, "Accounts Admin", [
        "phc.reimbursement.view", "phc.reimbursement.manage",
    ])
    assert accounts.post(f"/api/v1/phc/reimbursements/{claim_id}/verification", {},
                         format="json").json()["state"] == "pending_sanction"
    registrar = _as(stub_iam, 4001, "Registrar", [
        "phc.reimbursement.view", "phc.reimbursement.approve",
    ])
    assert registrar.post(f"/api/v1/phc/reimbursements/{claim_id}/sanction",
                          {"decision": "approve"}, format="json").json()["state"] == "approved_for_payment"
    accounts = _as(stub_iam, 3001, "Accounts Admin", [
        "phc.reimbursement.view", "phc.reimbursement.manage",
    ])
    payment = accounts.post(f"/api/v1/phc/reimbursements/{claim_id}/payment", {},
                            format="json")
    assert payment.status_code == 200, payment.content
    assert payment.json()["state"] == "reimbursed"
    assert ReimbursementAction.objects.filter(claim_id=claim_id).count() == 5
    assert PHCAuditEvent.objects.filter(object_id=claim_id,
                                        object_type="reimbursement_claim").count() == 5
    assert NotificationOutbox.objects.filter(
        event_key__startswith=f"claim:{claim_id}:").count() == 5


# PHC-BR-04; PHC-BR-05; PHC-BR-06; PHC-UC-04; CFR-PHC-003; AFR-PHC-013; AFR-PHC-014; AFR-PHC-015.
def test_phc_br_04_br_05_br_06_uc_04_rejects_student_late_expense_and_foreign_rx(
        stub_iam):
    UserRef.objects.create(user_id=1001, username="student",
                           display_name="Student", kind="student")
    _employee(1002)
    own_visit = PatientVisit.objects.create(patient_user_id=1002,
        visited_on=date.today(), notes="Own visit", recorded_by_user_id=2001)
    own_rx = Prescription.objects.create(visit=own_visit, details="Medicine",
        issued_on=date.today(), issued_by_user_id=2001)
    other_visit = PatientVisit.objects.create(patient_user_id=1003,
        visited_on=date.today(), notes="Other visit", recorded_by_user_id=2001)
    other_rx = Prescription.objects.create(visit=other_visit, details="Medicine",
        issued_on=date.today(), issued_by_user_id=2001)
    client = _as(stub_iam, 1001, "student", [
        "phc.reimbursement.create", "phc.reimbursement.view",
    ], kind="student")
    base = {"claim_amount": "50.00", "expense_date": date.today().isoformat()}
    assert client.post("/api/v1/phc/reimbursements", {
        **base, "prescription_id": own_rx.pk,
    }, format="json").status_code == 409
    faculty = _as(stub_iam, 1002, "faculty", [
        "phc.reimbursement.create", "phc.reimbursement.view",
    ], kind="faculty")
    expired = date.today() - timedelta(days=31)
    assert faculty.post("/api/v1/phc/reimbursements", {
        **base, "prescription_id": own_rx.pk,
        "expense_date": expired.isoformat(),
    }, format="json").status_code == 400
    assert faculty.post("/api/v1/phc/reimbursements", {
        **base, "prescription_id": other_rx.pk,
    }, format="json").status_code == 404


# PHC-BR-13; PHC-BR-14; PHC-UC-20; BW-PHC-02; CFR-PHC-004; AFR-PHC-020; AFR-PHC-023; AFR-PHC-038.
def test_phc_br_13_br_14_uc_20_bw_phc_02_rejection_is_terminal_and_reapplication_is_new(
        stub_iam):
    _employee(1101)
    visit = PatientVisit.objects.create(patient_user_id=1101,
        visited_on=date.today(), notes="Consultation", recorded_by_user_id=2001)
    prescription = Prescription.objects.create(visit=visit, details="Treatment",
        issued_on=date.today(), issued_by_user_id=2001)
    employee = _as(stub_iam, 1101, "faculty", ["phc.reimbursement.create"] , "faculty")
    submitted = employee.post("/api/v1/phc/reimbursements", {
        "prescription_id": prescription.pk, "claim_amount": "75.00",
        "expense_date": date.today().isoformat(),
    }, format="json")
    first_id = submitted.json()["id"]
    phc = _as(stub_iam, 2001, "Compounder", ["phc.reimbursement.review"])
    phc.post(f"/api/v1/phc/reimbursements/{first_id}/review", {}, format="json")
    accounts = _as(stub_iam, 3001, "Accounts Admin", ["phc.reimbursement.manage"])
    accounts.post(f"/api/v1/phc/reimbursements/{first_id}/verification", {}, format="json")
    registrar = _as(stub_iam, 4001, "Registrar", ["phc.reimbursement.approve"])
    rejected = registrar.post(f"/api/v1/phc/reimbursements/{first_id}/sanction",
                              {"decision": "reject"}, format="json")
    assert rejected.json()["state"] == "rejected"
    assert NotificationOutbox.objects.filter(
        event_key=f"claim:{first_id}:rejected").exists()
    assert registrar.post(f"/api/v1/phc/reimbursements/{first_id}/sanction",
                          {"decision": "approve"}, format="json").status_code == 404
    employee = _as(stub_iam, 1101, "faculty", ["phc.reimbursement.create"], "faculty")
    second = employee.post("/api/v1/phc/reimbursements", {
        "prescription_id": prescription.pk, "claim_amount": "75.00",
        "expense_date": date.today().isoformat(),
    }, format="json")
    assert second.status_code == 201
    assert second.json()["id"] != first_id
    assert second.json()["state"] == "pending_phc_review"
