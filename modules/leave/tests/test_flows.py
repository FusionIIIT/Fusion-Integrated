"""The basis workflows end to end over HTTP, the ordinary employee first."""
from datetime import date
from decimal import Decimal as D

import pytest
from freezegun import freeze_time

from modules.leave.models import LeaveRequest, LedgerEntry, Outbox, Task
from modules.leave.tests.conftest import (
    DEPUTY_REGISTRAR,
    DIRECTOR,
    FACULTY_CSE,
    FACULTY_CSE_2,
    HOD_CSE,
    REGISTRAR,
    STAFF_GA,
    STAFF_RO,
    apply_payload,
)

pytestmark = pytest.mark.django_db


def apply(client, **kw):
    return client.post("/api/v1/leave/requests", apply_payload(**kw), format="json")


def queue(client):
    r = client.get("/api/v1/leave/queue")
    assert r.status_code == 200, r.content
    return r.json()


def decide(client, task_id, action, remarks=""):
    return client.post(f"/api/v1/leave/tasks/{task_id}/decide",
                       {"action": action, "remarks": remarks}, format="json")


def balance(uid, cat, year=2026):
    return sum((e.delta for e in LedgerEntry.objects.filter(user_id=uid, category=cat,
                                                            leave_year=year)), start=D(0))


def test_bw01_ordinary_faculty_cl_approved_by_unit_head(configured, client_for):
    r = apply(client_for(FACULTY_CSE), start=date(2026, 3, 9))
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["status"] == "awaiting_unit_head" and body["days"] == "1.0"
    assert Outbox.objects.filter(topic="task.assigned", recipient_designation="HOD (CSE)").exists()

    hod = client_for(HOD_CSE)
    [task] = queue(hod)
    assert task["actions"] == ["approve", "reject"]
    r = decide(hod, task["id"], "approve")
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "approved" and r.json()["decided_role"] == "HOD (CSE)"
    assert balance(FACULTY_CSE, "CL") == D(7)
    assert Outbox.objects.filter(topic="decision.final", recipient_user_id=FACULTY_CSE).exists()


def test_bw01_rejection_needs_a_reason_and_leaves_the_balance(configured, client_for):
    apply(client_for(FACULTY_CSE))
    hod = client_for(HOD_CSE)
    [task] = queue(hod)
    assert decide(hod, task["id"], "reject").json()["error"]["code"] == "reason_required"
    r = decide(hod, task["id"], "reject", "Exams week")
    assert r.json()["status"] == "rejected" and r.json()["decision_remarks"] == "Exams week"
    assert balance(FACULTY_CSE, "CL") == D(8)


def test_half_days_on_one_date(configured, client_for):
    c = client_for(FACULTY_CSE)
    assert apply(c, half="first").status_code == 201
    assert apply(c, half="second").status_code == 201
    r = apply(c, half="first")
    assert r.status_code == 422 and r.json()["error"]["code"] == "overlaps_own_leave"


def test_bw04_higher_sanction_through_establishment(configured, client_for):
    """Staff EL: Unit Head recommends, Establishment forwards, Registrar sanctions."""
    r = apply(client_for(STAFF_RO), category="EL", start=date(2026, 3, 16),
              end=date(2026, 3, 20))
    assert r.status_code == 201, r.content
    assert r.json()["days"] == "5.0"

    reg = client_for(REGISTRAR)
    [task] = queue(reg)
    assert task["actions"] == ["recommend", "not_recommend"]
    assert decide(reg, task["id"], "recommend").json()["status"] == "awaiting_establishment"

    dr = client_for(DEPUTY_REGISTRAR)
    [task] = queue(dr)
    assert decide(dr, task["id"], "forward").json()["status"] == "awaiting_sanction"

    reg = client_for(REGISTRAR)
    [task] = queue(reg)
    assert task["step"] == "authority"
    r = decide(reg, task["id"], "approve")
    assert r.json()["status"] == "approved" and r.json()["unit_head_outcome"] == "recommended"
    assert balance(STAFF_RO, "EL") == D(25)


