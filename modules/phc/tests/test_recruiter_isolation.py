import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import PatientVisit

pytestmark = pytest.mark.django_db


def _patient(stub_iam, user_id):
    stub_iam(make_session(user_id=user_id, kind="student", modules=("phc",),
                          permissions=("phc.patient_record.view",)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token phc-isolation")
    return client


# PHC-BR-02; PHC-UC-02; CFR-PHC-002; AFR-PHC-009; AFR-PHC-010; AFR-PHC-012.
def test_phc_br_02_patient_list_search_and_report_keep_patient_data_scoped(stub_iam):
    own = PatientVisit.objects.create(patient_user_id=1001, visited_on="2026-11-20",
                                      notes="private own note", recorded_by_user_id=9)
    PatientVisit.objects.create(patient_user_id=1002, visited_on="2026-11-21",
                                notes="private other note", recorded_by_user_id=9)
    client = _patient(stub_iam, 1001)

    response = client.get("/api/v1/phc/records")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [own.pk]
    assert "private other note" not in response.content.decode()
    assert client.get("/api/v1/phc/records?search=private%20other").json()["results"] == [
        response.json()["results"][0]
    ]


# PHC-BR-12; PHC-UC-13; CFR-PHC-010; AFR-PHC-034; AFR-PHC-035.
def test_phc_br_12_reports_are_aggregate_and_contain_no_patient_identifiers(stub_iam):
    PatientVisit.objects.create(patient_user_id=903499, visited_on="2026-11-20",
                               notes="distinct clinical note text", recorded_by_user_id=9)
    stub_iam(make_session(user_id=9001, modules=("phc",),
                          permissions=("phc.report.view",), roles=("Compounder",),
                          active_role="Compounder"))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token phc-reports")

    response = client.get("/api/v1/phc/reports/demographics")

    assert response.status_code == 200
    body = response.content.decode()
    assert "903499" not in body
    assert "distinct clinical note text" not in body
    assert set(response.json()["data"]) == {"total", "by_kind"}
