"""Adversarial FR checks: auth gates, error envelopes, budgets and throttles."""
import datetime as dt

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.models import (
    DoctorSchedule,
    InventoryItem,
    Patient,
    Prescription,
    Requisition,
    StockAdjustment,
    Visit,
)

pytestmark = pytest.mark.django_db

SCHEDULE = "/api/v1/phc/schedule"


def _client(stub_iam, *, user_id=1001, kind="patient", roles=("patient",),
            active_role="patient", permissions=(), modules=("phc",), users=None):
    stub_iam(make_session(user_id=user_id, kind=kind, roles=roles,
                          active_role=active_role, permissions=permissions,
                          modules=modules),
             users=users or {})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _claimant(user_id=2001):
    patient = Patient.objects.create(user_id=user_id, display_name="Asha",
                                     kind="employee")
    visit = Visit.objects.create(patient=patient, user_id=user_id,
                                 recorded_by=1002, notes="v")
    rx = Prescription.objects.create(visit=visit, patient=patient, user_id=user_id,
                                     medicine="Paracetamol", recorded_by=1002)
    return patient, rx


def test_fr_adv_anonymous_request_is_401(stub_iam):
    stub_iam()
    resp = APIClient().get(SCHEDULE)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "not_authenticated"


def test_fr_adv_plain_user_without_module_grant_is_403(stub_iam, user_ref):
    c = _client(stub_iam, permissions=("phc.schedule.view",), modules=(),
                users={1001: user_ref(1001, kind="patient")})
    resp = c.get(SCHEDULE)
    assert resp.status_code == 403
    assert "module" in resp.json()["error"]["message"].lower()


def test_fr_adv_module_only_without_permission_is_403(stub_iam, user_ref):
    c = _client(stub_iam, permissions=(), modules=("phc",),
                users={1001: user_ref(1001, kind="patient")})
    resp = c.get(SCHEDULE)
    assert resp.status_code == 403
    assert "permission" in resp.json()["error"]["message"].lower()


def test_fr_adv_permission_only_without_module_grant_is_403(stub_iam, user_ref):
    c = _client(stub_iam, permissions=("phc.schedule.view",), modules=(),
                users={1001: user_ref(1001, kind="patient")})
    assert c.get(SCHEDULE).status_code == 403


def test_fr_adv_both_gates_allow(stub_iam, user_ref):
    c = _client(stub_iam, permissions=("phc.schedule.view",), modules=("phc",),
                users={1001: user_ref(1001, kind="patient")})
    assert c.get(SCHEDULE).status_code == 200


def test_fr_adv_invalid_limit_is_400_with_actionable_message(stub_iam, user_ref):
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.audit.view",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.get("/api/v1/phc/audit/log?limit=abc")
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "bad_request"
    assert "whole number" in error["message"]
    assert error["request_id"]


def test_fr_adv_out_of_range_limit_is_400(stub_iam, user_ref):
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.audit.view",),
                users={1002: user_ref(1002, kind="staff")})
    assert c.get("/api/v1/phc/audit/log?limit=0").status_code == 400
    assert c.get("/api/v1/phc/audit/log?limit=201").status_code == 400


def test_fr_adv_over_deduction_is_422(stub_iam, user_ref):
    item = InventoryItem.objects.create(name="Gloves", quantity=5,
                                        reorder_threshold=2)
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": 6, "direction": "deduct"},
                  format="json")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_deduction"
    item.refresh_from_db()
    assert item.quantity == 5
    assert not StockAdjustment.objects.filter(item=item).exists()


def test_fr_adv_unknown_requisition_item_is_422(stub_iam, user_ref):
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.requisition.submit",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post("/api/v1/phc/staff/requisitions",
                  {"items": [{"item_id": 99999, "quantity": 1}]}, format="json")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_requisition_item"


def test_fr_adv_future_expense_date_is_400(stub_iam, user_ref):
    _, rx = _claimant()
    future = (timezone.localdate() + dt.timedelta(days=1)).isoformat()
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="employee")})
    resp = c.post("/api/v1/phc/claims",
                  {"prescription_id": rx.id, "expense_date": future,
                   "amount": "100.00"}, format="json")
    assert resp.status_code == 400
    assert "expense_date" in str(resp.json()["error"]["details"])


def test_fr_adv_throttles_repeated_submissions(stub_iam, user_ref):
    _, rx = _claimant()
    c = _client(stub_iam, user_id=2001, kind="employee",
                permissions=("phc.reimbursement.submit",),
                users={2001: user_ref(2001, kind="employee")})
    payload = {"prescription_id": rx.id,
               "expense_date": timezone.localdate().isoformat(),
               "amount": "100.00"}
    responses = [c.post("/api/v1/phc/claims", payload, format="json")
                 for _ in range(11)]
    assert [r.status_code for r in responses[:10]] == [201] * 10
    assert responses[10].status_code == 429
    assert responses[10].json()["error"]["code"] == "throttled"


def test_fr_adv_oversized_integers_are_validation_errors(stub_iam, user_ref):
    item = InventoryItem.objects.create(name="Gloves", quantity=5,
                                        reorder_threshold=2)
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust", "phc.requisition.submit"),
                users={1002: user_ref(1002, kind="staff")})
    huge = 10 ** 12
    assert c.post("/api/v1/phc/staff/inventory/items",
                  {"name": "Mask", "reorder_threshold": huge},
                  format="json").status_code == 400
    assert c.post("/api/v1/phc/staff/inventory/adjust",
                  {"item_id": item.id, "quantity": huge, "direction": "add"},
                  format="json").status_code == 400
    assert c.post("/api/v1/phc/staff/requisitions",
                  {"items": [{"item_id": item.id, "quantity": huge}]},
                  format="json").status_code == 400


