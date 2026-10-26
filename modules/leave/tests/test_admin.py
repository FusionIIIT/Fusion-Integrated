"""Configuration revisions, calendar publication, offline records and adjustments (UC-014 to 018)."""
from datetime import date
from decimal import Decimal as D

import pytest

from modules.leave.models import (
    HolidayCalendar,
    LeaveRequest,
    LedgerEntry,
    PolicyRevision,
    RequestEvent,
    Task,
)
from modules.leave.services import readiness
from modules.leave.tests.conftest import FACULTY_CSE, HRADMIN, STAFF_RO, apply_payload

pytestmark = pytest.mark.django_db


def admin(client_for):
    return client_for(HRADMIN)


def test_policy_revision_governs_immediately_and_keeps_history(configured, client_for):
    c = admin(client_for)
    current = c.get("/api/v1/leave/admin/policy").json()
    rules = [{**r, "annual_entitlement": "10.0"} if r["category"] == "CL" else r
             for r in current["rules"]]
    r = c.post("/api/v1/leave/admin/policy", {**current, "rules": rules, "note": "OO 12"},
               format="json")
    assert r.status_code == 201, r.content
    assert PolicyRevision.objects.count() == 2
    assert next(x for x in r.json()["rules"] if x["category"] == "CL")["annual_entitlement"] == (
        "10.0")


def test_invalid_policy_is_not_saved_and_says_why(configured, client_for):
    c = admin(client_for)
    current = c.get("/api/v1/leave/admin/policy").json()
    r = c.post("/api/v1/leave/admin/policy", {**current, "rules": current["rules"][:3]},
               format="json")
    assert r.status_code == 422 and "missing" in r.json()["error"]["details"][0]["message"]
    assert PolicyRevision.objects.count() == 1


def test_hierarchy_rejects_a_designation_that_cannot_act(configured, client_for):
    c = admin(client_for)
    h = c.get("/api/v1/leave/admin/hierarchy").json()
    assert "HOD (CSE)" in h["choices"]["unit_head"]
    units = [*h["units"], {"department": "IWD", "unit_head_designation": "Junior Assistant",
                           "head_leave_designation": ""}]
    r = c.post("/api/v1/leave/admin/hierarchy", {"units": units, "routes": h["routes"]},
               format="json")
    assert r.status_code == 422
    assert "cannot review" in r.json()["error"]["details"][0]["message"]


def test_mapping_a_unit_lets_its_staff_apply(configured, client_for):
    c = admin(client_for)
    h = c.get("/api/v1/leave/admin/hierarchy").json()
    assert any("General Administration" in w for w in h["warnings"])
    units = [*h["units"], {"department": "General Administration",
                           "unit_head_designation": "Registrar",
                           "head_leave_designation": "Director"}]
    assert c.post("/api/v1/leave/admin/hierarchy", {"units": units, "routes": h["routes"]},
                  format="json").status_code == 201
    from modules.leave.tests.conftest import STAFF_GA

    r = client_for(STAFF_GA).post("/api/v1/leave/requests", apply_payload(), format="json")
    assert r.status_code == 201


def test_calendar_draft_does_not_govern_until_published(configured, client_for):
    c = admin(client_for)
    draft = c.post("/api/v1/leave/admin/calendars", {"year": 2026}, format="json").json()
    assert draft["status"] == "draft" and len(draft["holidays"]) == 4
    entries = [*draft["holidays"], {"date": "2026-03-09", "name": "New closed day",
                                    "kind": "closed"}]
    assert c.put(f"/api/v1/leave/admin/calendars/{draft['id']}", {"holidays": entries},
                 format="json").status_code == 200
    me = client_for(FACULTY_CSE)
    assert me.post("/api/v1/leave/requests", apply_payload(start="2026-03-09"),
                   format="json").status_code == 201
    c = admin(client_for)
    pub = c.post(f"/api/v1/leave/admin/calendars/{draft['id']}/publish", format="json")
    assert pub.json()["status"] == "published"
    assert HolidayCalendar.objects.filter(year=2026, status="superseded").count() == 1
    r = client_for(FACULTY_CSE).post("/api/v1/leave/requests",
                                     apply_payload(start="2026-03-09", half="first"),
                                     format="json")
    assert r.json()["error"]["code"] in ("no_chargeable_days", "overlaps_own_leave")


def test_a_published_calendar_is_never_edited(configured, client_for):
    pub = HolidayCalendar.objects.get(year=2026, status="published")
    r = admin(client_for).put(f"/api/v1/leave/admin/calendars/{pub.pk}", {"holidays": []},
                              format="json")
    assert r.json()["error"]["code"] == "calendar_not_draft"


def test_offline_record_is_synchronisation_not_sanction(configured, client_for):
    r = admin(client_for).post("/api/v1/leave/admin/records/offline", {
        "user_id": STAFF_RO, "category": "EL", "start_date": "2026-02-23",
        "end_date": "2026-02-25", "sanction_reference": "Estt/OO/2026/41",
        "reason": "server_unavailable"}, format="json")
    assert r.status_code == 201, r.content
    req = LeaveRequest.objects.get(pk=r.json()["id"])
    assert (req.status, req.source, req.decision, req.days) == ("approved", "offline", "", D(3))
    assert not Task.objects.filter(request=req).exists()
    assert RequestEvent.objects.filter(request=req, event="offline_recorded").exists()
    assert LedgerEntry.objects.get(request=req).delta == D(-3)


