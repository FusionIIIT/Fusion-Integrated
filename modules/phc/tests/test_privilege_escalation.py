import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.registry import MODULE, PERMISSIONS

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, modules, permissions, role="student", user_id=1001,
            roles=None):
    session = make_session(user_id=user_id, kind="student", modules=modules,
                           permissions=permissions, roles=roles or (role,),
                           active_role=role)
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token phc-test")
    return client


# PHC-BR-03; CFR-PHC-011; AFR-PHC-036.
def test_phc_br_03_permission_codes_match_registry():
    declared = {code for code, _ in PERMISSIONS}
    assert declared
    assert all(code.startswith(f"{MODULE['code']}.") for code in declared)
    assert len(declared) == len(PERMISSIONS)


@pytest.mark.parametrize("path,permission", [
    ("doctor-availability", "phc.doctor_schedule.view"),
    ("records", "phc.patient_record.view"),
    ("records/pdf", "phc.record.export"),
    ("reimbursements", "phc.reimbursement.view"),
    ("inventory", "phc.inventory.view"),
    ("requisitions", "phc.requisition.view"),
    ("ambulance-usage", "phc.ambulance_usage.view"),
    ("advisories", "phc.advisory.view"),
    ("notifications", "phc.notification.view"),
])
def test_phc_br_03_module_and_permission_are_independent_gates(
        stub_iam, path, permission):
    no_module = _client(stub_iam, modules=(), permissions=(permission,))

    def request(client):
        if path == "records/pdf":
            return client.post(f"/api/v1/phc/{path}", {"visit_ids": [1]}, format="json")
        return client.get(f"/api/v1/phc/{path}")

    assert request(no_module).status_code == 403
    no_permission = _client(stub_iam, modules=("phc",), permissions=())
    assert request(no_permission).status_code == 403


def test_phc_br_03_unauthenticated_request_is_rejected(stub_iam):
    stub_iam(None)
    response = APIClient().get("/api/v1/phc/records")
    assert response.status_code == 401


def test_phc_br_02_patient_cannot_create_or_view_another_patients_record(
        stub_iam):
    from modules.phc.models import PatientVisit

    own = PatientVisit.objects.create(patient_user_id=1001, visited_on="2026-11-20",
                                      notes="Own", recorded_by_user_id=8)
    PatientVisit.objects.create(patient_user_id=1002, visited_on="2026-11-20",
                                notes="Other", recorded_by_user_id=8)
    client = _client(stub_iam, modules=("phc",),
                     permissions=("phc.patient_record.view",))

    response = client.get("/api/v1/phc/records")

    assert [row["id"] for row in response.json()["results"]] == [own.pk]
    denied = client.post("/api/v1/phc/visits", {}, format="json")
    assert denied.status_code == 403


def test_phc_br_03_role_switch_uses_only_the_active_designation(stub_iam):
    client = _client(stub_iam, modules=("phc",),
                     permissions=("phc.patient_record.view",), role="student",
                     roles=("student", "Compounder"))
    assert client.get("/api/v1/phc/visits").status_code == 403


def test_phc_br_03_write_without_permission_refuses_patient_visit(stub_iam):
    client = _client(stub_iam, modules=("phc",),
                     permissions=("phc.patient_record.view",))
    response = client.post("/api/v1/phc/visits", {}, format="json")
    assert response.status_code == 403


def test_phc_br_03_cookie_write_requires_csrf_header(stub_iam):
    from django.conf import settings

    stub_iam(make_session(user_id=2001, kind="staff", modules=("phc",),
        permissions=("phc.patient_record.create",), roles=("Compounder",),
        active_role="Compounder"))
    client = APIClient()
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = "phc-cookie-session"
    response = client.post("/api/v1/phc/visits", {}, format="json")
    assert response.status_code == 403
    assert "CSRF" in response.json()["error"]["message"]
