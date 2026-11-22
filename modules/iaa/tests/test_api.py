"""The HTTP contract: whole flows, error envelopes, CSV export and configuration endpoints."""
import csv
import io

import pytest

from modules.iaa.domain import roles
from modules.iaa.services import review
from modules.iaa.tests.helpers import FACULTY, POLICY, actor, api_client, new_expense

pytestmark = pytest.mark.django_db

B = "/api/v1/iaa"
EXPENSE = {"kind": "expense", "department": "CSE", "request_type": "voucher",
           "title": "Lab kits", "description": "Soldering kits", "amount": "10000"}
DOC = {"title": "Invoice", "link": "https://files.example/invoice.pdf"}


def _post(client, url, body=None):
    return client.post(f"{B}{url}", body or {}, format="json")


def _error(response):
    return response.json()["error"]


def test_an_expense_travels_from_draft_to_recorded_over_http(stub_iam, people, configured):
    creator = api_client(stub_iam, 101, FACULTY)
    created = _post(creator, "/records", EXPENSE)
    assert created.status_code == 201 and created.json()["status"] == "draft"
    pk = created.json()["id"]
    assert _post(creator, f"/records/{pk}/documents", DOC).status_code == 201
    patched = creator.patch(f"{B}/records/{pk}", {"title": "Lab kits (revised)"}, format="json")
    assert patched.status_code == 200 and patched.json()["title"] == "Lab kits (revised)"
    submitted = _post(creator, f"/records/{pk}/submit")
    assert submitted.status_code == 200 and submitted.json()["status"] == "submitted"
    assert submitted.json()["financial_year"] == "2026-27"
    assert len(submitted.json()["documents"]) == 1

    finance = api_client(stub_iam, 201, roles.FINANCE)
    assert _post(finance, f"/records/{pk}/validate").json()["status"] == "finance_validated"

    hod = api_client(stub_iam, 301, roles.HOD)
    decided = _post(hod, f"/records/{pk}/decision",
                    {"decision": "approve", "remarks": "Within plan"})
    assert decided.json()["status"] == "approved"
    assert decided.json()["steps"][0]["decided_role"] == roles.HOD

    finance = api_client(stub_iam, 201, roles.FINANCE)
    done = _post(finance, f"/records/{pk}/processing", {"reference": "VCH-1", "note": "filed"})
    assert done.json()["status"] == "recorded" and done.json()["processing_reference"] == "VCH-1"

    creator = api_client(stub_iam, 101, FACULTY)
    history = creator.get(f"{B}/records/{pk}/history").json()
    assert [h["to_status"] for h in history if h["action"] not in ("create", "add_document",
                                                                   "update_draft")] == [
        "submitted", "finance_validated", "approved", "recorded"]
    assert all(h["actor_role"] for h in history)


def test_a_ta_claim_is_created_submitted_with_its_documents(stub_iam, people, configured):
    client = api_client(stub_iam, 101, FACULTY)
    body = {"kind": "ta", "department": "CSE", "amount": "8000", "purpose": "Conference",
            "trip_start": "2026-01-10", "trip_end": "2026-01-12", "documents": [DOC]}
    out = _post(client, "/records", body)
    assert out.status_code == 201 and out.json()["status"] == "submitted"
    assert client.get(f"{B}/records/{out.json()['id']}").json()["documents"][0]["title"] \
        == "Invoice"
    assert _post(client, "/records", {**body, "documents": []}).status_code == 422


def test_clarification_over_http(stub_iam, people, configured):
    rec = new_expense(people.creator)
    finance = api_client(stub_iam, 201, roles.FINANCE)
    assert _post(finance, f"/records/{rec.pk}/query",
                 {"text": "Which lab?"}).json()["status"] == "query_raised"
    creator = api_client(stub_iam, 101, FACULTY)
    assert _post(creator, f"/records/{rec.pk}/documents", DOC).status_code == 201
    answered = _post(creator, f"/records/{rec.pk}/query-response", {"text": "Embedded lab"})
    assert answered.json()["status"] == "query_responded"
    assert answered.json()["queries"][0]["response"] == "Embedded lab"


def test_errors_use_one_envelope_with_a_stable_code(stub_iam, people, configured):
    creator = api_client(stub_iam, 101, FACULTY)
    draft = _post(creator, "/records", {"kind": "expense"}).json()["id"]

    incomplete = _post(creator, f"/records/{draft}/submit")
    assert incomplete.status_code == 422 and _error(incomplete)["code"] == "submission_incomplete"
    assert {d["field"] for d in _error(incomplete)["details"]} >= {"amount", "documents"}

    assert _post(creator, "/records", {"kind": "loan"}).status_code == 400
    assert _post(creator, f"/records/{draft}/documents",
                 {"title": "x", "link": "http://insecure.test/a"}).status_code == 400
    assert _post(creator, "/records", {**EXPENSE, "amount": "-5"}).status_code == 400
    missing = creator.get(f"{B}/records/99999")
    assert missing.status_code == 404 and _error(missing)["code"] == "not_found"
    assert "request_id" in _error(missing)