def test_offline_record_needs_evidence_and_consistency(configured, client_for):
    c = admin(client_for)
    base = {"user_id": STAFF_RO, "category": "EL", "start_date": "2026-02-23",
            "end_date": "2026-02-25", "reason": "illness"}
    assert c.post("/api/v1/leave/admin/records/offline", {**base, "sanction_reference": " "},
                  format="json").status_code in (400, 409)
    assert c.post("/api/v1/leave/admin/records/offline",
                  {**base, "sanction_reference": "OO-1", "start_date": "2026-04-01",
                   "end_date": "2026-04-02"}, format="json").json()["error"]["code"] == (
        "invalid_period")
    assert c.post("/api/v1/leave/admin/records/offline",
                  {**base, "sanction_reference": "OO-1", "category": "VL"},
                  format="json").json()["error"]["code"] == "category_not_applicable"
    c.post("/api/v1/leave/admin/records/offline", {**base, "sanction_reference": "OO-1"},
           format="json")
    r = c.post("/api/v1/leave/admin/records/offline", {**base, "sanction_reference": "OO-2"},
               format="json")
    assert r.json()["error"]["code"] == "overlaps_own_leave"


def test_adjustment_is_an_entry_with_an_idempotent_reference(configured, client_for):
    c = admin(client_for)
    body = {"user_id": FACULTY_CSE, "year": 2026, "category": "COL", "delta": "12.0",
            "reference": "Opening balance 2026", "note": "Migrated from paper register"}
    assert c.post("/api/v1/leave/admin/records/adjustments", body, format="json").status_code == 201
    r = c.post("/api/v1/leave/admin/records/adjustments", body, format="json")
    assert r.json()["error"]["code"] == "duplicate_reference"
    # One office order may correct several categories or years.
    assert c.post("/api/v1/leave/admin/records/adjustments", {**body, "category": "EL"},
                  format="json").status_code == 201
    r = c.post("/api/v1/leave/admin/records/adjustments",
               {**body, "delta": "-500", "reference": "x"}, format="json")
    assert r.status_code in (400, 409)


def test_adjustment_cannot_take_a_balance_negative(configured, client_for):
    r = admin(client_for).post("/api/v1/leave/admin/records/adjustments", {
        "user_id": FACULTY_CSE, "year": 2026, "category": "CL", "delta": "-9",
        "reference": "OO-3", "note": "Correction"}, format="json")
    assert r.json()["error"]["code"] == "insufficient_balance"


def test_sla_validation(configured, client_for):
    c = admin(client_for)
    bad = {"rules": [{"step": "unit_head", "reminder_hours": 48, "escalation_hours": 24,
                      "action": "reassign", "escalate_to": "Junior Assistant"},
                     {"step": "substitute", "reminder_hours": 12, "escalation_hours": 24,
                      "action": "reassign", "escalate_to": "Director"}]}
    r = c.post("/api/v1/leave/admin/sla", bad, format="json")
    assert r.status_code == 422 and len(r.json()["error"]["details"]) >= 3
    good = {"rules": [{"step": "unit_head", "reminder_hours": 24, "escalation_hours": 72,
                       "action": "reassign", "escalate_to": "Director"}]}
    assert c.post("/api/v1/leave/admin/sla", good, format="json").status_code == 201


def test_readiness_names_what_is_missing(db):
    unmet = readiness.unmet()
    assert any("policy" in u for u in unmet) and any("calendar" in u for u in unmet)


def test_readiness_is_clean_once_configured(configured):
    assert readiness.unmet() == []


def test_a_fresh_installation_does_not_500(people, client_for):
    me = client_for(FACULTY_CSE)
    assert me.get("/api/v1/leave/overview").json()["configured"] is False
    r = me.post("/api/v1/leave/requests", apply_payload(), format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_configured"


def test_vacation_periods(configured, client_for):
    c = admin(client_for)
    r = c.post("/api/v1/leave/admin/vacations", {"label": "Winter", "start_date": "2026-12-20",
                                                 "end_date": "2026-12-31"}, format="json")
    assert r.status_code == 201
    assert c.post("/api/v1/leave/admin/vacations",
                  {"label": "Overlap", "start_date": "2026-12-30", "end_date": "2027-01-02"},
                  format="json").json()["error"]["code"] == "vacation_overlaps"
    assert c.delete(f"/api/v1/leave/admin/vacations/{r.json()['id']}").status_code == 204
    cal = client_for(FACULTY_CSE).get("/api/v1/leave/calendar?year=2026").json()
    assert cal["published"] and [v["label"] for v in cal["vacations"]] == ["Summer 2026"]
    assert date.fromisoformat(cal["holidays"][0]["date"]).year == 2026


def test_a_vacation_period_with_vl_in_it_cannot_be_removed(configured, client_for):
    r = client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(
        "VL", start=date(2026, 5, 18), end=date(2026, 5, 22)), format="json")
    assert r.status_code == 201, r.content
    c = admin(client_for)
    [summer] = c.get("/api/v1/leave/admin/vacations").json()
    r = c.delete(f"/api/v1/leave/admin/vacations/{summer['id']}")
    assert r.status_code == 409 and r.json()["error"]["code"] == "vacation_in_use"