def test_fr_adv_negative_reorder_threshold_is_validation_error(stub_iam, user_ref):
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust",),
                users={1002: user_ref(1002, kind="staff")})
    resp = c.post("/api/v1/phc/staff/inventory/items",
                  {"name": "Mask", "reorder_threshold": -(10 ** 12)},
                  format="json")
    assert resp.status_code == 400
    assert "reorder_threshold" in str(resp.json()["error"]["details"])
    assert InventoryItem.objects.count() == 0


def test_fr_adv_cumulative_stock_add_cannot_overflow_int4(stub_iam, user_ref):
    item = InventoryItem.objects.create(name="Gloves", quantity=0,
                                        reorder_threshold=2)
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.inventory.adjust",),
                users={1002: user_ref(1002, kind="staff")})
    path = "/api/v1/phc/staff/inventory/adjust"
    first = c.post(path, {"item_id": item.id, "quantity": 2_000_000_000,
                          "direction": "add"}, format="json")
    assert first.status_code == 201
    second = c.post(path, {"item_id": item.id, "quantity": 2_000_000_000,
                           "direction": "add"}, format="json")
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "stock_overflow"
    item.refresh_from_db()
    assert item.quantity == 2_000_000_000
    assert StockAdjustment.objects.filter(item=item).count() == 1


def test_fr_adv_oversized_text_fields_are_validation_errors(stub_iam, user_ref):
    patient, existing_rx = _claimant()
    item = InventoryItem.objects.create(name="Gloves", quantity=5,
                                        reorder_threshold=2)
    staff = _client(stub_iam, user_id=1002, kind="staff",
                    permissions=("phc.records.manage", "phc.inventory.adjust"),
                    users={1002: user_ref(1002, kind="staff")})
    rx = staff.post("/api/v1/phc/staff/prescriptions",
                    {"visit_id": existing_rx.visit_id,
                     "patient_id": patient.user_id,
                     "medicine": "Paracetamol", "dosage": "x" * 500},
                    format="json")
    assert rx.status_code == 400
    assert "dosage" in str(rx.json()["error"]["details"])

    created = staff.post("/api/v1/phc/staff/inventory/items",
                         {"name": "Mask", "unit": "x" * 100}, format="json")
    assert created.status_code == 400
    assert "unit" in str(created.json()["error"]["details"])
    assert InventoryItem.objects.count() == 1

    adjusted = staff.post("/api/v1/phc/staff/inventory/adjust",
                          {"item_id": item.id, "quantity": 1,
                           "direction": "add", "reason": "x" * 500},
                          format="json")
    assert adjusted.status_code == 400
    assert "reason" in str(adjusted.json()["error"]["details"])
    assert StockAdjustment.objects.count() == 0


def test_fr_adv_duplicate_doctor_day_schedule_is_conflict(stub_iam, user_ref):
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.schedule.manage",),
                users={1002: user_ref(1002, kind="staff")})
    payload = {"doctor_name": "Dr A", "day_of_week": 1,
               "start_time": "09:00", "end_time": "13:00"}
    assert c.post("/api/v1/phc/staff/schedule", payload,
                  format="json").status_code == 201
    duplicate = c.post("/api/v1/phc/staff/schedule", payload, format="json")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "schedule_exists"

    DoctorSchedule.objects.create(
        doctor_name="Dr B", day_of_week=2, start_time="09:00", end_time="13:00")
    other = DoctorSchedule.objects.create(
        doctor_name="Dr B", day_of_week=3, start_time="09:00", end_time="13:00")
    clash = c.patch(f"/api/v1/phc/staff/schedule/{other.id}",
                    {"day_of_week": 2}, format="json")
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "schedule_exists"
    other.refresh_from_db()
    assert other.day_of_week == 3
    assert DoctorSchedule.objects.count() == 3


def test_fr_adv_requisition_originator_is_projected_from_iam(stub_iam, user_ref):
    item = InventoryItem.objects.create(name="Gloves", quantity=5,
                                        reorder_threshold=2)
    c = _client(stub_iam, user_id=1002, kind="staff",
                permissions=("phc.requisition.submit",),
                users={1002: user_ref(1002, kind="staff")})
    assert not Patient.objects.filter(user_id=1002).exists()
    resp = c.post("/api/v1/phc/staff/requisitions",
                  {"items": [{"item_id": item.id, "quantity": 1}]},
                  format="json")
    assert resp.status_code == 201
    profile = Patient.objects.get(user_id=1002)
    assert profile.kind == "staff"
    assert Requisition.objects.get(pk=resp.json()["requisition_id"]).originator_id == 1002


def test_fr_adv_query_budget_is_constant_in_row_count(stub_iam, user_ref):
    c = _client(stub_iam, permissions=("phc.schedule.view",),
                users={1001: user_ref(1001, kind="patient")})
    with CaptureQueriesContext(connection) as small:
        c.get(SCHEDULE)
    for n in range(30):
        DoctorSchedule.objects.create(doctor_name=f"Dr {n}", day_of_week=n % 7,
                                      start_time="09:00", end_time="17:00",
                                      is_published=True, published_by=1)
    with CaptureQueriesContext(connection) as large:
        resp = c.get(SCHEDULE)
    assert resp.status_code == 200
    assert len(resp.json()["schedules"]) == 30
    assert len(small) == len(large)
