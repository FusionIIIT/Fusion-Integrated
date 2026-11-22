import pytest
from datetime import date
from modules.hreis.models import EmployeeServiceRecord
from modules.hreis.services.service_records import get_or_create_service_record, update_service_record

pytestmark = pytest.mark.django_db


def test_fr_033_employee_view_own_service_record(auth_client_factory):
    """TEST-FR-033 [HR-AFR-003]: Verify HR-EIS allows an Employee to view the Employee's own service records."""
    EmployeeServiceRecord.objects.create(
        user_id=170,
        employee_id="EMP0170",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 8},
    )
    client, _ = auth_client_factory(user_id=170, role="faculty")
    resp = client.get("/api/v1/hreis/service-records/me/")
    assert resp.status_code == 200
    assert resp.data["employee_id"] == "EMP0170"


def test_fr_034_centralized_service_record_maintenance():
    """TEST-FR-034 [HR-AFR-019]: Verify HR-EIS maintains a centralized service record for each employee."""
    rec = get_or_create_service_record(user_id=171)
    assert rec.id is not None
    assert rec.user_id == 171


def test_fr_035_appointment_details_included():
    """TEST-FR-035 [HR-AFR-020]: Verify HR-EIS includes appointment details in the employee service record."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=172,
        employee_id="EMP0172",
        department="ECE",
        designation="Professor",
        category="faculty",
        appointment_date=date(2020, 7, 1),
    )
    assert rec.appointment_date == date(2020, 7, 1)


def test_fr_036_department_included():
    """TEST-FR-036 [HR-AFR-021]: Verify HR-EIS includes department in the employee service record."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=173,
        employee_id="EMP0173",
        department="Mechanical Engineering",
        designation="Assistant Professor",
        category="faculty",
    )
    assert rec.department == "Mechanical Engineering"


def test_fr_037_designation_included():
    """TEST-FR-037 [HR-AFR-022]: Verify HR-EIS includes designation in the employee service record."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=174,
        employee_id="EMP0174",
        department="CSE",
        designation="Associate Professor",
        category="faculty",
    )
    assert rec.designation == "Associate Professor"


def test_fr_038_service_history_included():
    """TEST-FR-038 [HR-AFR-023]: Verify HR-EIS includes service history in the employee service record."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=175,
        employee_id="EMP0175",
        department="CSE",
        designation="Associate Professor",
        category="faculty",
        service_history=[
            {"event": "Appointment", "designation": "Assistant Professor", "date": "2018-01-01"},
            {"event": "Promotion", "designation": "Associate Professor", "date": "2023-01-01"},
        ],
    )
    assert len(rec.service_history) == 2
    assert rec.service_history[1]["event"] == "Promotion"


def test_fr_039_leave_balances_included():
    """TEST-FR-039 [HR-AFR-024]: Verify HR-EIS includes leave balances in the employee service record."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=176,
        employee_id="EMP0176",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 8, "medical": 10, "earned": 15},
    )
    assert rec.leave_balances["casual"] == 8
    assert rec.leave_balances["medical"] == 10


def test_fr_040_retirement_status_included():
    """TEST-FR-040 [HR-AFR-025]: Verify HR-EIS includes retirement status in the employee service record."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=177,
        employee_id="EMP0177",
        department="Design",
        designation="Professor",
        category="faculty",
        retirement_status="active",
    )
    assert rec.retirement_status == "active"


def test_fr_041_restrict_creation_to_hr_admin(auth_client_factory):
    """TEST-FR-041 [HR-AFR-026]: Verify HR-EIS restricts creation of employee service records to HR Administrators."""
    client_faculty, _ = auth_client_factory(user_id=178, role="faculty")
    resp = client_faculty.post(
        "/api/v1/hreis/service-records/",
        {"user_id": 999, "employee_id": "EMP9999", "department": "CSE"},
        format="json",
    )
    assert resp.status_code == 403


def test_fr_042_restrict_modification_to_hr_admin(auth_client_factory):
    """TEST-FR-042 [HR-AFR-027]: Verify HR-EIS restricts modification of employee service records to HR Administrators."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=179,
        employee_id="EMP0179",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    client_faculty, _ = auth_client_factory(user_id=179, role="faculty")
    resp = client_faculty.patch(f"/api/v1/hreis/service-records/{rec.id}/", {"designation": "HOD"})
    assert resp.status_code == 403


def test_fr_043_employees_view_read_only(auth_client_factory):
    """TEST-FR-043 [HR-AFR-028]: Verify HR-EIS allows Employees to view their own service records in read-only mode."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=180,
        employee_id="EMP0180",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    client, _ = auth_client_factory(user_id=180, role="faculty")
    resp_get = client.get("/api/v1/hreis/service-records/me/")
    assert resp_get.status_code == 200

    resp_put = client.put("/api/v1/hreis/service-records/me/", {"designation": "Director"})
    assert resp_put.status_code in (403, 405)


def test_fr_044_preserve_service_record_consistency():
    """TEST-FR-044 [HR-AFR-102]: Verify HR-EIS preserves service record consistency during updates."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=181,
        employee_id="EMP0181",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 8},
    )
    updated = update_service_record(
        record_id=rec.id,
        data={"designation": "Associate Professor", "department": "CSE"},
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert updated.designation == "Associate Professor"
    assert updated.leave_balances["casual"] == 8


def test_fr_045_prevent_partial_updates_corrupting_records():
    """TEST-FR-045 [HR-AFR-103]: Verify HR-EIS prevents partial updates from corrupting service records."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=182,
        employee_id="EMP0182",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    try:
        update_service_record(
            record_id=rec.id,
            data={"appointment_date": "invalid-date-format"},
            actor_id=201,
            actor_username="hradmin",
            actor_role="hr_admin",
        )
    except Exception:
        pass

    rec.refresh_from_db()
    assert rec.designation == "Assistant Professor"


def test_fr_046_employees_cannot_alter_official_records(auth_client_factory):
    """TEST-FR-046 [HR-AFR-107]: Verify HR-EIS does not permit Employees to alter official service records."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=183,
        employee_id="EMP0183",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    client_emp, _ = auth_client_factory(user_id=183, role="faculty")
    resp = client_emp.patch(
        f"/api/v1/hreis/service-records/{rec.id}/",
        {"leave_balances": {"casual": 999}},
        format="json",
    )
    assert resp.status_code == 403
