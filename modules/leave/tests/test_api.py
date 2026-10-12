"""The workflow, driven through the HTTP layer end to end (EL-UC-001…011).

Scoping is asserted by 404, permission by 403/400, rules by the status and
balance the API actually reports — the same seams production relies on.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.leave.models import (
    LeaveBalance,
    LeaveNotification,
    LeaveRequest,
)
from modules.leave.tests.conftest import (
    ADMIN,
    APPLICANT,
    AUTH,
    DEAN,
    DIRECTOR,
    ESTABLISHMENT,
    EST,
    OTHER,
    SELF,
    SUBSTITUTE,
    UH,
    UNIT_HEAD,
    UNPLACED,
)

pytestmark = pytest.mark.django_db


def _submit(c, **overrides):
    payload = {"category": "cl", "start_date": "2026-10-20",
               "end_date": "2026-10-22", "purpose": "home work"}
    payload.update(overrides)
    return c.post("/api/v1/leave/requests", payload, format="json")


# -- EL-UC-001: apply --------------------------------------------------------
def test_cl_application_reaches_the_unit_head_desk(stub_iam, desks, client):
    c = client(APPLICANT, permissions=SELF)
    body = _submit(c).json()
    assert body["status"] == "awaiting_unit_head_review"
    assert body["chargeable_days"] == "3.00"      # Tue–Thu, all working days
    assert "withdraw" in body["allowed_actions"]
    assert body["unit_head_user_id"] is not None


def test_apply_without_create_permission_is_403(stub_iam, desks, client):
    c = client(APPLICANT, permissions=("leave.request.view_self",))
    assert _submit(c).status_code == 403


def test_insufficient_balance_is_a_400_with_a_code(stub_iam, desks, client):
    c = client(APPLICANT, permissions=SELF)
    r = _submit(c, start_date="2026-10-01", end_date="2026-10-30")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "insufficient_balance"


def test_half_day_cl_is_half_a_day(stub_iam, desks, client):
    c = client(APPLICANT, permissions=SELF)
    body = _submit(c, start_date="2026-10-20", end_date="2026-10-20",
                   half_day="first").json()
    assert body["chargeable_days"] == "0.50"


def test_rh_needs_a_published_restricted_day(stub_iam, desks, client):
    c = client(APPLICANT, permissions=SELF)
    bad = _submit(c, category="rh", start_date="2026-10-20",
                  end_date="2026-10-20")
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "rh_not_applicable"
    good = _submit(c, category="rh", start_date="2026-10-21",
                   end_date="2026-10-21")
    assert good.status_code == 201
    assert good.json()["chargeable_days"] == "1.00"


def test_vl_is_faculty_only(stub_iam, desks, client):
    c = client(APPLICANT, permissions=SELF)          # staff
    r = _submit(c, category="vl", start_date="2026-10-20",
                end_date="2026-10-20", substitute_user_id=SUBSTITUTE)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "category_not_applicable"


def test_no_unit_head_configured_is_a_409(stub_iam, desks, client):
    c = client(UNPLACED, permissions=SELF)
    r = _submit(c)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "no_unit_head"


# -- EL-UC-003: Unit Head ----------------------------------------------------
def test_unit_head_approves_cl_and_the_balance_follows(stub_iam, desks, client):
    pk = _submit(client(APPLICANT, permissions=SELF)).json()["id"]
    uh = client(UNIT_HEAD, kind="faculty", permissions=UH)
    body = uh.post(f"/api/v1/leave/requests/{pk}/review",
                   {"outcome": "approve", "note": "ok"}, format="json").json()
    assert body["status"] == "approved"
    assert body["decision"] == "approve"
    row = LeaveBalance.objects.get(user_id=APPLICANT, category="cl", year=2026)
    assert row.used == Decimal("3.00")
    assert row.available == 5.00                   # 8 credited − 3 used


def test_only_the_assigned_unit_head_may_review(stub_iam, desks, client):
    pk = _submit(client(APPLICANT, permissions=SELF)).json()["id"]
    other_head = client(OTHER, permissions=UH)
    r = other_head.post(f"/api/v1/leave/requests/{pk}/review",
                        {"outcome": "approve"}, format="json")
    assert r.status_code == 403


def test_not_recommended_is_not_final_for_higher_categories(
        stub_iam, desks, client):
    """BR-EL-017: the Unit Head's 'no' forwards, it does not kill the file."""
    c = client(APPLICANT, permissions=SELF)
    pk = _submit(c, category="el", start_date="2026-10-26",
                 end_date="2026-10-28",
                 substitute_user_id=SUBSTITUTE).json()["id"]
    sub = client(SUBSTITUTE, permissions=SELF)
    sub.post(f"/api/v1/leave/requests/{pk}/substitute/respond",
             {"response": "accept"}, format="json")
    uh = client(UNIT_HEAD, kind="faculty", permissions=UH)
    body = uh.post(f"/api/v1/leave/requests/{pk}/review",
                   {"outcome": "not_recommended"},
                   format="json").json()
    assert body["status"] == "awaiting_establishment_routing"
    assert body["unit_head_outcome"] == "not_recommended"