def test_state_conflicts_are_409_and_policy_gaps_name_the_fix(stub_iam, people, configured):
    rec = new_expense(people.creator)
    creator = api_client(stub_iam, 101, FACULTY)
    again = _post(creator, f"/records/{rec.pk}/submit")
    assert again.status_code == 409 and _error(again)["code"] == "invalid_transition"
    locked = creator.patch(f"{B}/records/{rec.pk}", {"title": "x"}, format="json")
    assert locked.status_code == 409 and _error(locked)["code"] == "record_locked"


def test_a_decision_needs_remarks_a_valid_choice_and_the_right_role(
        stub_iam, people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    hod = api_client(stub_iam, 301, roles.HOD)
    blank = _post(hod, f"/records/{rec.pk}/decision", {"decision": "approve", "remarks": " "})
    assert blank.status_code == 422 and _error(blank)["code"] == "remarks_required"
    assert _post(hod, f"/records/{rec.pk}/decision",
                 {"decision": "maybe", "remarks": "x"}).status_code == 400
    dean = api_client(stub_iam, 302, roles.DEAN)
    assert _post(dean, f"/records/{rec.pk}/decision",
                 {"decision": "approve", "remarks": "x"}).status_code == 404


def test_a_self_approval_is_403_and_reroutes_the_item(stub_iam, people, configured):
    rec = new_expense(actor(301, FACULTY))
    review.validate(people.finance, rec.pk)
    hod = api_client(stub_iam, 301, roles.HOD)
    refused = _post(hod, f"/records/{rec.pk}/decision",
                    {"decision": "approve", "remarks": "mine"})
    assert refused.status_code == 403 and _error(refused)["code"] == "segregation_of_duties"
    dean = api_client(stub_iam, 302, roles.DEAN)
    assert _post(dean, f"/records/{rec.pk}/decision",
                 {"decision": "approve", "remarks": "independent"}).json()["status"] == "approved"


def test_pagination_returns_a_cursor_and_the_next_page_continues(stub_iam, people, configured):
    for _ in range(3):
        new_expense(people.creator)
    client = api_client(stub_iam, 101, FACULTY)
    first = client.get(f"{B}/records?limit=2").json()
    assert len(first["results"]) == 2 and first["next"]
    second = client.get(first["next"]).json()
    assert len(second["results"]) == 1 and second["next"] is None
    assert {r["id"] for r in first["results"]}.isdisjoint({r["id"] for r in second["results"]})


def test_anomalies_over_http(stub_iam, people, configured):
    rec = new_expense(people.creator)
    finance = api_client(stub_iam, 201, roles.FINANCE)
    flagged = _post(finance, "/anomalies", {"category": "budget", "description": "Overspend",
                                            "record_id": rec.pk})
    assert flagged.status_code == 201 and flagged.json()["status"] == "open"
    pk = flagged.json()["id"]
    assert _post(finance, "/anomalies", {"category": "mood", "description": "x"}).status_code == 400
    assert finance.get(f"{B}/anomalies?status=open").json()["results"][0]["id"] == pk
    escalated = _post(finance, f"/anomalies/{pk}/escalate", {"text": "Above my remit"})
    assert escalated.json()["assigned_role"] == roles.DEAN
    dean = api_client(stub_iam, 302, roles.DEAN)
    resolved = _post(dean, f"/anomalies/{pk}/resolve", {"text": "Reallocated"})
    assert resolved.json()["status"] == "resolved" and resolved.json()["resolved_role"] == "iaa_dean"
    creator = api_client(stub_iam, 101, FACULTY)
    assert _post(creator, "/anomalies", {"category": "budget", "description": "x"}
                 ).status_code == 403


def test_observations_over_http(stub_iam, people, configured):
    rec = new_expense(people.creator)
    auditor = api_client(stub_iam, 401, roles.AUDITOR)
    raised = _post(auditor, "/observations", {"title": "Missing note", "detail": "No sign-off",
                                              "record_id": rec.pk})
    assert raised.status_code == 201 and raised.json()["respondent_user_id"] == 101
    pk = raised.json()["id"]
    creator = api_client(stub_iam, 101, FACULTY)
    assert _post(creator, f"/observations/{pk}/respond",
                 {"corrective_action": "Added", "evidence_link": "ftp://x"}).status_code == 400
    responded = _post(creator, f"/observations/{pk}/respond",
                      {"corrective_action": "Added", "evidence_link": "https://x.test/n"})
    assert responded.json()["status"] == "responded"
    auditor = api_client(stub_iam, 401, roles.AUDITOR)
    assert _post(auditor, f"/observations/{pk}/review",
                 {"verdict": "unsatisfactory"}).status_code == 422
    closed = _post(auditor, f"/observations/{pk}/review", {"verdict": "satisfactory"})
    assert closed.json()["status"] == "closed" and len(closed.json()["responses"]) == 1


def test_reports_summarise_by_scope_and_export_as_csv(stub_iam, people, configured):
    done = new_expense(people.creator)
    new_expense(people.creator, submit=False)                         # drafts are not reported
    review.validate(people.finance, done.pk)
    hod = api_client(stub_iam, 301, roles.HOD)
    _post(hod, f"/records/{done.pk}/decision", {"decision": "approve", "remarks": "ok"})

    finance = api_client(stub_iam, 201, roles.FINANCE)
    summary = finance.get(f"{B}/reports/summary").json()
    assert summary["records"] == [{"kind": "expense", "status": "approved", "count": 1}]
    assert summary["approval_turnaround"][0]["designation"] == roles.HOD
    assert summary["approval_turnaround"][0]["decisions"] == 1
    assert finance.get(f"{B}/reports/summary?financial_year_id={configured.pk}"
                       ).json()["records"][0]["count"] == 1
    assert finance.get(f"{B}/reports/summary?financial_year_id=9999").json()["records"] == []

    export = finance.get(f"{B}/reports/export")
    assert export.status_code == 200 and export["Content-Type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(b"".join(export.streaming_content).decode())))
    assert rows[0][:3] == ["id", "kind", "status"] and len(rows) == 2
    assert rows[1][2] == "approved" and rows[1][7] == "2026-27"

    creator = api_client(stub_iam, 101, FACULTY)
    assert creator.get(f"{B}/reports/export").status_code == 403


def test_an_hod_report_covers_only_their_own_scope(stub_iam, people, configured):
    mine = new_expense(people.creator)
    other = new_expense(people.creator, department="ECE")
    review.validate(people.finance, mine.pk)
    review.validate(people.finance, other.pk)
    hod = api_client(stub_iam, 301, roles.HOD)
    assert hod.get(f"{B}/reports/summary").json()["records"] == [
        {"kind": "expense", "status": "finance_validated", "count": 1}]


def test_configuration_over_http(stub_iam, people):
    admin = api_client(stub_iam, 501, roles.SYSTEM_ADMIN)
    year = _post(admin, "/config/financial-years",
                 {"code": "2026-27", "starts_on": "2026-04-01", "ends_on": "2027-03-31"})
    assert year.status_code == 201
    assert _post(admin, "/config/financial-years",
                 {"code": "dup", "starts_on": "2026-06-01", "ends_on": "2026-09-30"}
                 ).status_code == 409
    entry = _post(admin, "/config/budget-entries", {"financial_year_id": year.json()["id"],
                                                    "department": "CSE", "kind": "allocation",
                                                    "amount": "500000"})
    assert entry.status_code == 201 and entry.json()["financial_year"] == "2026-27"
    assert _post(admin, "/config/budget-entries",
                 {"financial_year_id": year.json()["id"], "department": "CSE",
                  "kind": "commitment", "amount": "-5"}).status_code == 400
    listed = admin.get(f"{B}/config/budget-entries?financial_year_id={year.json()['id']}")
    assert [e["amount"] for e in listed.json()["results"]] == ["500000.00"]
    assert admin.get(f"{B}/config/budget-entries?financial_year_id=abc").status_code == 400

    published = _post(admin, "/config/policies", POLICY)
    assert published.status_code == 201 and published.json()["approval_timeout_hours"] == 48
    assert len(admin.get(f"{B}/config/policies").json()) == 1
    bad = _post(admin, "/config/policies", {**POLICY, "approval_timeout_hours": 0})
    assert bad.status_code == 422 and _error(bad)["code"] == "policy_invalid"
    assert _error(bad)["details"]
    past = _post(admin, "/config/policies", {**POLICY, "effective_from": "2020-01-01T00:00:00Z"})
    assert past.status_code == 422 and _error(past)["code"] == "backdated_policy"


def test_configuration_is_readable_by_none_but_the_admin_and_writable_by_none_else(
        stub_iam, people, configured):
    for uid, role in ((201, roles.FINANCE), (301, roles.HOD), (401, roles.AUDITOR),
                      (101, FACULTY)):
        client = api_client(stub_iam, uid, role)
        assert client.get(f"{B}/config/policies").status_code == 403
        assert _post(client, "/config/financial-years", {}).status_code == 403


def test_the_notification_feed_lists_messages_and_pending_counts(stub_iam, people, configured):
    new_expense(people.creator)
    finance = api_client(stub_iam, 201, roles.FINANCE)
    feed = finance.get(f"{B}/notifications").json()
    assert feed["pending"]["to_review"] == 1
    assert feed["notifications"][0]["kind"] == "submitted"
