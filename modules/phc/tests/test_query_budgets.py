from datetime import date

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import Doctor, DoctorScheduleSlot, PatientVisit

pytestmark = pytest.mark.django_db


def _client(stub_iam, permission, user_id=900):
    role = "student" if permission == "phc.patient_record.view" else "staff"
    stub_iam(make_session(user_id=user_id, kind=role, modules=("phc",),
                          permissions=(permission,), roles=(role,), active_role=role))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token query-budget")
    return client


def test_phc_br_02_patient_record_query_count_does_not_grow_with_rows(
        stub_iam, django_assert_num_queries):
    client = _client(stub_iam, "phc.patient_record.view")
    for index in range(2):
        PatientVisit.objects.create(patient_user_id=900, visited_on=date(2026, 1, index + 1),
                                    notes=f"Visit {index}", recorded_by_user_id=901)
    with CaptureQueriesContext(connection) as first:
        assert client.get("/api/v1/phc/records").status_code == 200
    for index in range(2, 20):
        PatientVisit.objects.create(patient_user_id=900, visited_on=date(2026, 2, index - 1),
                                    notes=f"Visit {index}", recorded_by_user_id=901)
    with CaptureQueriesContext(connection) as second:
        assert client.get("/api/v1/phc/records").status_code == 200
    assert len(first) == len(second)


def test_phc_br_01_schedule_list_has_a_fixed_query_budget(stub_iam,
                                                           django_assert_max_num_queries):
    doctor = Doctor.objects.create(display_name="Doctor", specialization="General",
                                   is_active=True)
    for day in range(7):
        DoctorScheduleSlot.objects.create(doctor=doctor, day_of_week=day,
                                          starts_at="09:00", ends_at="10:00",
                                          publication="published")
    client = _client(stub_iam, "phc.doctor_schedule.view")
    with django_assert_max_num_queries(5):
        assert client.get("/api/v1/phc/doctor-availability").status_code == 200