# -- EL-UC-002/019: substitute consent --------------------------------------
def test_el_needs_a_substitute_and_the_gate_blocks(stub_iam, desks, client):
    c = client(APPLICANT, permissions=SELF)
    r = _submit(c, category="el", start_date="2026-10-26",
                end_date="2026-10-28")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "substitute_required"

    body = _submit(c, category="el", start_date="2026-10-26",
                   end_date="2026-10-28",
                   substitute_user_id=SUBSTITUTE).json()
    assert body["status"] == "awaiting_substitute_response"

    # The gate holds: a review attempt is refused while consent is pending.
    uh = client(UNIT_HEAD, kind="faculty", permissions=UH)
    r = uh.post(f"/api/v1/leave/requests/{body['id']}/review",
                {"outcome": "approve"}, format="json")
    assert r.status_code == 409


def test_decline_parks_the_file_and_applicant_replaces(
        stub_iam, desks, client):
    c = client(APPLICANT, permissions=SELF)
    pk = _submit(c, category="el", start_date="2026-10-26",
                 end_date="2026-10-28",
                 substitute_user_id=SUBSTITUTE).json()["id"]
    sub = client(SUBSTITUTE, permissions=SELF)
    body = sub.post(f"/api/v1/leave/requests/{pk}/substitute/respond",
                    {"response": "decline"}, format="json").json()
    assert body["status"] == "applicant_action_required"
    assert body["substitute_status"] == "declined"
    assert "nominate_substitute" in body["allowed_actions"]

    # EL-UC-019: the applicant nominates someone else, back to the gate.
    body = c.post(f"/api/v1/leave/requests/{pk}/substitute",
                  {"substitute_user_id": OTHER}, format="json").json()
    assert body["status"] == "awaiting_substitute_response"
    assert body["substitute_user_id"] == OTHER


def test_substitute_cannot_respond_for_someone_elses_file(
        stub_iam, desks, client):
    pk = _submit(client(APPLICANT, permissions=SELF),
                 category="el", start_date="2026-10-26", end_date="2026-10-28",
                 substitute_user_id=SUBSTITUTE).json()["id"]
    intruder = client(OTHER, permissions=SELF)
    r = intruder.post(f"/api/v1/leave/requests/{pk}/substitute/respond",
                      {"response": "accept"}, format="json")
    assert r.status_code == 403


# -- EL-UC-004/005: establishment and final sanction ------------------------
def test_higher_category_walks_the_whole_hierarchy(stub_iam, desks, client):
    c = client(APPLICANT, permissions=SELF)
    pk = _submit(c, category="el", start_date="2026-10-26",
                 end_date="2026-10-28",
                 substitute_user_id=SUBSTITUTE).json()["id"]
    client(SUBSTITUTE, permissions=SELF).post(
        f"/api/v1/leave/requests/{pk}/substitute/respond",
        {"response": "accept"}, format="json")
    uh = client(UNIT_HEAD, kind="faculty", permissions=UH)
    assert uh.post(f"/api/v1/leave/requests/{pk}/review",
                   {"outcome": "recommended"}, format="json").json()[
        "status"] == "awaiting_establishment_routing"

    est = client(ESTABLISHMENT, permissions=EST)
    body = est.post(f"/api/v1/leave/requests/{pk}/route",
                    {"note": "record verified"}, format="json").json()
    assert body["status"] == "awaiting_final_sanction_decision"
    assert body["authority_user_id"] == DEAN

    dean = client(DEAN, kind="faculty", permissions=AUTH)
    body = dean.post(f"/api/v1/leave/requests/{pk}/sanction",
                     {"outcome": "approve", "reference": "EST/2026/9"},
                     format="json").json()
    assert body["status"] == "approved"
    row = LeaveBalance.objects.get(user_id=APPLICANT, category="el", year=2026)
    assert row.used == Decimal("3.00")


