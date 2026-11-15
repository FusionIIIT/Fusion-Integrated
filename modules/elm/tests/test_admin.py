"""Policy, calendar and offline records (EL-UC-014..016)."""
from datetime import date

import pytest

from modules.elm import registry
from modules.elm.domain.policy import DEFAULT_PARAMS
from modules.elm.models import LedgerEntry
from modules.elm.tests.conftest import ADM, ADMIN, FAC

pytestmark = pytest.mark.django_db


def _admin(as_user):
    return as_user(ADM, ADMIN, kind="staff", roles=("Leave Administrator",))


def test_publishing_a_policy_never_edits_a_published_one(as_user, policy):
    c = _admin(as_user)
    body = {"name": "v2", "params": DEFAULT_PARAMS, "hierarchy": registry.DEFAULT_HIERARCHY,
            "effective_from": "2001-01-01"}
    pk = c.post("/api/v1/elm/admin/policies", body, format="json").json()["id"]
    assert c.post(f"/api/v1/elm/admin/policies/{pk}/publish").json()["status"] == "published"
    r = c.put(f"/api/v1/elm/admin/policies/{pk}", body, format="json")
    assert r.json()["error"]["code"] == "policy_published"


def test_hierarchy_naming_a_role_without_decision_rights_is_refused(as_user, policy):
    h = {**registry.DEFAULT_HIERARCHY, "establishment_role": "Driver"}
    r = _admin(as_user).post("/api/v1/elm/admin/policies",
                             {"name": "bad", "params": DEFAULT_PARAMS, "hierarchy": h,
                              "effective_from": "2001-01-01"}, format="json")
    assert r.status_code == 400 and "Driver" in r.json()["error"]["message"]


def test_calendar_draft_then_publish(as_user, policy):
    c = _admin(as_user)
    body = {"name": "2027", "effective_from": "2027-01-01", "entries": [
        {"kind": "restricted_holiday", "name": "Holi", "start_date": "2027-03-22",
         "end_date": "2027-03-22"}]}
    pk = c.post("/api/v1/elm/admin/calendars", body, format="json").json()["id"]
    assert c.post(f"/api/v1/elm/admin/calendars/{pk}/publish").json()["status"] == "published"


def test_offline_record_debits_and_keeps_evidence(as_user, policy, calendar):
    r = _admin(as_user).post("/api/v1/elm/admin/offline", {
        "user_id": FAC, "category": "CL", "start_date": "2026-01-05",
        "end_date": "2026-01-06", "sanction_reference": "EST/12/2026",
        "sanctioned_by": "HOD (CSE)", "sanctioned_on": date(2026, 1, 2).isoformat()},
        format="json")
    assert r.status_code == 201, r.json()
    assert r.json()["leave"]["status"] == "approved"
    debit = LedgerEntry.objects.get(user_id=FAC, entry_type="offline_debit")
    assert debit.delta == -2


def test_offline_record_needs_evidence(as_user, policy, calendar):
    r = _admin(as_user).post("/api/v1/elm/admin/offline", {
        "user_id": FAC, "category": "CL", "start_date": "2026-01-05",
        "end_date": "2026-01-05", "sanction_reference": " ", "sanctioned_by": "x",
        "sanctioned_on": "2026-01-02"}, format="json")
    assert r.status_code in (400, 422)