def test_not_recommended_is_not_a_rejection(configured, client_for):
    """BR-EL-017: faculty COL, Not Recommended, still reaches the Director who approves."""
    apply(client_for(FACULTY_CSE), category="COL", start=date(2026, 3, 9),
          end=date(2026, 3, 10))
    hod = client_for(HOD_CSE)
    [task] = queue(hod)
    assert decide(hod, task["id"], "not_recommend").status_code == 409
    assert decide(hod, task["id"], "not_recommend", "Short staffed").json()["status"] == (
        "awaiting_establishment")
    dr = client_for(DEPUTY_REGISTRAR)
    decide(dr, queue(dr)[0]["id"], "forward")
    director = client_for(DIRECTOR)
    [task] = queue(director)
    r = decide(director, task["id"], "approve")
    assert r.json()["status"] == "approved"
    assert r.json()["unit_head_outcome"] == "not_recommended"
    assert balance(FACULTY_CSE, "COL") == D(18)


def test_an_unmapped_unit_is_refused_with_a_sentence(configured, client_for):
    r = apply(client_for(STAFF_GA))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "routing_unresolved"
    assert "General Administration" in r.json()["error"]["message"]
    assert not LeaveRequest.objects.exists()


def test_bw03_substitute_decline_then_replacement_accepts(configured, client_for):
    r = apply(client_for(FACULTY_CSE), substitute_user_id=FACULTY_CSE_2)
    assert r.json()["status"] == "awaiting_substitute"
    req_id = r.json()["id"]

    sub = client_for(FACULTY_CSE_2)
    [s] = sub.get("/api/v1/leave/substitutions").json()
    assert sub.post(f"/api/v1/leave/substitutions/{s['id']}/respond",
                    {"accept": False}, format="json").status_code == 409
    r = sub.post(f"/api/v1/leave/substitutions/{s['id']}/respond",
                 {"accept": False, "remarks": "Away at a conference"}, format="json")
    assert r.json()["status"] == "applicant_action_required"
    assert Outbox.objects.filter(topic="substitute.declined").exists()

    me = client_for(FACULTY_CSE)
    r = me.post(f"/api/v1/leave/requests/{req_id}/substitute",
                {"substitute_user_id": HOD_CSE}, format="json")
    assert r.json()["status"] == "awaiting_substitute"

    hod_as_colleague = client_for(HOD_CSE, as_role="faculty")
    [s] = hod_as_colleague.get("/api/v1/leave/substitutions").json()
    r = hod_as_colleague.post(f"/api/v1/leave/substitutions/{s['id']}/respond",
                              {"accept": True}, format="json")
    assert r.json()["status"] == "awaiting_unit_head"