def test_wrong_authority_cannot_sanction(stub_iam, desks, client):
    pk = _submit(client(APPLICANT, permissions=SELF),
                 category="el", start_date="2026-10-26", end_date="2026-10-28",
                 substitute_user_id=SUBSTITUTE).json()["id"]
    client(SUBSTITUTE, permissions=SELF).post(
        f"/api/v1/leave/requests/{pk}/substitute/respond",
        {"response": "accept"}, format="json")
    client(UNIT_HEAD, kind="faculty", permissions=UH).post(
        f"/api/v1/leave/requests/{pk}/review", {"outcome": "recommended"},
        format="json")
    client(ESTABLISHMENT, permissions=EST).post(
        f"/api/v1/leave/requests/{pk}/route", {}, format="json")
    # The Director holds `sanction` but is not this file's authority.
    r = client(DIRECTOR, kind="faculty", permissions=AUTH).post(
        f"/api/v1/leave/requests/{pk}/sanction", {"outcome": "approve"},
        format="json")
    assert r.status_code == 403


# -- BR-EL-020: Director self-sanction --------------------------------------
def test_director_sanctions_their_own_file(stub_iam, desks, client):
    body = _submit(client(DIRECTOR, kind="faculty", permissions=SELF),
                   start_date="2026-10-26", end_date="2026-10-27").json()
    assert body["status"] == "awaiting_director_self_sanction"
    assert body["is_director_self_sanction"] is True

    body = client(DIRECTOR, kind="faculty", permissions=AUTH).post(
        f"/api/v1/leave/requests/{body['id']}/sanction",
        {"outcome": "approve", "note": "self"}, format="json").json()
    assert body["status"] == "approved"


# -- BR-EL self-approval guard: a Unit Head's own file ------------------------
def test_unit_heads_own_file_skips_their_desk(stub_iam, desks, client):
    body = _submit(client(UNIT_HEAD, kind="faculty", permissions=SELF),
                   start_date="2026-10-26", end_date="2026-10-27").json()
    assert body["status"] == "awaiting_establishment_routing"
    assert body["establishment_user_id"] == ESTABLISHMENT


# -- BR-EL-022: withdrawal ---------------------------------------------------
def test_withdraw_is_immediate_and_scoped(stub_iam, desks, client):
    pk = _submit(client(APPLICANT, permissions=SELF)).json()["id"]
    body = client(APPLICANT, permissions=SELF).post(
        f"/api/v1/leave/requests/{pk}/withdraw", format="json").json()
    assert body["status"] == "withdrawn"
    # A withdrawn file consumes nothing.
    assert not LeaveBalance.objects.filter(user_id=APPLICANT,
                                           used__gt=0).exists()
    # Someone uninvolved cannot even see it existed.
    r = client(OTHER, permissions=SELF).get(
        f"/api/v1/leave/requests/{pk}")
    assert r.status_code == 404


def test_cannot_withdraw_an_approved_leave(stub_iam, desks, client):
    pk = _submit(client(APPLICANT, permissions=SELF)).json()["id"]
    client(UNIT_HEAD, kind="faculty", permissions=UH).post(
        f"/api/v1/leave/requests/{pk}/review", {"outcome": "approve"},
        format="json")
    r = client(APPLICANT, permissions=SELF).post(
        f"/api/v1/leave/requests/{pk}/withdraw", format="json")
    assert r.status_code == 409


# -- EL-UC-006/008/011: cancellation, extension, resumption ------------------
def _approve_cl(client) -> int:
    pk = _submit(client(APPLICANT, permissions=SELF)).json()["id"]
    client(UNIT_HEAD, kind="faculty", permissions=UH).post(
        f"/api/v1/leave/requests/{pk}/review", {"outcome": "approve"},
        format="json")
    return pk


