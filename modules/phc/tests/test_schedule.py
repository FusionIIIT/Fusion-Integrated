import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import Doctor, DoctorAttendance, DoctorScheduleSlot

pytestmark = pytest.mark.django_db


def _client(stub_iam, user_id, role, permissions):
    stub_iam(make_session(user_id=user_id, kind="staff", modules=("phc",),
                          permissions=permissions, roles=(role,), active_role=role))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token phc-schedule")
    return client


# PHC-BR-01; PHC-UC-01; PHC-UC-07; PHC-UC-08; PHC-UC-22; CFR-PHC-001; AFR-PHC-001; AFR-PHC-002; AFR-PHC-003; AFR-PHC-004; AFR-PHC-005.
def test_phc_br_01_uc_01_published_schedule_combines_current_attendance(stub_iam):
    doctor = Doctor.objects.create(display_name="Dr. Example",
                                   specialization="General Medicine")
    slot = DoctorScheduleSlot.objects.create(
        doctor=doctor, day_of_week=0, starts_at="09:00", ends_at="12:00",
        publication=DoctorScheduleSlot.Publication.PUBLISHED)
    DoctorAttendance.objects.create(doctor=doctor,
        attendance_date=timezone.localdate(), status=DoctorAttendance.Status.AVAILABLE,
        updated_by_user_id=8)
    DoctorScheduleSlot.objects.create(doctor=Doctor.objects.create(
        display_name="Dr. Draft", specialization="General Medicine"),
        day_of_week=1, starts_at="09:00", ends_at="10:00")
    patient = _client(stub_iam, 1001, "student", ["phc.doctor_schedule.view"])

    response = patient.get("/api/v1/phc/doctor-availability")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [slot.pk]
    assert response.json()[0]["attendance_status"] == "available"


def test_phc_uc_08_marks_attendance_and_schedule_overlap_returns_conflict(stub_iam):
    doctor = Doctor.objects.create(display_name="Dr. Example",
                                   specialization="General Medicine")
    DoctorScheduleSlot.objects.create(doctor=doctor, day_of_week=2,
                                      starts_at="09:00", ends_at="11:00")
    compounder = _client(stub_iam, 2001, "Compounder", [
        "phc.doctor_schedule.create", "phc.doctor_schedule.view",
        "phc.doctor_attendance.update",
    ])
    overlap = compounder.post("/api/v1/phc/doctor-schedules", {
        "doctor_id": doctor.pk, "day_of_week": 2,
        "starts_at": "10:00", "ends_at": "12:00",
    }, format="json")
    assert overlap.status_code == 409
    attendance = compounder.post("/api/v1/phc/doctor-attendance", {
        "doctor_id": doctor.pk, "status": "available",
    }, format="json")
    assert attendance.status_code == 200
    assert attendance.json()["status"] == "available"


def test_phc_uc_07_uc_22_compounder_creates_edits_and_publishes_schedule(stub_iam):
    compounder = _client(stub_iam, 2001, "Compounder", [
        "phc.doctor_schedule.create", "phc.doctor_schedule.update",
        "phc.doctor_schedule.publish",
    ])
    created = compounder.post("/api/v1/phc/doctor-schedules", {
        "display_name": "Dr. New", "specialization": "General Medicine",
        "day_of_week": 3, "starts_at": "09:00", "ends_at": "12:00",
    }, format="json")
    assert created.status_code == 201
    slot_id = created.json()["id"]
    assert created.json()["publication"] == "draft"
    changed = compounder.patch(f"/api/v1/phc/doctor-schedules/{slot_id}", {
        "starts_at": "10:00", "ends_at": "13:00",
    }, format="json")
    assert changed.status_code == 200
    assert changed.json()["starts_at"] == "10:00:00"
    published = compounder.post(f"/api/v1/phc/doctor-schedules/{slot_id}/publish", {},
                                format="json")
    assert published.status_code == 200
    assert published.json()["publication"] == "published"


# PHC-BR-01; PHC-UC-07; PHC-UC-08; CFR-PHC-001; AFR-PHC-002; AFR-PHC-003.
def test_phc_br_01_staff_schedule_and_attendance_lists_and_refuses_inactive_doctor(
        stub_iam):
    doctor = Doctor.objects.create(display_name="Dr. Active",
                                   specialization="General Medicine")
    slot = DoctorScheduleSlot.objects.create(
        doctor=doctor, day_of_week=4, starts_at="09:00", ends_at="10:00")
    compounder = _client(stub_iam, 2001, "Compounder", [
        "phc.doctor_schedule.view", "phc.doctor_schedule.update",
        "phc.doctor_schedule.publish", "phc.doctor_attendance.update",
    ])
    assert compounder.get("/api/v1/phc/doctor-schedules").json()["results"][0]["id"] == slot.pk
    assert compounder.get("/api/v1/phc/doctor-attendance").status_code == 200
    empty_patch = compounder.patch(f"/api/v1/phc/doctor-schedules/{slot.pk}", {},
                                   format="json")
    assert empty_patch.status_code == 400
    doctor.is_active = False
    doctor.save(update_fields=["is_active"])
    inactive_publish = compounder.post(
        f"/api/v1/phc/doctor-schedules/{slot.pk}/publish", {}, format="json")
    assert inactive_publish.status_code == 404
    inactive_attendance = compounder.post("/api/v1/phc/doctor-attendance", {
        "doctor_id": doctor.pk, "status": "available",
    }, format="json")
    assert inactive_attendance.status_code == 404
