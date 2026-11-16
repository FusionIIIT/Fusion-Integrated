import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import DoctorSchedule, Visit

pytestmark = pytest.mark.django_db

PATIENT = ["health_center.schedule.view", "health_center.record.view_self"]
STAFF = [
    "health_center.schedule.view",
    "health_center.schedule.manage",
    "health_center.record.manage",
]


@pytest.fixture
def client_for(stub_iam):
    def _client(permissions, uid=101):
        session = make_session(
            user_id=uid,
            kind="staff",
            permissions=permissions,
            modules=("health_center",),
            roles=("staff",),
            active_role="staff",
        )
        stub_iam(session=session)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token test-phc")
        return client

    return _client


def test_patient_sees_published_schedules(client_for):
    client = client_for(PATIENT)
    DoctorSchedule.objects.create(
        doctor_name="Dr A",
        day_of_week=0,
        start_time="10:00:00",
        end_time="12:00:00",
        published=True,
    )
    response = client.get("/api/v1/phc/schedules")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


def test_patient_cannot_post_schedule(client_for):
    client = client_for(PATIENT)
    data = {"doctor_name": "Dr B", "day_of_week": 1, "start_time": "10:00", "end_time": "12:00"}
    response = client.post("/api/v1/phc/schedules", data=data)
    assert response.status_code == 403


def test_staff_post_invalid_times(client_for):
    client = client_for(STAFF)
    data = {"doctor_name": "Dr C", "day_of_week": 2, "start_time": "12:00", "end_time": "10:00"}
    response = client.post("/api/v1/phc/schedules", data=data)
    assert response.status_code == 400


def test_presence_on_unpublished_schedule(client_for):
    schedule = DoctorSchedule.objects.create(
        doctor_name="Dr D", day_of_week=3, start_time="10:00", end_time="12:00", published=False
    )
    client = client_for(STAFF)
    response = client.post(f"/api/v1/phc/schedules/{schedule.pk}/presence", {"is_present": True})
    assert response.status_code == 400


def test_publish_then_presence(client_for):
    schedule = DoctorSchedule.objects.create(
        doctor_name="Dr E", day_of_week=4, start_time="10:00", end_time="12:00", published=False
    )
    client = client_for(STAFF)
    response = client.post(f"/api/v1/phc/schedules/{schedule.pk}/publish")
    assert response.status_code == 200
    response = client.post(f"/api/v1/phc/schedules/{schedule.pk}/presence", {"is_present": True})
    assert response.status_code == 200


def test_staff_create_visit(client_for):
    client = client_for(STAFF)
    data = {
        "patient_id": 1,
        "visit_date": "2025-01-01",
        "complaint": "headache",
        "prescriptions": [{"medicine": "Paracetamol", "dosage": "500mg", "duration_days": 3}],
    }
    response = client.post("/api/v1/phc/visits", data=data, format="json")
    assert response.status_code == 201
    visit_data = response.json()
    assert visit_data["recorded_by"] == 101


def test_patient_sees_own_visit(client_for):
    staff = client_for(STAFF, uid=900)
    DoctorSchedule.objects.create(doctor_name="Dr F", day_of_week=0, start_time="10:00", end_time="12:00", published=True)
    visit_data = {
        "patient_id": 101,
        "visit_date": "2025-01-01",
        "complaint": "fever",
        "prescriptions": [],
    }
    staff.post("/api/v1/phc/visits", data=visit_data, format="json")

    patient = client_for(PATIENT, uid=101)
    response = patient.get("/api/v1/phc/records/mine")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


def test_patient_cannot_get_all_visits(client_for):
    DoctorSchedule.objects.create(doctor_name="Dr G", day_of_week=5, start_time="10:00", end_time="12:00", published=True)
    Visit.objects.create(patient_id=1, visit_date="2025-01-01", complaint="test", recorded_by=900)
    client = client_for(PATIENT)
    response = client.get("/api/v1/phc/visits")
    assert response.status_code == 403