def test_cancellation_restores_the_balance(stub_iam, desks, client):
    base_pk = _approve_cl(client)
    derived = client(APPLICANT, permissions=SELF).post(
        f"/api/v1/leave/requests/{base_pk}/cancellation",
        {"reason": "plans changed"}, format="json").json()
    assert derived["kind"] == "cancellation"
    assert derived["status"] == "awaiting_unit_head_review"

    client(UNIT_HEAD, kind="faculty", permissions=UH).post(
        f"/api/v1/leave/requests/{derived['id']}/review",
        {"outcome": "approve"}, format="json")
    base = LeaveRequest.objects.get(pk=base_pk)
    assert base.status == "cancelled"
    row = LeaveBalance.objects.get(user_id=APPLICANT, category="cl", year=2026)
    assert row.used == Decimal("0.00")


def test_extension_charges_only_the_increment(stub_iam, desks, client):
    c = client(APPLICANT, permissions=SELF)
    pk = _submit(c, category="el", start_date="2026-10-26",
                 end_date="2026-10-28",
                 substitute_user_id=SUBSTITUTE).json()["id"]
    client(SUBSTITUTE, permissions=SELF).post(
        f"/api/v1/leave/requests/{pk}/substitute/respond",
        {"response": "accept"}, format="json")
    client(UNIT_HEAD, kind="faculty", permissions=UH).post(
        f"/api/v1/leave/requests/{pk}/review", {"outcome": "recommended"},
        format="json")
    client(ESTABLISHMENT, permissions=EST).post(
        f"/api/v1/leave/requests/{pk}/route", {}, format="json")
    client(DEAN, kind="faculty", permissions=AUTH).post(
        f"/api/v1/leave/requests/{pk}/sanction", {"outcome": "approve"},
        format="json")

    derived = c.post(f"/api/v1/leave/requests/{pk}/extension",
                     {"new_end_date": "2026-10-30",
                      "substitute_user_id": SUBSTITUTE,
                      "reason": "still unwell"}, format="json").json()
    assert derived["kind"] == "extension"
    assert derived["start_date"] == "2026-10-29"      # day after current end
    assert derived["chargeable_days"] == "2.00"

    client(SUBSTITUTE, permissions=SELF).post(
        f"/api/v1/leave/requests/{derived['id']}/substitute/respond",
        {"response": "accept"}, format="json")
    client(UNIT_HEAD, kind="faculty", permissions=UH).post(
        f"/api/v1/leave/requests/{derived['id']}/review",
        {"outcome": "recommended"}, format="json")
    client(ESTABLISHMENT, permissions=EST).post(
        f"/api/v1/leave/requests/{derived['id']}/route", {}, format="json")
    client(DEAN, kind="faculty", permissions=AUTH).post(
        f"/api/v1/leave/requests/{derived['id']}/sanction",
        {"outcome": "approve"}, format="json")

    base = LeaveRequest.objects.get(pk=pk)
    assert base.end_date == date(2026, 10, 30)
    assert base.chargeable_days == Decimal("5.00")
    row = LeaveBalance.objects.get(user_id=APPLICANT, category="el", year=2026)
    assert row.used == Decimal("5.00")


def test_resumption_refund_after_early_return(stub_iam, desks, client):
    c = client(APPLICANT, permissions=SELF)
    pk = _submit(c, category="el", start_date="2026-10-26",
                 end_date="2026-10-28",
                 substitute_user_id=SUBSTITUTE).json()["id"]
    client(SUBSTITUTE, permissions=SELF).post(
        f"/api/v1/leave/requests/{pk}/substitute/respond",
        {"response": "accept"}, format="json")
    client(UNIT_HEAD, kind="faculty", permissions=UH).post(
        f"/api/v1/leave/requests/{pk}/review", {"outcome": "recommended"},
        format="json")
    client(ESTABLISHMENT, permissions=EST).post(
        f"/api/v1/leave/requests/{pk}/route", {}, format="json")
    client(DEAN, kind="faculty", permissions=AUTH).post(
        f"/api/v1/leave/requests/{pk}/sanction", {"outcome": "approve"},
        format="json")

    resumption = c.post(f"/api/v1/leave/requests/{pk}/resumption",
                        {"actual_date": "2026-10-27",
                         "details": "joined early"}, format="json").json()
    assert resumption["status"] == "pending_review"
    assert resumption["approved_end_date"] == "2026-10-28"

    reviewed = client(DEAN, kind="faculty", permissions=AUTH).post(
        f"/api/v1/leave/resumptions/{resumption['id']}/review",
        {"note": "noted"}, format="json").json()
    assert reviewed["status"] == "reviewed_early"
    assert reviewed["adjustment_days"] == "-1"
    row = LeaveBalance.objects.get(user_id=APPLICANT, category="el", year=2026)
    assert row.used == Decimal("2.00")


