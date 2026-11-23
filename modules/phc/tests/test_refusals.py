"""Each refusal a write can give, with its status and code, and nothing left behind."""
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from modules.phc.models import (
    AmbulanceLog,
    AuditRecord,
    ClaimAction,
    DoctorAttendance,
    DoctorSchedule,
    HealthAdvisory,
    InventoryItem,
    LowStockAlert,
    Notification,
    PatientVisit,
    Prescription,
    ReimbursementClaim,
    ReimbursementPolicy,
    Requisition,
    RequisitionLine,
    ScheduleSlot,
    StockAdjustment,
)
from modules.phc.selectors import scoping
from modules.phc.services import records
from modules.phc.tests.factories import (
    EMPLOYEE_ID,
    PHC_STAFF_ID,
    STUDENT_ID,
    client_as,
    item,
    visit_for,
)

pytestmark = pytest.mark.django_db

SLOT = {"day_of_week": 0, "start_time": "10:00", "end_time": "12:00"}


def _staff(stub_iam, **kw):
    return client_as(stub_iam, "PHC Staff", PHC_STAFF_ID, **kw)


# PHC-UC-22 E1
def test_duplicate_slot_is_refused(stub_iam):
    r = _staff(stub_iam).post("/api/v1/phc/schedules", {"doctor_name": "Dr. A",
                                                        "slots": [SLOT, SLOT]}, format="json")
    assert (r.status_code, r.data["error"]["code"]) == (400, "duplicate_slot")
    assert not DoctorSchedule.objects.exists()


def test_unknown_schedule_is_404(stub_iam):
    staff = _staff(stub_iam)
    assert staff.post("/api/v1/phc/schedules/999/publish").status_code == 404
    assert staff.post("/api/v1/phc/schedules/999/attendance",
                      {"status": "available"}).status_code == 404
    assert staff.put("/api/v1/phc/schedules/999", {"doctor_name": "x", "slots": [SLOT]},
                     format="json").status_code == 404
    assert not DoctorAttendance.objects.exists()


# PHC-UC-22 E1
def test_publishing_twice_or_with_no_slots_is_a_conflict(stub_iam):
    staff = _staff(stub_iam)
    empty = DoctorSchedule.objects.create(doctor_name="Dr. B", created_by_user_id=PHC_STAFF_ID)
    r = staff.post(f"/api/v1/phc/schedules/{empty.pk}/publish")
    assert (r.status_code, r.data["error"]["code"]) == (409, "schedule_without_slots")
    sid = staff.post("/api/v1/phc/schedules", {"doctor_name": "Dr. C", "slots": [SLOT]},
                     format="json").data["id"]
    assert staff.post(f"/api/v1/phc/schedules/{sid}/publish").status_code == 200
    r = staff.post(f"/api/v1/phc/schedules/{sid}/publish")
    assert (r.status_code, r.data["error"]["code"]) == (409, "already_published")


# PHC-UC-06 E1
def test_future_visit_and_unknown_patient_are_refused(stub_iam):
    staff = _staff(stub_iam)
    body = {"patient_user_id": EMPLOYEE_ID, "complaint": "x",
            "prescriptions": [{"medicine": "m", "dosage": "d"}]}
    r = staff.post("/api/v1/phc/records", {**body, "visit_date": str(
        timezone.localdate() + timedelta(days=1))}, format="json")
    assert (r.status_code, r.data["error"]["code"]) == (400, "visit_in_future")
    r = staff.post("/api/v1/phc/records", {**body, "visit_date": str(timezone.localdate())},
                   format="json")
    assert (r.status_code, r.data["error"]["code"]) == (404, "unknown_patient")
    assert not PatientVisit.objects.exists()


def test_pdf_prints_prescription_instructions():
    visit = visit_for(STUDENT_ID)
    Prescription.objects.create(visit=visit, medicine="ORS", dosage="1 sachet",
                                instructions="After each loose stool")
    body = records.records_pdf([visit])
    assert b"After each loose stool" in body
    assert b"ORS - 1 sachet" in body


# PHC-UC-10 E1
def test_requisition_with_duplicate_or_zero_line_is_refused(stub_iam):
    stock = item()
    staff = _staff(stub_iam)
    r = staff.post("/api/v1/phc/requisitions", {"purpose": "x", "lines": [
        {"item_id": stock.pk, "quantity": "1"}, {"item_id": stock.pk, "quantity": "2"}]},
        format="json")
    assert (r.status_code, r.data["error"]["code"]) == (400, "duplicate_line")
    r = staff.post("/api/v1/phc/requisitions", {"purpose": "x", "lines": [
        {"item_id": stock.pk, "quantity": "0"}]}, format="json")
    assert r.status_code == 400
    assert not Requisition.objects.exists()


def test_service_refuses_a_zero_quantity_line_on_its_own():
    from core.api.exceptions import BadRequestError
    from modules.phc.services import requisitions

    actor = SimpleNamespace(user_id=PHC_STAFF_ID)
    with pytest.raises(BadRequestError) as exc:
        requisitions.submit(actor=actor, purpose="x",
                            lines=[{"item_id": item().pk, "quantity": "0"}])
    assert exc.value.code == "bad_quantity"


def test_negative_opening_stock_and_unknown_item_are_refused(stub_iam):
    from core.api.exceptions import DomainError
    from modules.phc.services import inventory

    actor = SimpleNamespace(user_id=PHC_STAFF_ID)
    with pytest.raises(DomainError) as exc:
        inventory.create_item(actor=actor, name="X", unit="u", stock_level=-1,
                              reorder_threshold=0)
    assert exc.value.code == "negative_quantity"
    r = _staff(stub_iam).post("/api/v1/phc/inventory/999/adjust", {"delta": "1"})
    assert r.status_code == 404
    assert not InventoryItem.objects.exists()
    assert not AuditRecord.objects.exists()


