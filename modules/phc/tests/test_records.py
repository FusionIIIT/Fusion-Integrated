from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.phc.models import PatientVisit, PHCAuditEvent, Prescription

pytestmark = pytest.mark.django_db


def _client(stub_iam, user_id, role, permissions, kind="staff"):
    stub_iam(make_session(user_id=user_id, kind=kind, modules=("phc",),
                          permissions=permissions, roles=(role,), active_role=role))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token phc-records")
    return client


# PHC-BR-02; PHC-BR-09; PHC-UC-06; CFR-PHC-002; AFR-PHC-007; AFR-PHC-008; AFR-PHC-037.
def test_phc_br_02_br_09_uc_06_records_visit_prescription_and_audit_atomically(stub_iam):
    UserRef.objects.create(user_id=1001, username="patient", display_name="Patient",
                           kind="faculty")
    compounder = _client(stub_iam, 2001, "Compounder", ["phc.patient_record.create"])

    response = compounder.post("/api/v1/phc/visits", {
        "patient_user_id": 1001,
        "visited_on": date.today().isoformat(),
        "notes": "Clinical remarks",
        "prescription_details": "Medicine and dosage instructions",
        "issued_on": date.today().isoformat(),
    }, format="json")

    assert response.status_code == 201
    visit_id = response.json()["id"]
    assert response.json()["prescriptions"][0]["details"] == "Medicine and dosage instructions"
    assert PatientVisit.objects.count() == 1
    assert Prescription.objects.filter(visit_id=visit_id).count() == 1
    assert PHCAuditEvent.objects.filter(object_type__in=(
        "patient_visit", "prescription")).count() == 2

    patient = _client(stub_iam, 1001, "faculty", ["phc.patient_record.view"], "faculty")
    own_record = patient.get("/api/v1/phc/records")
    assert [row["id"] for row in own_record.json()["results"]] == [visit_id]


# PHC-BR-02; PHC-UC-06; CFR-PHC-002; AFR-PHC-006.
def test_phc_uc_06_searches_only_directory_matches_with_bounded_query(stub_iam):
    UserRef.objects.create(user_id=1001, username="alpha", display_name="Alpha Person",
                           kind="staff")
    client = _client(stub_iam, 2001, "Compounder", ["phc.patient_record.create"])
    found = client.get("/api/v1/phc/directory/patients?q=Alpha")
    assert found.status_code == 200
    assert [row["user_id"] for row in found.json()] == [1001]
    too_long = client.get(f"/api/v1/phc/directory/patients?q={'x' * 81}")
    assert too_long.status_code == 400


# PHC-BR-02; PHC-UC-03; CFR-PHC-002; AFR-PHC-011; AFR-PHC-012.
def test_phc_uc_03_patient_exports_only_selected_visits_from_own_history(stub_iam):
    from modules.phc.models import PatientVisit

    own = PatientVisit.objects.create(
        patient_user_id=1001, visited_on=date(2026, 2, 1),
        notes="Clinical note & follow-up", recorded_by_user_id=2001,
    )
    late = PatientVisit.objects.create(
        patient_user_id=1001, visited_on=date(2026, 3, 1),
        notes="Later visit", recorded_by_user_id=2001,
    )
    Prescription.objects.create(
        visit=own, details="Medicine and dosage", issued_on=date(2026, 2, 1),
        issued_by_user_id=2001,
    )
    other = PatientVisit.objects.create(
        patient_user_id=1002, visited_on=date(2026, 1, 1),
        notes="Other patient's note", recorded_by_user_id=2001,
    )
    client = _client(stub_iam, 1001, "student", ["phc.record.export"], "student")
    exported = client.post("/api/v1/phc/records/pdf", {
        "visit_ids": [late.pk, own.pk],
    }, format="json")
    assert exported.status_code == 200
    assert exported["Content-Type"] == "application/pdf"
    assert exported["Content-Disposition"] == 'attachment; filename="medical-records.pdf"'
    assert exported.content.startswith(b"%PDF-")
    assert b"Patient identifier: 1001" in exported.content
    assert b"Clinical note & follow-up" in exported.content
    assert b"Medicine and dosage" in exported.content
    assert exported.content.index(b"Visit date: 2026-02-01") < exported.content.index(
        b"Visit date: 2026-03-01")
    refused = client.post("/api/v1/phc/records/pdf", {
        "visit_ids": [own.pk, other.pk],
    }, format="json")
    assert refused.status_code == 404
    duplicate = client.post("/api/v1/phc/records/pdf", {
        "visit_ids": [own.pk, own.pk],
    }, format="json")
    assert duplicate.status_code == 400


# PHC-UC-03; CFR-PHC-002; AFR-PHC-011.
def test_phc_uc_03_pdf_embeds_unicode_font_for_non_latin_clinical_text(stub_iam):
    visit = PatientVisit.objects.create(
        patient_user_id=1001, visited_on=date(2026, 5, 3),
        notes="दवा और उपचार", recorded_by_user_id=2001,
    )
    Prescription.objects.create(
        visit=visit, details="सुबह एक गोली लें", issued_on=date(2026, 5, 3),
        issued_by_user_id=2001,
    )
    client = _client(stub_iam, 1001, "student", ["phc.record.export"], "student")
    response = client.post("/api/v1/phc/records/pdf", {"visit_ids": [visit.pk]},
                           format="json")
    assert response.status_code == 200
    assert b"/ToUnicode" in response.content
    assert b"/FontFile2" in response.content
