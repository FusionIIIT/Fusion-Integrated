"""The module end to end through HTTP only: each actor signs in in turn, the rows and the trail
are read back through the API. One test per use case's main flow and per workflow in the spec.

Ids are cited next to each test so that `grep -rn <ID> modules/iaa/tests` finds it.
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.iaa.domain import roles
from modules.iaa.services import decisions
from modules.iaa.tests.helpers import DOC, FACULTY, POLICY, api_client

pytestmark = pytest.mark.django_db

B = "/api/v1/iaa"
LATE = timedelta(hours=49)                      # the policy allows 48

CREATOR = (101, FACULTY)
FINANCE = (201, roles.FINANCE)
HOD = (301, roles.HOD)
DEAN = (302, roles.DEAN)
DIRECTOR = (303, roles.DIRECTOR)
AUDITOR = (401, roles.AUDITOR)
ADMIN = (501, roles.SYSTEM_ADMIN)


class Journey:
    """Drives the API as one actor at a time and fails on any unexpected status."""

    def __init__(self, stub_iam):
        self.stub_iam = stub_iam

    def call(self, who, method, url, body=None, expect=200):
        client = api_client(self.stub_iam, *who)
        if method == "get":
            response = client.get(f"{B}{url}")
        elif method == "patch":
            response = client.patch(f"{B}{url}", body or {}, format="json")
        else:
            response = client.post(f"{B}{url}", body or {}, format="json")
        if response.streaming:
            assert response.status_code == expect
            return response
        assert response.status_code == expect, response.content
        return response.json() if response.content else None

    def get(self, who, url, expect=200):
        return self.call(who, "get", url, expect=expect)

    def post(self, who, url, body=None, expect=200):
        return self.call(who, "post", url, body, expect)

    # ── building blocks ────────────────────────────────────────────────────────────────
    def submitted_expense(self, amount="10000", department="CSE"):
        made = self.post(CREATOR, "/records", {
            "kind": "expense", "department": department, "request_type": "voucher",
            "title": "Lab kits", "description": "Soldering kits", "amount": amount}, expect=201)
        self.post(CREATOR, f"/records/{made['id']}/documents", DOC, expect=201)
        return self.post(CREATOR, f"/records/{made['id']}/submit")["id"]

    def submitted_ta(self, amount="30000"):
        today = timezone.localdate()
        made = self.post(CREATOR, "/records", {
            "kind": "ta", "department": "CSE", "amount": amount, "purpose": "Conference",
            "trip_start": str(today - timedelta(days=5)), "trip_end": str(today - timedelta(days=3)),
            "documents": [DOC]}, expect=201)
        return made["id"]

    def validated(self, pk):
        return self.post(FINANCE, f"/records/{pk}/validate")

    def decide(self, who, pk, decision, remarks="Reviewed", expect=200):
        return self.post(who, f"/records/{pk}/decision",
                         {"decision": decision, "remarks": remarks}, expect)

    def status(self, pk):
        return self.get(CREATOR, f"/records/{pk}")["status"]

    def transitions(self, pk):
        skip = ("create", "add_document", "update_draft")
        return [h["to_status"] for h in self.get(CREATOR, f"/records/{pk}/history")
                if h["action"] not in skip]

    def overdue(self):
        decisions.escalate_overdue(at=timezone.now() + LATE)

    def raise_budget_anomaly(self):
        return self.post(FINANCE, "/anomalies",
                         {"category": "budget", "description": "Overspend"}, expect=201)["id"]


@pytest.fixture
def run(stub_iam, people, configured):
    return Journey(stub_iam)


# ── UC-101, UC-102: drafting and submitting an expense ───────────────────────────────────
# AFR-IAA-001 AFR-IAA-002 AFR-IAA-003 AFR-IAA-004 AFR-IAA-005 AFR-IAA-006 AFR-IAA-007
# AFR-IAA-008 AFR-IAA-009 CFR-IAA-01 IAA-BR-101 IAA-BR-104
def test_uc_101_and_uc_102_a_draft_may_be_incomplete_but_a_submission_may_not(run):
    draft = run.post(CREATOR, "/records", {"kind": "expense"}, expect=201)
    assert draft["status"] == "draft"
    pk = draft["id"]
    refused = run.post(CREATOR, f"/records/{pk}/submit", expect=422)
    assert refused["error"]["code"] == "submission_incomplete"
    assert {d["field"] for d in refused["error"]["details"]} >= {"amount", "documents"}

    run.call(CREATOR, "patch", f"/records/{pk}", {
        "department": "CSE", "request_type": "voucher", "title": "Kits",
        "description": "Soldering kits", "amount": "10000"})
    run.post(CREATOR, f"/records/{pk}/documents", DOC, expect=201)
    done = run.post(CREATOR, f"/records/{pk}/submit")
    assert done["status"] == "submitted" and len(done["documents"]) == 1

    locked = run.call(CREATOR, "patch", f"/records/{pk}", {"title": "Edited"}, expect=409)
    assert locked["error"]["code"] == "record_locked"
    assert run.transitions(pk) == ["submitted"]
    assert {h["action"] for h in run.get(CREATOR, f"/records/{pk}/history")} >= {"create", "submit"}


# ── BW-IAA-01 / CW-IAA-01 ────────────────────────────────────────────────────────────────
# UC-103 UC-105 UC-201 AFR-IAA-010 AFR-IAA-011 AFR-IAA-015 AFR-IAA-016 AFR-IAA-017
# AFR-IAA-018 AFR-IAA-019 AFR-IAA-020 AFR-IAA-021 AFR-IAA-022 AFR-IAA-029 AFR-IAA-075
# CFR-IAA-02 CFR-IAA-03 CFR-IAA-04 CFR-IAA-18 IAA-BR-002 IAA-BR-003 IAA-BR-006 IAA-BR-503
def test_bw_iaa_01_an_expense_goes_from_draft_to_recorded_with_one_approval(run):
    pk = run.submitted_expense()
    assert run.validated(pk)["status"] == "finance_validated"
    approved = run.decide(HOD, pk, "approve", "Within plan")
    assert approved["status"] == "approved" and approved["steps"][0]["decided_role"] == roles.HOD
    done = run.post(FINANCE, f"/records/{pk}/processing", {"reference": "VCH-1", "note": "filed"})
    assert done["status"] == "recorded" and done["processing_reference"] == "VCH-1"
    assert run.transitions(pk) == ["submitted", "finance_validated", "approved", "recorded"]
    history = run.get(CREATOR, f"/records/{pk}/history")
    assert all(h["actor_user_id"] is not None and h["actor_role"] for h in history)
    assert {h["actor_role"] for h in history} >= {FACULTY, roles.FINANCE, roles.HOD}
    run.call(CREATOR, "patch", f"/records/{pk}", {"title": "x"}, expect=409)   # read-only now


# ── BW-IAA-02 ────────────────────────────────────────────────────────────────────────────
# AFR-IAA-025 CFR-IAA-04
def test_bw_iaa_02_a_large_expense_needs_a_second_approval_in_order(run):
    pk = run.submitted_expense(amount="60000")
    run.validated(pk)
    first = run.decide(HOD, pk, "approve", "Level one")
    assert first["status"] == "approval_pending" and first["current_level"] == 1
    run.decide(DIRECTOR, pk, "approve", "Too early", expect=404)      # no step of theirs yet
    assert run.decide(DEAN, pk, "approve", "Level two")["status"] == "approved"
    assert run.post(FINANCE, f"/records/{pk}/processing", {"reference": "V-2"})["status"] == "recorded"
    assert run.transitions(pk) == ["submitted", "finance_validated", "approval_pending",
                                   "approved", "recorded"]


# ── BW-IAA-03 ────────────────────────────────────────────────────────────────────────────
# AFR-IAA-023 IAA-BR-005
def test_bw_iaa_03_a_rejection_is_final_and_needs_remarks(run):
    pk = run.submitted_expense()
    run.validated(pk)
    blank = run.decide(HOD, pk, "reject", " ", expect=422)
    assert blank["error"]["code"] == "remarks_required"
    assert run.decide(HOD, pk, "reject", "Not justified")["status"] == "rejected"
    run.decide(HOD, pk, "approve", "Changed my mind", expect=409)
    run.post(FINANCE, f"/records/{pk}/processing", {"reference": "no"}, expect=409)
    assert run.status(pk) == "rejected"


# ── BW-IAA-04 ────────────────────────────────────────────────────────────────────────────
# UC-104 AFR-IAA-012 AFR-IAA-013 AFR-IAA-014
def test_bw_iaa_04_finance_asks_one_question_and_the_requester_answers(run):
    pk = run.submitted_expense()
    asked = run.post(FINANCE, f"/records/{pk}/query", {"text": "Which lab?"})
    assert asked["status"] == "query_raised"
    run.post(CREATOR, f"/records/{pk}/documents", DOC, expect=201)
    answered = run.post(CREATOR, f"/records/{pk}/query-response", {"text": "Embedded lab"})
    assert answered["status"] == "query_responded"
    assert answered["queries"][0]["question"] == "Which lab?"
    assert answered["queries"][0]["response"] == "Embedded lab"
    assert run.validated(pk)["status"] == "finance_validated"
    assert run.decide(HOD, pk, "approve")["status"] == "approved"
    assert run.transitions(pk)[:3] == ["submitted", "query_raised", "query_responded"]


# ── BW-IAA-05 ────────────────────────────────────────────────────────────────────────────
# UC-202 UC-203 AFR-IAA-026 AFR-IAA-027 AFR-IAA-028 CFR-IAA-05 IAA-BR-401
def test_bw_iaa_05_an_overdue_approval_is_escalated_and_the_dean_approves(run):
    pk = run.submitted_expense()
    run.validated(pk)
    run.overdue()
    assert run.status(pk) == "escalated"
    assert pk in {r["id"] for r in run.get(DEAN, "/records")["results"]}
    run.decide(HOD, pk, "approve", "Too late", expect=409)             # the HoD lost it
    assert run.decide(DEAN, pk, "approve", "Handled")["status"] == "approved"
    notes = run.get(CREATOR, "/notifications")["notifications"]
    assert any(n["kind"] == "escalated" for n in notes)


# ── BW-IAA-06 ────────────────────────────────────────────────────────────────────────────
def test_bw_iaa_06_an_escalated_approval_can_be_rejected_by_the_dean(run):
    pk = run.submitted_expense()
    run.validated(pk)
    run.overdue()
    assert run.decide(DEAN, pk, "reject", "Not approved")["status"] == "rejected"
    assert run.transitions(pk)[-2:] == ["escalated", "rejected"]


# ── BW-IAA-07 / CW-IAA-02 ────────────────────────────────────────────────────────────────
# UC-401 UC-402 UC-404 AFR-IAA-036 AFR-IAA-037 AFR-IAA-038 AFR-IAA-039 AFR-IAA-040
# AFR-IAA-041 AFR-IAA-046 AFR-IAA-047 CFR-IAA-08 CFR-IAA-09 CFR-IAA-11 IAA-BR-201
def test_bw_iaa_07_a_normal_ta_claim_is_verified_and_recorded_without_approval(run):
    pk = run.submitted_ta(amount="10000")
    assert run.status(pk) == "submitted"
    assert run.post(FINANCE, f"/records/{pk}/validate",
                    {"decision": "verify"})["status"] == "verified"
    done = run.post(FINANCE, f"/records/{pk}/processing", {"reference": "TA-1"})
    assert done["status"] == "recorded"
    run.decide(HOD, pk, "approve", expect=404)                      # never needed an authority
    run.call(CREATOR, "patch", f"/records/{pk}", {"purpose": "x"}, expect=409)


# ── BW-IAA-08 ────────────────────────────────────────────────────────────────────────────
# UC-403 AFR-IAA-043 AFR-IAA-044 CFR-IAA-10 IAA-BR-202
def test_bw_iaa_08_a_high_value_ta_claim_is_approved_by_the_hod_then_recorded(run):
    pk = run.submitted_ta(amount="30000")
    assert run.validated(pk)["status"] == "approval_pending"
    run.post(FINANCE, f"/records/{pk}/processing", {"reference": "early"}, expect=409)
    assert run.decide(HOD, pk, "approve", "Valid trip")["status"] == "approved"
    assert run.post(FINANCE, f"/records/{pk}/processing", {"reference": "TA-2"})["status"] \
        == "recorded"


# ── BW-IAA-09 ────────────────────────────────────────────────────────────────────────────
# UC-703 AFR-IAA-069
def test_bw_iaa_09_a_high_value_ta_claim_can_need_a_second_approval(run):
    two_levels = {**POLICY, "routes": [
        *POLICY["routes"][:2],
        {"kind": "ta", "min_amount": "0", "levels": [roles.HOD, roles.DEAN],
         "escalation_designation": roles.DIRECTOR}]}
    run.post(ADMIN, "/config/policies", two_levels, expect=201)
    pk = run.submitted_ta(amount="30000")
    run.validated(pk)
    assert run.decide(HOD, pk, "approve")["status"] == "approval_pending"
    assert run.decide(DEAN, pk, "approve")["status"] == "approved"
    assert run.post(FINANCE, f"/records/{pk}/processing", {"reference": "TA-3"})["status"] \
        == "recorded"


# ── BW-IAA-10 ────────────────────────────────────────────────────────────────────────────
def test_bw_iaa_10_a_high_value_ta_claim_can_be_rejected(run):
    pk = run.submitted_ta(amount="40000")
    run.validated(pk)
    assert run.decide(HOD, pk, "reject", "Not on duty")["status"] == "rejected"
    run.post(FINANCE, f"/records/{pk}/processing", {"reference": "no"}, expect=409)


# ── BW-IAA-11 ────────────────────────────────────────────────────────────────────────────
# AFR-IAA-042
def test_bw_iaa_11_a_ta_claimant_answers_one_finance_question(run):
    pk = run.submitted_ta(amount="10000")
    run.post(FINANCE, f"/records/{pk}/query", {"text": "Boarding pass?"})
    run.post(CREATOR, f"/records/{pk}/documents", DOC, expect=201)
    run.post(CREATOR, f"/records/{pk}/query-response", {"text": "Attached"})
    assert run.post(FINANCE, f"/records/{pk}/validate")["status"] == "verified"


# ── BW-IAA-16 / BW-IAA-17 ────────────────────────────────────────────────────────────────
def test_bw_iaa_16_an_escalated_high_value_ta_claim_is_approved_by_the_dean(run):
    pk = run.submitted_ta(amount="30000")
    run.validated(pk)
    run.overdue()
    assert run.status(pk) == "escalated"
    assert run.decide(DEAN, pk, "approve")["status"] == "approved"
    assert run.post(FINANCE, f"/records/{pk}/processing", {"reference": "TA-4"})["status"] \
        == "recorded"


def test_bw_iaa_17_an_escalated_high_value_ta_claim_can_be_rejected_by_the_dean(run):
    pk = run.submitted_ta(amount="30000")
    run.validated(pk)
    run.overdue()
    assert run.decide(DEAN, pk, "reject", "No")["status"] == "rejected"


# ── BW-IAA-12 / CW-IAA-03 ────────────────────────────────────────────────────────────────
# UC-302 UC-303 AFR-IAA-031 AFR-IAA-032 AFR-IAA-034 AFR-IAA-035 CFR-IAA-07 IAA-BR-103
def test_bw_iaa_12_an_anomaly_is_flagged_and_resolved_by_its_resolver(run):
    pk = run.raise_budget_anomaly()
    assert run.get(FINANCE, "/anomalies?status=open")["results"][0]["id"] == pk
    done = run.post(FINANCE, f"/anomalies/{pk}/resolve", {"text": "Reallocated"})
    assert done["status"] == "resolved" and done["resolved_role"] == roles.FINANCE
    run.post(FINANCE, f"/anomalies/{pk}/resolve", {"text": "again"}, expect=409)
    flagged = run.post(AUDITOR, "/anomalies",
                       {"category": "financial", "description": "Odd ledger"}, expect=201)
    assert flagged["assigned_role"] == roles.AUDITOR                 # AFR-IAA-032


# ── BW-IAA-13 ────────────────────────────────────────────────────────────────────────────
def test_bw_iaa_13_an_anomaly_is_escalated_once_and_resolved_by_the_next_resolver(run):
    pk = run.raise_budget_anomaly()
    escalated = run.post(FINANCE, f"/anomalies/{pk}/escalate", {"text": "Above my remit"})
    assert escalated["status"] == "escalated" and escalated["assigned_role"] == roles.DEAN
    run.post(FINANCE, f"/anomalies/{pk}/resolve", {"text": "Late"}, expect=409)
    assert run.post(DEAN, f"/anomalies/{pk}/resolve", {"text": "Done"})["status"] == "resolved"


# ── BW-IAA-18 / BW-IAA-19 ────────────────────────────────────────────────────────────────
# UC-304 AFR-IAA-030 AFR-IAA-033 CFR-IAA-06 IAA-BR-102
def test_bw_iaa_18_a_budget_shortfall_raises_an_automatic_anomaly_not_a_rejection(run):
    pk = run.submitted_expense(department="ECE")                     # ECE has no allocation
    assert run.validated(pk)["status"] == "finance_validated"
    anomalies = run.get(FINANCE, "/anomalies")["results"]
    assert len(anomalies) == 1 and anomalies[0]["source"] == "automatic"
    assert anomalies[0]["record"] == pk
    done = run.post(FINANCE, f"/anomalies/{anomalies[0]['id']}/resolve", {"text": "Funds moved"})
    assert done["status"] == "resolved"


def test_bw_iaa_19_an_automatic_anomaly_can_be_escalated_to_the_dean(run):
    pk = run.submitted_expense(department="ECE")
    run.validated(pk)
    anomaly = run.get(FINANCE, "/anomalies")["results"][0]["id"]
    run.post(FINANCE, f"/anomalies/{anomaly}/escalate", {"text": "Needs the Dean"})
    assert run.post(DEAN, f"/anomalies/{anomaly}/resolve", {"text": "Approved overspend"}
                    )["status"] == "resolved"


# ── BW-IAA-14 / CW-IAA-04 ────────────────────────────────────────────────────────────────
# UC-501 UC-502 UC-503 UC-504 AFR-IAA-048 AFR-IAA-049 AFR-IAA-050 AFR-IAA-051 AFR-IAA-052
# AFR-IAA-053 AFR-IAA-054 AFR-IAA-055 AFR-IAA-057 CFR-IAA-12 CFR-IAA-13 IAA-BR-301 IAA-BR-302
def test_bw_iaa_14_an_audit_observation_is_raised_answered_verified_and_closed(run):
    pk = run.submitted_expense()
    assert pk in {r["id"] for r in run.get(AUDITOR, "/records")["results"]}      # UC-504
    raised = run.post(AUDITOR, "/observations", {"title": "Missing note", "detail": "No sign-off",
                                                 "record_id": pk}, expect=201)
    assert raised["status"] == "open" and raised["respondent_user_id"] == 101
    obs = raised["id"]
    replied = run.post(CREATOR, f"/observations/{obs}/respond", {
        "corrective_action": "Added", "evidence_link": "https://files.example/n.pdf"})
    assert replied["status"] == "responded"
    closed = run.post(AUDITOR, f"/observations/{obs}/review", {"verdict": "satisfactory"})
    assert closed["status"] == "closed" and len(closed["responses"]) == 1
    run.post(CREATOR, f"/observations/{obs}/respond", {"corrective_action": "more"}, expect=409)
    kept = run.get(AUDITOR, "/observations?status=closed")["results"]             # never deleted
    assert [o["id"] for o in kept] == [obs]


# ── BW-IAA-15 ────────────────────────────────────────────────────────────────────────────
# AFR-IAA-056
def test_bw_iaa_15_an_unsatisfactory_response_reopens_the_observation_for_another_cycle(run):
    pk = run.submitted_expense()
    obs = run.post(AUDITOR, "/observations", {"title": "t", "detail": "d", "record_id": pk},
                   expect=201)["id"]
    run.post(CREATOR, f"/observations/{obs}/respond", {"corrective_action": "first"})
    reopened = run.post(AUDITOR, f"/observations/{obs}/review",
                        {"verdict": "unsatisfactory", "remarks": "Evidence missing"})
    assert reopened["status"] == "open"
    run.post(CREATOR, f"/observations/{obs}/respond", {"corrective_action": "second"})
    closed = run.post(AUDITOR, f"/observations/{obs}/review", {"verdict": "satisfactory"})
    assert closed["status"] == "closed" and len(closed["responses"]) == 2


# ── UC-601, UC-602, UC-603, UC-604 ───────────────────────────────────────────────────────
# AFR-IAA-058 AFR-IAA-059 AFR-IAA-060 AFR-IAA-061 AFR-IAA-062 AFR-IAA-063 AFR-IAA-064
# AFR-IAA-065 AFR-IAA-066 AFR-IAA-067 CFR-IAA-14 CFR-IAA-15 IAA-BR-504
def test_uc_601_to_uc_604_reports_status_tracking_and_notifications(run):
    pk = run.submitted_expense()
    run.validated(pk)
    run.decide(HOD, pk, "approve")
    summary = run.get(FINANCE, "/reports/summary")
    assert summary["records"] == [{"kind": "expense", "status": "approved", "count": 1}]
    assert summary["approval_turnaround"][0]["decisions"] == 1                    # AFR-IAA-059
    assert "anomalies" in summary and "observations" in summary                   # AFR-IAA-060
    export = run.get(FINANCE, "/reports/export")
    assert export.status_code == 200 and export["Content-Type"].startswith("text/csv")
    run.get(CREATOR, "/reports/export", expect=403)
    assert run.get(CREATOR, f"/records/{pk}")["status"] == "approved"             # UC-603
    mine = run.get(CREATOR, "/notifications")
    assert {n["kind"] for n in mine["notifications"]} >= {"finance_validated", "approved"}
    assert run.get(FINANCE, "/notifications")["pending"]["to_review"] == 0        # UC-604


# ── UC-703, UC-704 ───────────────────────────────────────────────────────────────────────
# AFR-IAA-068 AFR-IAA-070 AFR-IAA-071 CFR-IAA-16 IAA-BR-004
def test_uc_703_and_uc_704_the_admin_configures_but_cannot_see_or_decide_operational_items(
        run):
    pk = run.submitted_expense()
    run.validated(pk)
    run.get(ADMIN, "/records", expect=403)
    run.get(ADMIN, f"/records/{pk}", expect=403)
    run.decide(ADMIN, pk, "approve", expect=403)
    changed = run.post(ADMIN, "/config/policies", {**POLICY, "approval_timeout_hours": 24},
                       expect=201)
    assert changed["approval_timeout_hours"] == 24
    year = run.post(ADMIN, "/config/financial-years", {
        "code": "2030-31", "starts_on": "2030-04-01", "ends_on": "2031-03-31"}, expect=201)
    assert year["code"] == "2030-31"


# ── IAA-BR-001: nobody decides their own item ────────────────────────────────────────────
# AFR-IAA-024 AFR-IAA-045
def test_br_001_an_approver_cannot_approve_their_own_request_and_it_is_rerouted(run):
    made = run.post((301, FACULTY), "/records", {
        "kind": "expense", "department": "CSE", "request_type": "voucher", "title": "Own",
        "description": "x", "amount": "10000"}, expect=201)["id"]
    run.post((301, FACULTY), f"/records/{made}/documents", DOC, expect=201)
    run.post((301, FACULTY), f"/records/{made}/submit")
    run.validated(made)
    refused = run.decide(HOD, made, "approve", "mine", expect=403)
    assert refused["error"]["code"] == "segregation_of_duties"
    final = run.decide(DEAN, made, "approve", "independent")
    assert final["status"] == "approved" and final["steps"][-1]["decided_role"] == roles.DEAN


# ── IAA-BR-502: a role change never rewrites history ─────────────────────────────────────
# AFR-IAA-072 AFR-IAA-073 AFR-IAA-074 CFR-IAA-17
def test_br_502_the_trail_keeps_the_role_each_action_was_taken_in(run):
    pk = run.submitted_expense()
    run.validated(pk)
    run.post((301, roles.DEAN), f"/records/{pk}/decision",
             {"decision": "approve", "remarks": "Acting as Dean"}, expect=404)  # wrong acting role
    run.decide(HOD, pk, "approve")
    roles_seen = [h["actor_role"] for h in run.get(CREATOR, f"/records/{pk}/history")]
    assert roles.HOD in roles_seen and roles.DEAN not in roles_seen
