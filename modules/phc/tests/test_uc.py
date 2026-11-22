"""UC strategy: exercise active actor goals through the PHC API."""

import datetime as dt
from decimal import Decimal

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


# Additional independent actor-goal scenarios; pytest counts every parameter
# as a separate executable case and prints the scenario ID in its report.


@pytest.mark.parametrize("kind,expected", [("student", 1), ("staff", 2)], ids=["patient", "phc-staff"])
def test_uc_patient_sees_published_schedule_while_staff_sees_drafts(phc_client, kind, expected):
    from modules.phc.models import DoctorSchedule

    DoctorSchedule.objects.create(
        doctor_name="Published Doctor", day_of_week="MON", start_time="09:00", end_time="10:00",
        is_published=True, created_by_user_id=900,
    )
    DoctorSchedule.objects.create(
        doctor_name="Draft Doctor", day_of_week="TUE", start_time="10:00", end_time="11:00",
        is_published=False, created_by_user_id=900,
    )
    permissions = ("phc.schedule.manage",) if kind == "staff" else ()
    response = phc_client(kind=kind, permissions=permissions).get("/api/v1/phc/schedules/")
    assert response.status_code == 200
    assert len(response.json()["results"]) == expected


@pytest.mark.parametrize("status", ["available", "departed"], ids=["available", "departed"])
def test_uc_staff_marks_doctor_attendance_for_selected_day(phc_client, status):
    from modules.phc.models import DoctorSchedule

    schedule = DoctorSchedule.objects.create(
        doctor_name="Dr Day", day_of_week="MON", start_time="09:00", end_time="10:00",
        created_by_user_id=900,
    )
    response = phc_client(uid=900, kind="staff", permissions=("phc.attendance.mark",)).post(
        "/api/v1/phc/attendance/mark/",
        {"schedule_id": schedule.pk, "status": status, "date": "2026-11-23"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == status
    assert response.json()["marked_by_user_id"] == 900


@pytest.mark.parametrize("uid,expected", [(1001, 1), (2002, 0)], ids=["owner", "other-patient"])
def test_uc_patient_visit_list_is_scoped_to_authenticated_patient(phc_client, visit, uid, expected):
    client = phc_client(uid=uid, permissions=("phc.record.view_self",))
    response = client.get("/api/v1/phc/my/visits/")
    assert response.status_code == 200
    assert len(response.json()["results"]) == expected


@pytest.mark.parametrize("uid,expected", [(1001, 1), (2002, 0)], ids=["prescription-owner", "different-patient"])
def test_uc_patient_prescription_list_is_scoped_by_owner(phc_client, prescription, uid, expected):
    client = phc_client(uid=uid, permissions=("phc.record.view_self",))
    response = client.get("/api/v1/phc/my/prescriptions/")
    assert response.status_code == 200
    assert len(response.json()["results"]) == expected


@pytest.mark.parametrize("selection", ["all", "single"], ids=["all-own-visits", "one-selected-visit"])
def test_uc_patient_downloads_all_or_selected_own_visit_records(phc_client, visit, selection):
    client = phc_client(uid=1001, permissions=("phc.record.view_self",))
    suffix = "" if selection == "all" else f"?ids={visit.pk}"
    response = client.get(f"/api/v1/phc/my/visits/download/{suffix}")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


@pytest.mark.parametrize("kind", ["faculty", "staff"], ids=["faculty-claimant", "staff-claimant"])
def test_uc_employee_tracks_their_claim(phc_client, prescription, kind):
    from decimal import Decimal

    from modules.phc.models import ReimbursementClaim

    claim = ReimbursementClaim.objects.create(
        user_id=1001, prescription=prescription, amount_claimed=Decimal("16.50")
    )
    response = phc_client(uid=1001, kind=kind, permissions=("phc.claim.view_self",)).get(
        f"/api/v1/phc/claims/my/{claim.pk}/"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending_phc_review"


@pytest.mark.parametrize("status", ["pending_phc_review", "pending_sanction"], ids=["phc-queue", "sanction-queue"])
def test_uc_authorized_reviewer_filters_claim_queue_by_status(phc_client, prescription, status):
    from decimal import Decimal

    from modules.phc.models import ReimbursementClaim

    ReimbursementClaim.objects.create(
        user_id=1001, prescription=prescription, amount_claimed=Decimal("11.00"), status=status
    )
    response = phc_client(uid=900, kind="staff", permissions=("phc.claim.review_phc",)).get(
        f"/api/v1/phc/claims/?status={status}"
    )
    assert response.status_code == 200
    assert all(row["status"] == status for row in response.json()["results"])


@pytest.mark.parametrize("name,stock", [("Cotton", "0"), ("Gloves", "12.50")], ids=["zero-stock", "fractional-stock"])
def test_uc_staff_creates_inventory_items(phc_client, name, stock):
    response = phc_client(uid=900, kind="staff", permissions=("phc.inventory.manage",)).post(
        "/api/v1/phc/inventory/create/",
        {"name": name, "stock_quantity": stock, "reorder_threshold": "2", "unit": "pack"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["name"] == name
    assert Decimal(response.json()["stock_quantity"]) == Decimal(stock)


@pytest.mark.parametrize("stock,expected", [("1", 1), ("2", 0)], ids=["below-threshold", "at-threshold"])
def test_uc_staff_uses_low_stock_view_for_reorder_work(phc_client, stock, expected):
    from decimal import Decimal

    from modules.phc.models import InventoryItem

    InventoryItem.objects.create(
        name=f"Threshold-{stock}", stock_quantity=Decimal(stock), reorder_threshold=Decimal("2")
    )
    response = phc_client(uid=900, kind="staff", permissions=("phc.inventory.manage",)).get(
        "/api/v1/phc/inventory/low-stock/"
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == expected


@pytest.mark.parametrize("items", [[{"item_name": "Mask", "quantity": "1"}], [{"item_name": "Mask", "quantity": "1"}, {"item_name": "Glove", "quantity": "2"}]], ids=["single-line", "multiple-lines"])
def test_uc_staff_submits_requisition_with_requested_line_items(phc_client, items):
    response = phc_client(uid=900, kind="staff", permissions=("phc.requisition.submit",)).post(
        "/api/v1/phc/requisitions/create/", {"title": "Clinic supplies", "line_items": items},
        format="json",
    )
    assert response.status_code == 201
    assert len(response.json()["line_items"]) == len(items)


@pytest.mark.parametrize("role,permission,expected", [("staff", "phc.requisition.submit", 1), ("staff", "phc.requisition.decide", 1)], ids=["submitter-view", "authority-pending-view"])
def test_uc_submitter_or_authority_can_retrieve_requisition_queue(phc_client, role, permission, expected):
    from modules.phc.models import ProcurementRequisition

    ProcurementRequisition.objects.create(title="Reorder", submitted_by_user_id=900)
    response = phc_client(uid=900 if permission.endswith("submit") else 902, kind=role, permissions=(permission,)).get(
        "/api/v1/phc/requisitions/"
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == expected


@pytest.mark.parametrize("notes", ["", "Urgent patient transfer"], ids=["optional-notes-omitted", "notes-recorded"])
def test_uc_staff_records_ambulance_trip_with_optional_notes(phc_client, notes):
    payload = {"patient_name": "Patient B", "destination": "City Hospital", "usage_at": "2026-11-20T10:30:00Z"}
    if notes:
        payload["notes"] = notes
    response = phc_client(uid=900, kind="staff", permissions=("phc.ambulance.log",)).post(
        "/api/v1/phc/ambulance/log/", payload, format="json"
    )
    assert response.status_code == 201
    assert response.json()["notes"] == notes


@pytest.mark.parametrize("kind,expected", [("student", 1), ("staff", 2)], ids=["patient-published-only", "staff-includes-drafts"])
def test_uc_announcement_audience_sees_correct_publication_scope(phc_client, kind, expected):
    from modules.phc.models import HealthAnnouncement

    HealthAnnouncement.objects.create(title="Public", body="Update", is_published=True, published_by_user_id=900)
    HealthAnnouncement.objects.create(title="Draft", body="Not public", is_published=False, published_by_user_id=900)
    permissions = ("phc.announcement.publish",) if kind == "staff" else ()
    response = phc_client(kind=kind, permissions=permissions).get("/api/v1/phc/announcements/")
    assert response.status_code == 200
    assert len(response.json()["results"]) == expected


@pytest.mark.parametrize("report_type", ["inventory", "utilization"], ids=["stock-report", "visit-utilization-report"])
def test_uc_staff_generates_supported_operational_report(phc_client, report_type):
    response = phc_client(uid=900, kind="staff", permissions=("phc.report.view",)).get(
        f"/api/v1/phc/reports/?type={report_type}"
    )
    assert response.status_code == 200
    assert response.json()["report_type"] == report_type


@pytest.mark.parametrize("with_optional_fields", [False, True], ids=["defaults", "full-schedule-details"])
def test_uc_staff_creates_schedule_slot_as_unpublished_draft(phc_client, with_optional_fields):
    payload = {
        "doctor_name": "Dr Schedule",
        "day_of_week": "WED",
        "start_time": "09:00",
        "end_time": "11:00",
    }
    if with_optional_fields:
        payload.update({"specialisation": "General Medicine", "room": "Room 2"})
    response = phc_client(uid=900, kind="staff", permissions=("phc.schedule.manage",)).post(
        "/api/v1/phc/schedules/create/", payload, format="json"
    )
    assert response.status_code == 201
    assert response.json()["is_published"] is False
    assert response.json()["doctor_name"] == "Dr Schedule"


@pytest.mark.django_db
def test_uc_staff_publishes_existing_schedule_and_patient_can_see_it(phc_client):
    from modules.phc.models import DoctorSchedule

    schedule = DoctorSchedule.objects.create(
        doctor_name="Dr Publish", day_of_week="THU", start_time="10:00", end_time="11:00",
        is_published=False, created_by_user_id=900,
    )
    staff = phc_client(uid=900, kind="staff", permissions=("phc.schedule.manage",))
    response = staff.post(f"/api/v1/phc/schedules/{schedule.pk}/publish/")
    assert response.status_code == 200
    patient = phc_client(uid=1001)
    assert any(
        row["id"] == schedule.pk for row in patient.get("/api/v1/phc/schedules/").json()["results"]
    )


@pytest.mark.django_db
def test_uc_staff_can_review_all_patient_visits(phc_client, visit):
    from modules.phc.models import PatientVisit

    PatientVisit.objects.create(
        user_id=2002, visit_date="2026-11-02", chief_complaint="Review", recorded_by_user_id=900
    )
    response = phc_client(uid=900, kind="staff", permissions=("phc.record.manage",)).get(
        "/api/v1/phc/visits/"
    )
    assert response.status_code == 200
    assert {row["user_id"] for row in response.json()["results"]} == {1001, 2002}


@pytest.mark.parametrize(
    "limit,expected_status", [("abc", 400), ("0", 200), ("101", 200)],
    ids=["nonnumeric-limit", "lower-limit-clamped", "upper-limit-clamped"],
)
def test_uc_staff_patient_search_validates_and_clamps_result_limit(
    phc_client, monkeypatch, limit, expected_status
):
    from modules.phc.services import records

    monkeypatch.setattr(records.directory_contracts, "search", lambda query, kind, limit: [])
    response = phc_client(uid=900, kind="staff", permissions=("phc.record.manage",)).get(
        f"/api/v1/phc/patients/search/?q=Patient&limit={limit}"
    )
    assert response.status_code == expected_status


def test_uc_staff_short_patient_query_returns_empty_results_without_directory_lookup(
    phc_client, monkeypatch
):
    from modules.phc.services import records

    monkeypatch.setattr(
        records.directory_contracts,
        "search",
        lambda *args, **kwargs: pytest.fail("short queries must not search Directory"),
    )
    response = phc_client(uid=900, kind="staff", permissions=("phc.record.manage",)).get(
        "/api/v1/phc/patients/search/?q=A"
    )
    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.parametrize(
    "optional", [False, True], ids=["minimal-prescription", "instructions-and-expense-date"]
)
def test_uc_staff_adds_prescription_with_optional_details(phc_client, visit, optional):
    payload = {"medicine_name": "Medicine", "dosage": "1 tablet"}
    if optional:
        payload.update({"duration_days": 4, "instructions": "After food", "expense_date": "2026-11-20"})
    response = phc_client(uid=900, kind="staff", permissions=("phc.record.manage",)).post(
        f"/api/v1/phc/visits/{visit.pk}/prescriptions/", payload, format="json"
    )
    assert response.status_code == 201
    assert response.json()["medicine_name"] == "Medicine"


@pytest.mark.django_db
def test_uc_staff_reads_inventory_item_details_and_ordered_list(phc_client):
    from modules.phc.models import InventoryItem

    InventoryItem.objects.create(name="Zinc", stock_quantity=Decimal("4"))
    item = InventoryItem.objects.create(name="Antiseptic", stock_quantity=Decimal("6"))
    client = phc_client(uid=900, kind="staff", permissions=("phc.inventory.manage",))
    assert client.get(f"/api/v1/phc/inventory/{item.pk}/").json()["name"] == "Antiseptic"
    names = [row["name"] for row in client.get("/api/v1/phc/inventory/").json()["results"]]
    assert names == ["Antiseptic", "Zinc"]


@pytest.mark.parametrize("owner,visible", [(1001, True), (2002, False)], ids=["recipient", "other-user"])
def test_uc_notifications_are_visible_only_to_the_recipient(phc_client, owner, visible):
    from modules.phc.models import PhcNotification

    PhcNotification.objects.create(
        recipient_user_id=1001, event_type="claim_status_changed", subject="Claim update", body="New status"
    )
    response = phc_client(uid=owner).get("/api/v1/phc/notifications/")
    assert response.status_code == 200
    assert bool(response.json()["results"]) is visible


@pytest.mark.parametrize("include_date", [False, True], ids=["server-default-date", "explicit-date"])
def test_uc_attendance_mark_uses_default_or_requested_date(phc_client, include_date):
    from django.utils import timezone

    from modules.phc.models import DoctorAttendance, DoctorSchedule

    schedule = DoctorSchedule.objects.create(
        doctor_name="Dr Attendance", day_of_week="FRI", start_time="08:00", end_time="09:00",
        created_by_user_id=900,
    )
    payload = {"schedule_id": schedule.pk, "status": "available"}
    if include_date:
        payload["date"] = "2026-11-20"
    response = phc_client(uid=900, kind="staff", permissions=("phc.attendance.mark",)).post(
        "/api/v1/phc/attendance/mark/", payload, format="json"
    )
    expected = dt.date.fromisoformat(payload["date"]) if include_date else timezone.localdate()
    assert response.status_code == 200
    assert DoctorAttendance.objects.get(schedule=schedule).date == expected


@pytest.mark.parametrize("report_type", ["demographics", "inventory_consumption"], ids=["default-report", "consumption-report"])
def test_uc_staff_can_use_default_report_and_consumption_alias(phc_client, report_type):
    query = "" if report_type == "demographics" else "?type=inventory_consumption"
    response = phc_client(uid=900, kind="staff", permissions=("phc.report.view",)).get(
        f"/api/v1/phc/reports/{query}"
    )
    assert response.status_code == 200
    assert response.json()["report_type"] == report_type


@pytest.mark.parametrize(
    "kind,permission,path,method,payload",
    [
        ("staff", "phc.schedule.manage", "/api/v1/phc/schedules/999999/publish/", "post", {}),
        ("staff", "phc.attendance.mark", "/api/v1/phc/attendance/mark/", "post", {"schedule_id": 999999, "status": "available"}),
        ("student", "phc.record.view_self", "/api/v1/phc/my/visits/download/?ids=999999", "get", None),
        ("staff", "phc.record.manage", "/api/v1/phc/visits/999999/prescriptions/", "post", {"medicine_name": "M", "dosage": "1"}),
        ("staff", "phc.claim.review_phc", "/api/v1/phc/claims/999999/review/", "post", {}),
        ("staff", "phc.claim.verify", "/api/v1/phc/claims/999999/verify/", "post", {}),
        ("staff", "phc.claim.decide", "/api/v1/phc/claims/999999/decide/", "post", {"approve": True}),
        ("staff", "phc.claim.payment", "/api/v1/phc/claims/999999/payment/", "post", {}),
        ("staff", "phc.inventory.manage", "/api/v1/phc/inventory/999999/", "get", None),
        ("staff", "phc.inventory.manage", "/api/v1/phc/inventory/999999/adjust/", "post", {"delta": "1"}),
        ("staff", "phc.requisition.decide", "/api/v1/phc/requisitions/999999/decide/", "post", {"approve": True}),
        ("staff", "phc.requisition.fulfill", "/api/v1/phc/requisitions/999999/fulfill/", "post", {}),
    ],
    ids=[
        "missing-schedule-publish", "attendance-missing-schedule", "pdf-missing-owned-visit",
        "prescription-missing-visit", "review-missing-claim", "verify-missing-claim",
        "decide-missing-claim", "payment-missing-claim", "inventory-missing-item",
        "adjust-missing-item", "decide-missing-requisition", "fulfill-missing-requisition",
    ],
)
def test_uc_missing_resource_actions_return_not_found(phc_client, kind, permission, path, method, payload):
    client = phc_client(uid=1001 if kind == "student" else 900, kind=kind, permissions=(permission,))
    response = client.get(path) if method == "get" else client.post(path, payload, format="json")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"day_of_week": "MON", "start_time": "09:00", "end_time": "10:00"},
        {"doctor_name": "Dr Invalid", "day_of_week": "XYZ", "start_time": "09:00", "end_time": "10:00"},
        {"doctor_name": "Dr Invalid", "day_of_week": "MON", "start_time": "bad", "end_time": "10:00"},
        {"doctor_name": "Dr Invalid", "day_of_week": "MON", "start_time": "10:00", "end_time": "09:00"},
    ],
    ids=["doctor-name-required", "weekday-choice", "time-format", "end-after-start"],
)
def test_uc_invalid_schedule_creation_is_rejected(phc_client, payload):
    response = phc_client(uid=900, kind="staff", permissions=("phc.schedule.manage",)).post(
        "/api/v1/phc/schedules/create/", payload, format="json"
    )
    assert response.status_code == 400


@pytest.mark.parametrize("status", ["present", "absent", ""], ids=["unknown-choice", "unknown-choice-two", "blank-status"])
def test_uc_attendance_rejects_status_outside_available_or_departed(phc_client, status):
    from modules.phc.models import DoctorSchedule

    schedule = DoctorSchedule.objects.create(
        doctor_name="Dr Status", day_of_week="MON", start_time="09:00", end_time="10:00",
        created_by_user_id=900,
    )
    response = phc_client(uid=900, kind="staff", permissions=("phc.attendance.mark",)).post(
        "/api/v1/phc/attendance/mark/", {"schedule_id": schedule.pk, "status": status}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_uc_employee_tracks_claims_in_list_view(phc_client, prescription):
    from modules.phc.models import ReimbursementClaim

    ReimbursementClaim.objects.create(user_id=1001, prescription=prescription, amount_claimed="8.00")
    response = phc_client(uid=1001, kind="faculty", permissions=("phc.claim.view_self",)).get(
        "/api/v1/phc/claims/my/"
    )
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


@pytest.mark.django_db
def test_uc_pdf_export_contains_prescription_instructions_and_escapes_pdf_text(visit, prescription):
    from modules.phc.services.pdf import render_visits_pdf

    visit.diagnosis = "Pain (left side)"
    visit.notes = "Use backslash \\ carefully"
    visit.save(update_fields=["diagnosis", "notes"])
    prescription.instructions = "Take (after food)"
    prescription.duration_days = None
    prescription.save(update_fields=["instructions", "duration_days"])
    document = render_visits_pdf([visit])
    assert document.startswith(b"%PDF-")
    assert b"Diagnosis: Pain \\(left side\\)" in document
    assert b"Instructions: Take \\(after food\\)" in document


@pytest.mark.django_db
def test_uc_pdf_export_replaces_unsupported_unicode_safely(visit):
    from modules.phc.services.pdf import render_visits_pdf

    visit.chief_complaint = "Pain — follow-up"
    visit.save(update_fields=["chief_complaint"])
    document = render_visits_pdf([visit])
    assert b"Chief complaint: Pain ? follow-up" in document


@pytest.mark.django_db
def test_uc_staff_reads_and_updates_reimbursement_window_configuration(phc_client):
    staff = phc_client(uid=900, kind="staff", permissions=("phc.claim.configure",))
    read = staff.get("/api/v1/phc/claims/config/")
    assert read.status_code == 200
    assert read.json()["submission_window_days"] == 90
    updated = staff.patch(
        "/api/v1/phc/claims/config/", {"submission_window_days": 45}, format="json"
    )
    assert updated.status_code == 200
    assert updated.json()["submission_window_days"] == 45


@pytest.mark.django_db
def test_uc_staff_reads_ambulance_usage_log(phc_client):
    from modules.phc.models import AmbulanceLog

    AmbulanceLog.objects.create(
        patient_name="Patient C", destination="District Hospital", usage_at="2026-11-21T10:00:00Z",
        recorded_by_user_id=900,
    )
    response = phc_client(uid=900, kind="staff", permissions=("phc.ambulance.log",)).get(
        "/api/v1/phc/ambulance/"
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["destination"] == "District Hospital"
