"""UC strategy: exercise active actor goals through the PHC API."""

import pytest

pytestmark = pytest.mark.django_db


def test_patient_reads_only_own_records_and_can_download_pdf(phc_client, visit):
    from modules.phc.models import PatientVisit

    PatientVisit.objects.create(
        user_id=2002, visit_date="2026-10-02", chief_complaint="Private", recorded_by_user_id=900
    )
    client = phc_client(uid=1001, permissions=("phc.record.view_self",))
    rows = client.get("/api/v1/phc/my/visits/").json()["results"]
    assert [row["user_id"] for row in rows] == [1001]
    assert client.get(f"/api/v1/phc/my/visits/{visit.pk}/").status_code == 200
    assert client.get("/api/v1/phc/my/visits/2/").status_code == 404
    pdf = client.get(f"/api/v1/phc/my/visits/download/?ids={visit.pk}")
    assert pdf.status_code == 200
    assert pdf["Content-Type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")


def test_patient_schedule_visibility_and_attendance(phc_client):
    from modules.phc.models import DoctorAttendance, DoctorSchedule

    schedule = DoctorSchedule.objects.create(
        doctor_name="Dr Rao",
        day_of_week="MON",
        start_time="09:00",
        end_time="12:00",
        is_published=True,
        created_by_user_id=900,
    )
    DoctorAttendance.objects.create(
        schedule=schedule, date="2026-11-23", status="departed", marked_by_user_id=900
    )
    patient = phc_client(uid=1001, permissions=("phc.schedule.view",))
    assert patient.get("/api/v1/phc/schedules/").status_code == 200
    assert patient.get("/api/v1/phc/attendance/today/").status_code == 200


def test_staff_can_create_visit_and_add_linked_prescription(phc_client):
    staff = phc_client(uid=900, kind="staff", permissions=("phc.record.manage",))
    response = staff.post(
        "/api/v1/phc/visits/create/",
        {
            "patient_user_id": 1001,
            "visit_date": "2026-11-20",
            "chief_complaint": "Cough",
        },
        format="json",
    )
    assert response.status_code == 201
    visit_id = response.json()["id"]
    rx = staff.post(
        f"/api/v1/phc/visits/{visit_id}/prescriptions/",
        {
            "medicine_name": "Syrup",
            "dosage": "5 ml",
            "expense_date": "2026-11-20",
        },
        format="json",
    )
    assert rx.status_code == 201
    assert rx.json()["visit"] == visit_id


def test_staff_can_search_patient_profile(phc_client, monkeypatch):
    from types import SimpleNamespace

    from modules.phc.services import records

    monkeypatch.setattr(
        records.directory_contracts,
        "search",
        lambda query, kind, limit: (
            [
                SimpleNamespace(
                    user_id=1001,
                    username="student-1001",
                    display_name="Asha Patient",
                    kind=kind,
                )
            ]
            if kind == "student"
            else []
        ),
    )
    staff = phc_client(uid=900, kind="staff", permissions=("phc.record.manage",))
    response = staff.get("/api/v1/phc/patients/search/?q=Asha")
    assert response.status_code == 200
    assert response.json()["results"] == [
        {
            "user_id": 1001,
            "username": "student-1001",
            "display_name": "Asha Patient",
            "kind": "student",
        }
    ]


def test_staff_can_log_ambulance_and_publish_patient_advisory(phc_client):
    staff = phc_client(
        uid=900, kind="staff", permissions=("phc.ambulance.log", "phc.announcement.publish")
    )
    log = staff.post(
        "/api/v1/phc/ambulance/log/",
        {
            "patient_name": "Patient A",
            "destination": "City Hospital",
            "usage_at": "2026-11-20T10:30:00Z",
        },
        format="json",
    )
    assert log.status_code == 201
    published = staff.post(
        "/api/v1/phc/announcements/publish/",
        {
            "title": "Flu clinic",
            "body": "Clinic runs Friday.",
        },
        format="json",
    )
    assert published.status_code == 201
    patient = phc_client(uid=1001)
    assert patient.get("/api/v1/phc/announcements/").json()["results"][0]["title"] == "Flu clinic"


def test_patient_cannot_create_staff_visit(phc_client):
    patient = phc_client(uid=1001, permissions=("phc.record.view_self",))
    response = patient.post(
        "/api/v1/phc/visits/create/",
        {
            "patient_user_id": 1001,
            "visit_date": "2026-11-20",
            "chief_complaint": "Unauthorized",
        },
        format="json",
    )
    assert response.status_code == 403


def test_staff_can_report_consumed_inventory_from_stock_audit(phc_client):
    from decimal import Decimal

    from modules.phc.models import InventoryAudit, InventoryItem

    item = InventoryItem.objects.create(name="Masks", unit="box")
    InventoryAudit.objects.create(
        item=item,
        delta=Decimal("-3"),
        quantity_before=Decimal("10"),
        quantity_after=Decimal("7"),
        actor_user_id=900,
    )
    InventoryAudit.objects.create(
        item=item,
        delta=Decimal("-2"),
        quantity_before=Decimal("7"),
        quantity_after=Decimal("5"),
        actor_user_id=900,
    )
    InventoryAudit.objects.create(
        item=item,
        delta=Decimal("4"),
        quantity_before=Decimal("5"),
        quantity_after=Decimal("9"),
        actor_user_id=900,
    )
    staff = phc_client(uid=900, kind="staff", permissions=("phc.report.view",))
    response = staff.get("/api/v1/phc/reports/?type=inventory_consumption")
    assert response.status_code == 200
    row = response.json()["items"][0]
    assert row["item_name"] == "Masks"
    assert Decimal(row["quantity_consumed"]) == Decimal("5")
