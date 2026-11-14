"""End-to-end workflows through the API, ordinary cases first (WF-EL-01..05)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.elm.models import LeaveRequest, LedgerEntry
from modules.elm.tests.conftest import (
    DIR,
    DR,
    EMPLOYEE,
    ESTT,
    FAC,
    FAC2,
    HOD,
    REG,
    SANCTION,
    STF,
    UNIT_HEAD,
    leave,
    monday,
)

pytestmark = pytest.mark.django_db

HOD_ROLES = ("faculty", "HOD (CSE)")


def _apply(as_user, uid, body, kind="faculty", roles=None):
    return as_user(uid, EMPLOYEE, kind=kind, roles=roles).post(
        "/api/v1/elm/requests", body, format="json")


def _hod(as_user):
    return as_user(HOD, EMPLOYEE + UNIT_HEAD, roles=HOD_ROLES, active_role="HOD (CSE)")


def _balance(uid, cat):
    return sum(e.delta for e in LedgerEntry.objects.filter(user_id=uid, category=cat))


def test_plain_faculty_applies_cl_and_unit_head_approves(as_user, policy, calendar):
    r = _apply(as_user, FAC, leave("CL", days=2))
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["status"] == "awaiting_unit_head"
    assert body["current_role"] == "HOD (CSE)"
    assert Decimal(body["days"]) == 2

    queue = _hod(as_user).get("/api/v1/elm/queue").json()["results"]
    assert [q["id"] for q in queue] == [body["id"]]
    assert queue[0]["allowed_decisions"] == ["approve", "reject"]

    r = _hod(as_user).post(f"/api/v1/elm/queue/{body['id']}/decide",
                           {"event": "approve"}, format="json")
    assert r.json()["status"] == "approved"
    assert _balance(FAC, "CL") == 6


def test_staff_el_goes_through_estt_to_registrar(as_user, policy, calendar):
    r = _apply(as_user, STF, leave("EL", days=7), kind="staff")
    pk = r.json()["id"]
    hod = _hod(as_user)
    assert hod.post(f"/api/v1/elm/queue/{pk}/decide", {"event": "approve"},
                    format="json").status_code == 400
    r = hod.post(f"/api/v1/elm/queue/{pk}/decide",
                 {"event": "not_recommend", "note": "short staffed"}, format="json")
    assert r.json()["status"] == "awaiting_establishment"
    assert r.json()["recommendation"] == "not_recommended"

    dr = as_user(DR, EMPLOYEE + ESTT, kind="staff", roles=("staff", "Deputy Registrar"),
                 active_role="Deputy Registrar")
    r = dr.post(f"/api/v1/elm/queue/{pk}/decide", {"event": "forward"}, format="json")
    assert r.json()["status"] == "awaiting_sanction"
    assert r.json()["current_role"] == "Registrar"

    reg = as_user(REG, EMPLOYEE + SANCTION, kind="staff", roles=("staff", "Registrar"),
                  active_role="Registrar")
    r = reg.post(f"/api/v1/elm/queue/{pk}/decide", {"event": "approve"}, format="json")
    assert r.json()["status"] == "approved"
    assert _balance(STF, "EL") == 23


def test_director_self_sanction(as_user, policy, calendar):
    roles = ("faculty", "Director")
    c = as_user(DIR, EMPLOYEE + SANCTION, roles=roles, active_role="faculty")
    r = c.post("/api/v1/elm/requests", leave("CL"), format="json")
    assert r.json()["status"] == "awaiting_director"
    pk = r.json()["id"]
    d = as_user(DIR, EMPLOYEE + SANCTION, roles=roles, active_role="Director")
    assert [q["id"] for q in d.get("/api/v1/elm/queue").json()["results"]] == [pk]
    r = d.post(f"/api/v1/elm/queue/{pk}/decide", {"event": "approve"}, format="json")
    assert r.json()["status"] == "approved"


def test_unit_head_never_sees_own_request(as_user, policy, calendar):
    c = as_user(HOD, EMPLOYEE + UNIT_HEAD, roles=HOD_ROLES, active_role="faculty")
    pk = c.post("/api/v1/elm/requests", leave("CL"), format="json").json()["id"]
    assert _hod(as_user).get("/api/v1/elm/queue").json()["results"] == []
    r = _hod(as_user).post(f"/api/v1/elm/queue/{pk}/decide", {"event": "approve"},
                           format="json")
    assert r.status_code == 404


def test_substitute_gate_decline_then_renominate(as_user, policy, calendar):
    r = _apply(as_user, FAC, leave("CL", substitute_user_id=FAC2, responsibility="classes"))
    pk = r.json()["id"]
    assert r.json()["status"] == "awaiting_substitute"
    assert _hod(as_user).get("/api/v1/elm/queue").json()["results"] == []

    sub = as_user(FAC2, EMPLOYEE)
    r = sub.post(f"/api/v1/elm/substitutions/{pk}/respond", {"accept": False},
                 format="json")
    assert r.json()["status"] == "substitute_declined"

    r = as_user(FAC, EMPLOYEE).post(f"/api/v1/elm/requests/{pk}/substitute",
                                    {"substitute_user_id": STF}, format="json")
    assert r.json()["status"] == "awaiting_substitute"
    r = as_user(STF, EMPLOYEE, kind="staff").post(
        f"/api/v1/elm/substitutions/{pk}/respond", {"accept": True}, format="json")
    assert r.json()["status"] == "awaiting_unit_head"


def test_substitute_cannot_be_self_or_on_leave(as_user, policy, calendar):
    assert _apply(as_user, FAC, leave("CL", substitute_user_id=FAC)).status_code == 422
    _apply(as_user, FAC2, leave("CL"))
    r = _apply(as_user, FAC, leave("CL", substitute_user_id=FAC2))
    assert r.json()["error"]["code"] == "substitute_unavailable"


def test_withdraw_is_immediate_and_blocks_later_decisions(as_user, policy, calendar):
    pk = _apply(as_user, FAC, leave("CL")).json()["id"]
    r = as_user(FAC, EMPLOYEE).post(f"/api/v1/elm/requests/{pk}/withdraw", {},
                                    format="json")
    assert r.json()["status"] == "withdrawn"
    r = _hod(as_user).post(f"/api/v1/elm/queue/{pk}/decide", {"event": "approve"},
                           format="json")
    assert r.status_code == 404


def test_modify_revalidates_and_restarts_routing(as_user, policy, calendar):
    pk = _apply(as_user, STF, leave("EL", days=3), kind="staff").json()["id"]
    _hod(as_user).post(f"/api/v1/elm/queue/{pk}/decide", {"event": "recommend"},
                       format="json")
    c = as_user(STF, EMPLOYEE, kind="staff")
    r = c.post(f"/api/v1/elm/requests/{pk}/modify", leave("EL", days=40), format="json")
    assert r.json()["error"]["code"] == "insufficient_balance"
    r = c.post(f"/api/v1/elm/requests/{pk}/modify", leave("EL", days=5), format="json")
    assert r.json()["status"] == "awaiting_unit_head"
    assert r.json()["recommendation"] == ""


def test_overlap_refused_but_other_half_allowed(as_user, policy, calendar):
    first = leave("CL", half="first")
    assert _apply(as_user, FAC, first).status_code == 201
    assert _apply(as_user, FAC, first).json()["error"]["code"] == "overlap"
    assert _apply(as_user, FAC, leave("CL", half="second")).status_code == 201
    assert _apply(as_user, FAC, leave("CL")).json()["error"]["code"] == "overlap"


def test_pending_requests_reserve_balance(as_user, policy, calendar):
    assert _apply(as_user, FAC, leave("CL", days=5)).status_code == 201
    r = _apply(as_user, FAC, leave("CL", start=monday(4), days=5))
    assert r.json()["error"]["code"] == "insufficient_balance"


def test_rh_must_match_calendar_and_vl_only_in_vacation(as_user, policy, calendar):
    rh_day = monday(3) + timedelta(days=2)
    assert _apply(as_user, FAC, leave("RH", start=monday(3))).status_code == 422
    assert _apply(as_user, FAC, leave("RH", start=rh_day)).status_code == 201
    assert _apply(as_user, FAC, leave("VL", start=monday(2))).status_code == 422
    assert _apply(as_user, FAC, leave("VL", start=monday(5), days=10)).status_code == 201
    assert _apply(as_user, STF, leave("VL", start=monday(5)), kind="staff") \
        .json()["error"]["code"] == "not_eligible"


def test_col_needs_medical_evidence(as_user, policy, calendar):
    assert _apply(as_user, FAC, leave("COL")).json()["error"]["code"] == \
        "medical_evidence_required"
    assert _apply(as_user, FAC, leave("COL", medical_evidence="cert-1")).status_code == 201


def test_cancellation_before_start_reverses_the_debit(as_user, policy, calendar):
    pk = _apply(as_user, FAC, leave("CL", days=2)).json()["id"]
    _hod(as_user).post(f"/api/v1/elm/queue/{pk}/decide", {"event": "approve"},
                       format="json")
    assert _balance(FAC, "CL") == 6
    r = as_user(FAC, EMPLOYEE).post(f"/api/v1/elm/requests/{pk}/cancel", {}, format="json")
    assert r.json()["status"] == "cancellation_pending"
    r = _hod(as_user).post(f"/api/v1/elm/queue/{pk}/decide",
                           {"event": "cancel_approve"}, format="json")
    assert r.json()["status"] == "cancelled"
    assert _balance(FAC, "CL") == 8


def test_rejected_cancellation_keeps_the_leave(as_user, policy, calendar):
    pk = _apply(as_user, FAC, leave("CL")).json()["id"]
    _hod(as_user).post(f"/api/v1/elm/queue/{pk}/decide", {"event": "approve"},
                       format="json")
    as_user(FAC, EMPLOYEE).post(f"/api/v1/elm/requests/{pk}/cancel", {}, format="json")
    r = _hod(as_user).post(f"/api/v1/elm/queue/{pk}/decide",
                           {"event": "cancel_reject", "note": "needed"}, format="json")
    assert r.json()["status"] == "approved"
    assert _balance(FAC, "CL") == 7


def _ongoing_el(as_user, days=10):
    start = timezone.localdate() - timedelta(days=2)
    req = LeaveRequest.objects.create(
        user_id=STF, category="EL", applicant_kind="staff", applicant_unit="CSE",
        start_date=start, end_date=start + timedelta(days=days - 1), days=days,
        purpose="x", status="approved",
        route=[{"step": "unit_head", "role": "HOD (CSE)"},
               {"step": "establishment", "role": "Deputy Registrar"},
               {"step": "sanction", "role": "Registrar"}])
    LedgerEntry.objects.create(user_id=STF, category="EL", entry_type="annual_credit",
                               delta=30, year=start.year)
    LedgerEntry.objects.create(user_id=STF, category="EL", entry_type="debit",
                               delta=-days, year=start.year, request=req)
    return req


def test_extension_posts_only_the_increment(as_user, policy, calendar):
    parent = _ongoing_el(as_user)
    c = as_user(STF, EMPLOYEE, kind="staff")
    r = c.post(f"/api/v1/elm/requests/{parent.pk}/extend",
               {"end_date": (parent.end_date + timedelta(days=3)).isoformat(),
                "purpose": "recovering"}, format="json")
    assert r.status_code == 201, r.json()
    ext = r.json()["id"]
    assert Decimal(r.json()["days"]) == 3
    _hod(as_user).post(f"/api/v1/elm/queue/{ext}/decide", {"event": "recommend"},
                       format="json")
    as_user(DR, ESTT, kind="staff", roles=("Deputy Registrar",)).post(
        f"/api/v1/elm/queue/{ext}/decide", {"event": "forward"}, format="json")
    as_user(REG, SANCTION, kind="staff", roles=("Registrar",)).post(
        f"/api/v1/elm/queue/{ext}/decide", {"event": "approve"}, format="json")
    assert _balance(STF, "EL") == 30 - 10 - 3


def test_cl_cannot_be_extended(as_user, policy, calendar):
    pk = _apply(as_user, FAC, leave("CL")).json()["id"]
    r = as_user(FAC, EMPLOYEE).post(f"/api/v1/elm/requests/{pk}/extend",
                                    {"end_date": monday(3).isoformat(), "purpose": "x"},
                                    format="json")
    assert r.json()["error"]["code"] == "not_extendable"


def test_early_resumption_restores_only_after_verification(as_user, policy, calendar):
    parent = _ongoing_el(as_user)
    back = timezone.localdate()
    r = as_user(STF, EMPLOYEE, kind="staff").post(
        f"/api/v1/elm/requests/{parent.pk}/resume",
        {"actual_return_date": back.isoformat()}, format="json")
    assert r.json()["status"] == "resumption_pending"
    assert _balance(STF, "EL") == 20

    hod = as_user(HOD, UNIT_HEAD, roles=HOD_ROLES, active_role="HOD (CSE)")
    r = hod.post(f"/api/v1/elm/resumptions/{parent.pk}/verify", {"verified": True},
                 format="json")
    assert r.json()["status"] == "closed"
    unused = (parent.end_date - back).days + 1
    assert _balance(STF, "EL") == 20 + unused


def test_printable_application(as_user, policy, calendar):
    pk = _apply(as_user, FAC, leave("CL", station_leave=True,
                                   station_from=monday(2).isoformat(),
                                   station_to=monday(2).isoformat(),
                                   station_address="Bhopal")).json()["id"]
    r = as_user(FAC, EMPLOYEE).get(f"/api/v1/elm/requests/{pk}/print")
    assert r.status_code == 200
    assert b"Bhopal" in r.content and b"Casual Leave" in r.content


def test_no_policy_says_what_is_missing(as_user, db):
    r = _apply(as_user, FAC, leave("CL"))
    assert r.status_code == 409
    assert "Leave Administrator" in r.json()["error"]["message"]
