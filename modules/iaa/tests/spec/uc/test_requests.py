"""UC specification cases for request submission and Finance review."""
import pytest

from modules.iaa.domain import roles
from modules.iaa.models import FinancialRecord
from modules.iaa.tests.spec.uc.test_support import (
    CREATOR,
    FINANCE,
    IaaHttp,
)

pytestmark = pytest.mark.django_db


def test_iaa_tc_101_01__uc_101_main_success_scenario_create_draft(stub_iam, configured):
    """IAA-TC-101-01 / IAA-UC-101 Main Success Scenario: save an editable Draft with history."""
    run = IaaHttp(stub_iam)

    draft = run.expense_draft()
    edited = run.patch(CREATOR, f"/records/{draft['id']}", {"title": "Updated draft title"})
    history = run.history(draft["id"])

    assert draft["status"] == "draft"
    assert edited["status"] == "draft"
    assert edited["title"] == "Updated draft title"
    assert any(item["action"] == "create" and item["to_status"] == "draft"
               for item in history)


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE saves incomplete drafts but does not expose missing submission "
    "fields until a separate submit attempt."
))
def test_iaa_tc_101_02__uc_101_incomplete_draft_alternative():
    """IAA-TC-101-02 / IAA-UC-101 Alternative Flow - Incomplete Draft."""


def test_iaa_tc_101_03__uc_101_authorization_failure_denies_creation(stub_iam, configured):
    """IAA-TC-101-03 / IAA-UC-101 Exception Flow - Authorization failure."""
    run = IaaHttp(stub_iam)
    before = FinancialRecord.objects.count()

    refused = run.post_response((501, roles.SYSTEM_ADMIN), "/records", {
        "kind": "expense", "department": "CSE", "request_type": "voucher",
        "title": "Unauthorized request", "description": "Attempted by an admin",
        "amount": "10000",
    })

    assert refused.status_code == 403
    assert FinancialRecord.objects.count() == before


def test_iaa_tc_102_01__uc_102_main_success_scenario_submit_complete_draft(stub_iam, configured):
    """IAA-TC-102-01 / IAA-UC-102 Main Success Scenario: submit, lock, route, log, notify."""
    run = IaaHttp(stub_iam)
    draft = run.expense_draft()
    run.post(CREATOR, f"/records/{draft['id']}/documents", {
        "title": "Invoice", "link": "https://files.example/invoice.pdf",
    }, expected_status=201)

    submitted = run.post(CREATOR, f"/records/{draft['id']}/submit")
    refused_edit = run.request(CREATOR, "patch", f"/records/{draft['id']}", {
        "title": "Ordinary post-submit edit",
    })
    finance_queue = run.get(FINANCE, "/records?queue=finance_review")
    history = run.history(draft["id"])
    creator_feed = run.get(CREATOR, "/notifications")
    finance_feed = run.get(FINANCE, "/notifications")

    assert submitted["status"] == "submitted"
    assert refused_edit.status_code == 409
    assert run.get(CREATOR, f"/records/{draft['id']}")["title"] == draft["title"]
    assert draft["id"] in {item["id"] for item in finance_queue["results"]}
    assert any(item["action"] == "submit" and item["to_status"] == "submitted"
               for item in history)
    assert any(item["kind"] == "submitted" and item["entity_id"] == draft["id"]
               for item in creator_feed["notifications"])
    assert any(item["kind"] == "submitted" and item["entity_id"] == draft["id"]
               for item in finance_feed["notifications"])


def test_iaa_tc_102_02__uc_102_validation_failure_keeps_request_in_draft(stub_iam, configured):
    """IAA-TC-102-02 / IAA-UC-102 Alternative Flow - Validation fails."""
    run = IaaHttp(stub_iam)
    draft = run.expense_draft(amount=None, title="", description="")
    before = run.history(draft["id"])

    refused = run.post_response(CREATOR, f"/records/{draft['id']}/submit")
    after = run.get(CREATOR, f"/records/{draft['id']}")

    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "submission_incomplete"
    assert {item["field"] for item in refused.json()["error"]["details"]} >= {
        "amount", "documents",
    }
    assert after["status"] == "draft"
    assert run.history(draft["id"]) == before


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE has no separate Finance-routing service or failure-injection "
    "interface during submission; submission creates internal role notifications directly."
))
def test_iaa_tc_102_03__uc_102_routing_failure_preserves_submitted_request():
    """IAA-TC-102-03 / IAA-UC-102 Exception Flow - Routing failure."""


