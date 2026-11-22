from dataclasses import replace
from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import Appointment, Doctor, Patient

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, user_id=1001, permissions=(), kind="student"):
    stub_iam(make_session(user_id=user_id, kind=kind, modules=("phc",), permissions=permissions))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_patient_list_is_limited_to_the_callers_own_record(stub_iam):
    Patient.objects.create(user_id=1001, patient_number="PHC-00001001", registered_by=1001)
    Patient.objects.create(user_id=2002, patient_number="PHC-00002002", registered_by=2002)
    response = _client(stub_iam, permissions=("phc.patient.view_self",)).get("/api/v1/phc/patients")
    assert response.status_code == 200
    assert [row["user_id"] for row in response.json()["results"]] == [1001]


def test_foreign_appointment_transition_is_hidden(stub_iam):
    patient = Patient.objects.create(
        user_id=2002, patient_number="PHC-00002002", registered_by=2002
    )
    doctor = Doctor.objects.create(user_id=3003)
    appt = Appointment.objects.create(
        patient=patient, doctor=doctor, starts_at=datetime(2035, 1, 1, 10, 0, tzinfo=UTC)
    )
    response = _client(
        stub_iam, permissions=("phc.appointment.book", "phc.appointment.view_self")
    ).post(f"/api/v1/phc/appointments/{appt.pk}/transition", {"status": "cancelled"})
    assert response.status_code == 404


def test_unauthenticated_appointments_are_rejected():
    response = APIClient().get("/api/v1/phc/appointments")
    assert response.status_code == 401


def test_patient_can_register_once_and_duplicate_is_a_conflict(stub_iam, user_ref):
    permissions = ("phc.patient.register_self",)
    stub_iam(
        make_session(user_id=1001, modules=("phc",), permissions=permissions),
        users={1001: user_ref(1001)},
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    first = client.post("/api/v1/phc/patients", {}, format="json")
    second = client.post("/api/v1/phc/patients", {}, format="json")
    assert first.status_code == 201
    assert second.status_code == 409


def test_inactive_identity_cannot_be_registered(stub_iam, user_ref):
    inactive = replace(user_ref(1001), is_active=False)
    stub_iam(
        make_session(user_id=1001, modules=("phc",), permissions=("phc.patient.register_self",)),
        users={1001: inactive},
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    response = client.post("/api/v1/phc/patients", {}, format="json")
    assert response.status_code == 400


def test_user_without_clinical_permission_cannot_create_consultation(stub_iam):
    patient = Patient.objects.create(
        user_id=2002, patient_number="PHC-00002002", registered_by=2002
    )
    doctor = Doctor.objects.create(user_id=3003)
    appt = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        starts_at=datetime(2035, 1, 1, 10, 0, tzinfo=UTC),
        status="confirmed",
    )
    response = _client(stub_iam, user_id=9999, permissions=()).post(
        f"/api/v1/phc/appointments/{appt.pk}/consultation",
        {"symptoms": "Example", "diagnosis": "Example"},
        format="json",
    )
    assert response.status_code == 403