# -- scoping and permissions -------------------------------------------------
def test_sees_only_own_requests_without_the_view_permission(
        stub_iam, desks, client):
    _submit(client(APPLICANT, permissions=SELF))
    rows = client(OTHER, permissions=SELF).get(
        "/api/v1/leave/requests").json()["results"]
    assert rows == []
    rows = client(DEAN, kind="faculty",
                  permissions=AUTH).get(
        "/api/v1/leave/requests").json()["results"]
    assert len(rows) == 1                          # AUTH includes view


def test_cross_user_balance_needs_the_scope_permission(stub_iam, desks, client):
    _submit(client(APPLICANT, permissions=SELF))
    r = client(OTHER, permissions=SELF).get(
        f"/api/v1/leave/balances?user_id={APPLICANT}")
    assert r.status_code == 403
    r = client(OTHER, permissions=ADMIN).get(
        f"/api/v1/leave/balances?user_id={APPLICANT}")
    assert r.status_code == 200
    assert {b["category"] for b in r.json()["results"]} >= {"cl", "el"}


def test_own_balance_is_readable_by_employees(stub_iam, desks, client):
    body = client(APPLICANT, permissions=SELF).get(
        "/api/v1/leave/balances?year=2026").json()
    cl = next(b for b in body["results"] if b["category"] == "cl")
    assert cl["available"] == 8.0
    # Staff have no VL track (BR-EL-006).
    assert all(b["category"] != "vl" for b in body["results"])


# -- BR-EL-029: offline records ---------------------------------------------
def test_offline_record_is_approved_with_its_reference(stub_iam, desks, client):
    admin = client(ESTABLISHMENT, permissions=ADMIN)
    body = admin.post("/api/v1/leave/admin/offline-leave",
                      {"user_id": APPLICANT, "category": "cl",
                       "start_date": "2026-10-05", "end_date": "2026-10-06",
                       "sanction_reference": "ORD-77/2026"},
                      format="json").json()
    assert body["status"] == "approved"
    assert body["source"] == "offline"
    assert body["sanction_reference"] == "ORD-77/2026"
    row = LeaveBalance.objects.get(user_id=APPLICANT, category="cl", year=2026)
    assert row.used == Decimal("2.00")


def test_offline_record_without_a_reference_is_refused(
        stub_iam, desks, client):
    admin = client(ESTABLISHMENT, permissions=ADMIN)
    r = admin.post("/api/v1/leave/admin/offline-leave",
                   {"user_id": APPLICANT, "category": "cl",
                    "start_date": "2026-10-05", "end_date": "2026-10-06",
                    "sanction_reference": "   "}, format="json")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "reference_required"


# -- BR-EL-035: tasks and notifications -------------------------------------
def test_assignment_notifies_the_next_desk(stub_iam, desks, client):
    _submit(client(APPLICANT, permissions=SELF))
    rows = LeaveNotification.objects.filter(user_id=9001, kind="assigned")
    assert rows.exists()
    assert "needs your action" in rows.first().message


def test_tasks_page_lists_what_is_waiting_on_me(stub_iam, desks, client):
    _submit(client(APPLICANT, permissions=SELF))
    rows = client(UNIT_HEAD, kind="faculty",
                  permissions=UH).get("/api/v1/leave/tasks").json()["results"]
    assert len(rows) == 1
    assert rows[0]["status"] == "awaiting_unit_head_review"


# -- administration ----------------------------------------------------------
def test_policy_put_needs_its_permission(stub_iam, desks, client):
    r = client(APPLICANT, permissions=SELF).put(
        "/api/v1/leave/policy", {"cl_annual": "10"}, format="json")
    assert r.status_code == 403
    body = client(OTHER, permissions=ADMIN).put(
        "/api/v1/leave/policy", {"cl_annual": "10"}, format="json").json()
    assert body["cl_annual"] == "10.00"