def test_iaa_tc_103_01__uc_103_main_success_scenario_validate_and_route(stub_iam, configured):
    """IAA-TC-103-01 / IAA-UC-103 Main Success Scenario: validate and route to approval."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    validated = run.validated(submitted["id"])
    finance_view = run.get(FINANCE, f"/records/{submitted['id']}")
    approver_feed = run.get((301, roles.HOD), "/notifications")
    history = run.history(submitted["id"])

    assert validated["status"] == "finance_validated"
    assert finance_view["steps"][0]["designation"] == roles.HOD
    assert finance_view["steps"][0]["status"] == "pending"
    assert any(item["kind"] == "approval_needed" and item["entity_id"] == submitted["id"]
               for item in approver_feed["notifications"])
    assert any(item["to_status"] == "finance_validated" for item in history)


def test_iaa_tc_103_02__uc_103_clarification_needed_alternative(stub_iam, configured):
    """IAA-TC-103-02 / IAA-UC-103 Alternative Flow - Clarification needed."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    queried = run.post(FINANCE, f"/records/{submitted['id']}/query", {
        "text": "Please provide the original invoice.",
    })
    creator_feed = run.get(CREATOR, "/notifications")

    assert queried["status"] == "query_raised"
    assert queried["queries"][0]["question"] == "Please provide the original invoice."
    assert any(item["kind"] == "query_raised" and item["entity_id"] == submitted["id"]
               for item in creator_feed["notifications"])


def test_iaa_tc_103_03__uc_103_material_anomaly_blocks_finance_validation(
        stub_iam, configured):
    """IAA-TC-103-03 / IAA-UC-103 Alternative Flow - Material anomaly detected."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(department="ECE", amount="10000")

    validated = run.validated(submitted["id"])
    anomalies = run.get(FINANCE, "/anomalies")

    assert validated["status"] != "finance_validated"
    assert any(item["record"] == submitted["id"] and item["status"] == "open"
               for item in anomalies["results"])


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE treats an absent departmental allocation as zero available budget "
    "and does not distinguish an unavailable budget reference from a real zero balance."
))
def test_iaa_tc_103_04__uc_103_required_budget_reference_unavailable():
    """IAA-TC-103-04 / IAA-UC-103 Exception Flow - Required budget reference unavailable."""


def test_iaa_tc_104_01__uc_104_main_success_scenario_respond_to_query(stub_iam, configured):
    """IAA-TC-104-01 / IAA-UC-104 Main Success Scenario: respond with information and evidence."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.post(FINANCE, f"/records/{submitted['id']}/query", {"text": "Attach the invoice."})

    run.post(CREATOR, f"/records/{submitted['id']}/documents", {
        "title": "Original invoice", "link": "https://files.example/original-invoice.pdf",
    }, expected_status=201)
    answered = run.post(CREATOR, f"/records/{submitted['id']}/query-response", {
        "text": "The original invoice is attached.",
    })
    finance_feed = run.get(FINANCE, "/notifications")

    assert answered["status"] == "query_responded"
    assert answered["queries"][0]["response"] == "The original invoice is attached."
    assert any(item["title"] == "Original invoice" for item in answered["documents"])
    assert any(item["kind"] == "query_responded" and item["entity_id"] == submitted["id"]
               for item in finance_feed["notifications"])


def test_iaa_tc_104_02__uc_104_incomplete_response_is_refused(stub_iam, configured):
    """IAA-TC-104-02 / IAA-UC-104 Alternative Flow - Response incomplete."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.post(FINANCE, f"/records/{submitted['id']}/query", {"text": "Explain this item."})
    before = run.get(CREATOR, f"/records/{submitted['id']}")

    refused = run.post_response(CREATOR, f"/records/{submitted['id']}/query-response", {
        "text": "",
    })
    after = run.get(CREATOR, f"/records/{submitted['id']}")

    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "response_required"
    assert "response" in refused.json()["error"]["message"].lower()
    assert after["status"] == before["status"] == "query_raised"
    assert after["queries"][0]["response"] == ""