def test_stale_substitute_answer_is_refused(configured, client_for):
    req_id = apply(client_for(FACULTY_CSE), substitute_user_id=FACULTY_CSE_2).json()["id"]
    sub = client_for(FACULTY_CSE_2)
    [s] = sub.get("/api/v1/leave/substitutions").json()
    client_for(FACULTY_CSE).post(f"/api/v1/leave/requests/{req_id}/withdraw", {}, format="json")
    sub = client_for(FACULTY_CSE_2)
    r = sub.post(f"/api/v1/leave/substitutions/{s['id']}/respond", {"accept": True},
                 format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "no_longer_pending"


def test_bw07_director_self_sanction(configured, client_for):
    r = apply(client_for(DIRECTOR, as_role="faculty"))
    assert r.json()["status"] == "awaiting_director"
    assert not queue(client_for(DIRECTOR, as_role="faculty"))
    director = client_for(DIRECTOR)
    [task] = queue(director)
    assert task["step"] == "director"
    assert decide(director, task["id"], "approve").json()["status"] == "approved"


def test_withdrawal_terminates_and_blocks_later_decisions(configured, client_for):
    req_id = apply(client_for(FACULTY_CSE)).json()["id"]
    hod = client_for(HOD_CSE)
    [task] = queue(hod)
    r = client_for(FACULTY_CSE).post(f"/api/v1/leave/requests/{req_id}/withdraw",
                                     {"reason": "Plans changed"}, format="json")
    assert r.json()["status"] == "withdrawn"
    assert Task.objects.get(pk=task["id"]).status == "cancelled"
    assert Outbox.objects.filter(topic="request.withdrawn",
                                 recipient_designation="HOD (CSE)").exists()
    hod = client_for(HOD_CSE)
    assert not queue(hod)
    assert decide(hod, task["id"], "approve").status_code == 409


def test_approved_leave_cannot_be_withdrawn(configured, client_for):
    req_id = apply(client_for(FACULTY_CSE)).json()["id"]
    hod = client_for(HOD_CSE)
    decide(hod, queue(hod)[0]["id"], "approve")
    r = client_for(FACULTY_CSE).post(f"/api/v1/leave/requests/{req_id}/withdraw", {},
                                     format="json")
    assert r.json()["error"]["code"] == "already_approved"


def test_bw10_cancellation_restores_the_balance(configured, client_for):
    me = client_for(FACULTY_CSE)
    leave_id = apply(me).json()["id"]
    hod = client_for(HOD_CSE)
    decide(hod, queue(hod)[0]["id"], "approve")
    assert balance(FACULTY_CSE, "CL") == D(7)

    me = client_for(FACULTY_CSE)
    r = me.post(f"/api/v1/leave/requests/{leave_id}/cancellation",
                {"reason": "Function postponed"}, format="json")
    assert r.status_code == 201 and r.json()["kind"] == "cancellation"
    assert me.post(f"/api/v1/leave/requests/{leave_id}/cancellation",
                   {"reason": "again"}, format="json").status_code == 409
    hod = client_for(HOD_CSE)
    decide(hod, queue(hod)[0]["id"], "approve")
    assert LeaveRequest.objects.get(pk=leave_id).status == "cancelled"
    assert balance(FACULTY_CSE, "CL") == D(8)


def test_rejected_cancellation_leaves_the_leave_approved(configured, client_for):
    me = client_for(FACULTY_CSE)
    leave_id = apply(me).json()["id"]
    hod = client_for(HOD_CSE)
    decide(hod, queue(hod)[0]["id"], "approve")
    client_for(FACULTY_CSE).post(f"/api/v1/leave/requests/{leave_id}/cancellation",
                                 {"reason": "x"}, format="json")
    hod = client_for(HOD_CSE)
    decide(hod, queue(hod)[0]["id"], "reject", "Already arranged")
    assert LeaveRequest.objects.get(pk=leave_id).status == "approved"
    assert balance(FACULTY_CSE, "CL") == D(7)


def _approved_staff_el(client_for, start, end):
    leave_id = apply(client_for(STAFF_RO), category="EL", start=start, end=end).json()["id"]
    reg = client_for(REGISTRAR)
    decide(reg, queue(reg)[0]["id"], "recommend")
    dr = client_for(DEPUTY_REGISTRAR)
    decide(dr, queue(dr)[0]["id"], "forward")
    reg = client_for(REGISTRAR)
    decide(reg, queue(reg)[0]["id"], "approve")
    return leave_id


def test_cancellation_is_refused_once_leave_has_begun(configured, client_for):
    leave_id = _approved_staff_el(client_for, date(2026, 3, 3), date(2026, 3, 6))
    with freeze_time("2026-03-04 10:00:00+05:30"):
        r = client_for(STAFF_RO).post(f"/api/v1/leave/requests/{leave_id}/cancellation",
                                      {"reason": "x"}, format="json")
    assert r.json()["error"]["code"] == "leave_already_started"


def test_bw12_extension_posts_only_the_increment_then_early_resumption(configured, client_for):
    leave_id = _approved_staff_el(client_for, date(2026, 3, 3), date(2026, 3, 6))
    assert balance(STAFF_RO, "EL") == D(26)
    with freeze_time("2026-03-05 10:00:00+05:30"):
        r = client_for(STAFF_RO).post(f"/api/v1/leave/requests/{leave_id}/extension",
                                      {"end_date": "2026-03-10", "purpose": "Recovering"},
                                      format="json")
        assert r.status_code == 201, r.content
        assert r.json()["start_date"] == "2026-03-07" and r.json()["days"] == "4.0"
        reg = client_for(REGISTRAR)
        decide(reg, queue(reg)[0]["id"], "recommend")
        dr = client_for(DEPUTY_REGISTRAR)
        decide(dr, queue(dr)[0]["id"], "forward")
        reg = client_for(REGISTRAR)
        decide(reg, queue(reg)[0]["id"], "approve")
    assert balance(STAFF_RO, "EL") == D(22)
    base = LeaveRequest.objects.get(pk=leave_id)
    assert base.end_date == date(2026, 3, 6)

    with freeze_time("2026-03-09 10:00:00+05:30"):
        me = client_for(STAFF_RO)
        r = me.post(f"/api/v1/leave/requests/{leave_id}/resumption",
                    {"resumption_date": "2026-03-09"}, format="json")
        assert r.status_code == 201, r.content
        reg = client_for(REGISTRAR)
        [task] = queue(reg)
        assert task["step"] == "resumption_review" and task["actions"] == ["review"]
        r = decide(reg, task["id"], "review")
        assert r.status_code == 200, r.content
        assert r.json()["resumption"]["outcome"] == "early"
        assert r.json()["resumption"]["actual_end_date"] == "2026-03-08"
    assert balance(STAFF_RO, "EL") == D(24)


def test_normal_resumption_changes_nothing(configured, client_for):
    leave_id = _approved_staff_el(client_for, date(2026, 3, 3), date(2026, 3, 6))
    with freeze_time("2026-03-07 10:00:00+05:30"):
        client_for(STAFF_RO).post(f"/api/v1/leave/requests/{leave_id}/resumption",
                                  {"resumption_date": "2026-03-07"}, format="json")
        reg = client_for(REGISTRAR)
        r = decide(reg, queue(reg)[0]["id"], "review")
    assert r.json()["resumption"]["outcome"] == "normal"
    assert balance(STAFF_RO, "EL") == D(26)


def test_late_resumption_charges_the_extra_days(configured, client_for):
    leave_id = _approved_staff_el(client_for, date(2026, 3, 3), date(2026, 3, 6))
    with freeze_time("2026-03-10 10:00:00+05:30"):
        client_for(STAFF_RO).post(f"/api/v1/leave/requests/{leave_id}/resumption",
                                  {"resumption_date": "2026-03-10"}, format="json")
        reg = client_for(REGISTRAR)
        r = decide(reg, queue(reg)[0]["id"], "review")
    assert r.json()["resumption"]["outcome"] == "late"
    assert balance(STAFF_RO, "EL") == D(23)


def test_overview_and_document(configured, client_for):
    me = client_for(FACULTY_CSE)
    req_id = apply(me).json()["id"]
    ov = me.get("/api/v1/leave/overview").json()
    cl = next(b for b in ov["balances"] if b["category"] == "CL")
    assert (cl["balance"], cl["pending"], cl["available"]) == ("8.00", "1.00", "7.00")
    assert [c["category"] for c in ov["categories"]] == ["CL", "RH", "SCL", "EL", "COL", "VL"]
    doc = me.get(f"/api/v1/leave/requests/{req_id}/document")
    assert doc.status_code == 200 and b"Family function" in doc.content
    assert doc["Content-Type"].startswith("text/html")


def test_a_substitute_cannot_go_on_leave_over_the_period_they_cover(configured, client_for):
    """Adversarial pass: an accepted substitute made unavailable afterwards."""
    client_for(FACULTY_CSE).post("/api/v1/leave/requests",
                                 apply_payload(substitute_user_id=FACULTY_CSE_2), format="json")
    sub = client_for(FACULTY_CSE_2)
    [s] = sub.get("/api/v1/leave/substitutions").json()
    sub.post(f"/api/v1/leave/substitutions/{s['id']}/respond", {"accept": True}, format="json")
    r = client_for(FACULTY_CSE_2).post("/api/v1/leave/requests", apply_payload(), format="json")
    assert r.status_code == 422 and r.json()["error"]["code"] == "covering_for_colleague"


def test_a_nominee_who_went_on_leave_meanwhile_cannot_accept(configured, client_for):
    client_for(FACULTY_CSE).post("/api/v1/leave/requests",
                                 apply_payload(substitute_user_id=FACULTY_CSE_2), format="json")
    from modules.leave.models import Substitution

    Substitution.objects.update(status="void")
    client_for(FACULTY_CSE_2).post("/api/v1/leave/requests", apply_payload(), format="json")
    Substitution.objects.update(status="pending")
    sub = client_for(FACULTY_CSE_2)
    [s] = sub.get("/api/v1/leave/substitutions").json()
    r = sub.post(f"/api/v1/leave/substitutions/{s['id']}/respond", {"accept": True},
                 format="json")
    assert r.json()["error"]["code"] == "substitute_on_leave"