def test_an_actor_with_no_identity_sees_nothing():
    nobody = SimpleNamespace(user_id=None, has_any_permission=lambda *c: True)
    for selector in (scoping.visits_for, scoping.own_prescriptions, scoping.claims_for,
                     scoping.requisitions_for, scoping.notifications_for):
        assert list(selector(nobody)) == []


def test_a_role_with_no_claim_grant_sees_no_claims():
    visitor = SimpleNamespace(user_id=STUDENT_ID, has_any_permission=lambda *c: False)
    assert list(scoping.claims_for(visitor)) == []
    assert list(scoping.requisitions_for(visitor)) == []


def test_every_model_names_itself_without_personal_data():
    stock = item()
    visit = visit_for(EMPLOYEE_ID)
    prescription = visit.prescriptions.get()
    schedule = DoctorSchedule.objects.create(doctor_name="Dr. D", created_by_user_id=1)
    slot = ScheduleSlot.objects.create(schedule=schedule, day_of_week=1, start_time="09:00",
                                       end_time="10:00")
    attendance = DoctorAttendance.objects.create(schedule=schedule,
                                                 attendance_date=timezone.localdate(),
                                                 status="available", updated_by_user_id=1)
    claim = ReimbursementClaim.objects.create(user_id=EMPLOYEE_ID, prescription=prescription,
                                              expense_date=timezone.localdate(),
                                              amount="1.00", submitted_at=timezone.now())
    action = ClaimAction.objects.create(claim=claim, actor_user_id=1, event="submit",
                                        to_status=claim.status)
    policy = ReimbursementPolicy.objects.create(effective_from=timezone.localdate(),
                                                window_days=30, includes_last_day=True)
    adjustment = StockAdjustment.objects.create(item=stock, delta="-60", level_after="40",
                                                adjusted_by_user_id=1)
    alert = LowStockAlert.objects.create(item=stock, adjustment=adjustment, level="40",
                                         threshold="50")
    req = Requisition.objects.create(originator_user_id=1, purpose="x")
    line = RequisitionLine.objects.create(requisition=req, item=stock, quantity="2")
    log = AmbulanceLog.objects.create(used_at=timezone.now(), patient_name="Hidden",
                                      destination="H", recorded_by_user_id=1)
    advisory = HealthAdvisory.objects.create(title="Heat", body="b",
                                             published_at=timezone.now(),
                                             published_by_user_id=1)
    audit = AuditRecord.objects.create(actor_user_id=1, resource_type="x", resource_id=1,
                                       action="create")
    note = Notification.objects.create(recipient_user_id=1, kind="k", message="m",
                                       resource_type="x", resource_id=1)
    labels = [str(o) for o in (stock, visit, prescription, schedule, slot, attendance, claim,
                               action, policy, adjustment, alert, req, line, log, advisory,
                               audit, note)]
    assert all(labels)
    assert not any("Hidden" in label for label in labels)
    assert str(slot).startswith("Tuesday 09:00")


# PHC-UC-09 E1
def test_adjustment_beyond_what_the_column_holds_is_refused(stub_iam):
    stock = item(level="9999999999.00", threshold="0")
    r = _staff(stub_iam).post(f"/api/v1/phc/inventory/{stock.pk}/adjust",
                              {"delta": "9999999999.00"})
    assert (r.status_code, r.data["error"]["code"]) == (422, "stock_too_large")
    stock.refresh_from_db()
    assert str(stock.stock_level) == "9999999999.00"
    assert not StockAdjustment.objects.exists()


# PHC-UC-03
def test_more_than_fifty_records_in_one_pdf_is_refused(stub_iam):
    student = client_as(stub_iam, "student", STUDENT_ID)
    ids = ",".join(str(i) for i in range(1, 52))
    r = student.get("/api/v1/phc/records/pdf", {"ids": ids})
    assert (r.status_code, r.data["error"]["code"]) == (400, "too_many_records")


# PHC-UC-03
def test_text_the_pdf_cannot_print_is_refused_at_entry(stub_iam, user_ref):
    staff = _staff(stub_iam, users={EMPLOYEE_ID: user_ref(EMPLOYEE_ID, kind="staff")})
    r = staff.post("/api/v1/phc/records", {
        "patient_user_id": EMPLOYEE_ID, "visit_date": str(timezone.localdate()),
        "complaint": "बुखार और खांसी", "prescriptions": [{"medicine": "m", "dosage": "d"}]},
        format="json")
    assert (r.status_code, r.data["error"]["code"]) == (400, "unprintable_text")
    assert not PatientVisit.objects.exists()


# PHC-BR-08
def test_illegal_claim_move_says_who_acts_next(stub_iam):
    visit = visit_for(EMPLOYEE_ID)
    claim = ReimbursementClaim.objects.create(user_id=EMPLOYEE_ID,
                                              prescription=visit.prescriptions.get(),
                                              expense_date=timezone.localdate(),
                                              amount="1.00", submitted_at=timezone.now())
    accounts = client_as(stub_iam, "Accounts & Audit", 4001)
    r = accounts.post(f"/api/v1/phc/claims/{claim.pk}/transition", {"event": "verify"})
    assert r.status_code == 409
    assert r.data["error"]["message"] == (
        "This claim is pending phc review, so it cannot be verified by your office now. "
        "It is waiting for PHC Staff to act.")
