"""FR specification cases for expense and voucher records."""
import pytest

from modules.iaa.domain import roles
from modules.iaa.tests.spec.fr.test_support import CREATOR, FINANCE, IaaHttp

pytestmark = pytest.mark.django_db


def test_iaa_t001__afr_iaa_001_create_and_save_an_expense_draft(stub_iam, configured):
    """IAA-T001 / AFR-IAA-001: create and save an expense/voucher draft."""
    run = IaaHttp(stub_iam)

    draft = run.expense_draft()

    assert draft["status"] == "draft"


def test_iaa_t002__afr_iaa_002_enter_required_request_details(stub_iam, configured):
    """IAA-T002 / AFR-IAA-002: entered request details are retained."""
    run = IaaHttp(stub_iam)
    draft = run.expense_draft(amount="10000")

    updated = run.patch(CREATOR, f"/records/{draft['id']}", {
        "request_type": "reimbursement", "amount": "12000.00", "department": "CSE",
        "description": "Conference travel", "title": "Travel reimbursement",
    })

    assert updated["request_type"] == "reimbursement"
    assert updated["amount"] == "12000.00"
    assert updated["department"] == "CSE"
    assert updated["description"] == "Conference travel"
    assert updated["title"] == "Travel reimbursement"


def test_iaa_t003__afr_iaa_003_attach_supporting_document(stub_iam, configured):
    """IAA-T003 / AFR-IAA-003: a supporting document is associated with the draft."""
    run = IaaHttp(stub_iam)
    draft = run.expense_draft()

    run.post(CREATOR, f"/records/{draft['id']}/documents", {
        "title": "Invoice", "link": "https://files.example/invoice.pdf",
    }, expected_status=201)
    detail = run.get(CREATOR, f"/records/{draft['id']}")

    assert len(detail["documents"]) == 1
    assert detail["documents"][0]["title"] == "Invoice"
    assert detail["documents"][0]["link"] == "https://files.example/invoice.pdf"
    assert detail["documents"][0]["added_by"] == 101


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: saving a draft has no interface that reports which submission fields are "
    "missing; missing-field details are only returned by the separate submit action."
))
def test_iaa_t004__afr_iaa_004_save_incomplete_draft_and_identify_missing_information():
    """IAA-T004 / AFR-IAA-004: saving an incomplete draft identifies missing submission fields."""


def test_iaa_t005__afr_iaa_005_submit_complete_expense_draft(stub_iam, configured):
    """IAA-T005 / AFR-IAA-005: a complete draft can be formally submitted."""
    run = IaaHttp(stub_iam)
    draft = run.expense_draft()
    run.post(CREATOR, f"/records/{draft['id']}/documents", {
        "title": "Invoice", "link": "https://files.example/invoice.pdf",
    }, expected_status=201)

    submitted = run.post(CREATOR, f"/records/{draft['id']}/submit")

    assert submitted["status"] == "submitted"


def test_iaa_t006__afr_iaa_006_block_submission_with_missing_information(stub_iam, configured):
    """IAA-T006 / AFR-IAA-006: incomplete submission is refused without changing the draft."""
    run = IaaHttp(stub_iam)
    draft = run.expense_draft(amount=None, title="", description="")
    before = run.history(draft["id"])

    refused = run.request(CREATOR, "post", f"/records/{draft['id']}/submit")
    after = run.get(CREATOR, f"/records/{draft['id']}")

    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "submission_incomplete"
    assert {item["field"] for item in refused.json()["error"]["details"]} >= {
        "amount", "documents",
    }
    assert after["status"] == "draft"
    assert after["title"] == ""
    assert run.history(draft["id"]) == before


def test_iaa_t007__afr_iaa_007_submit_and_route_request_to_finance(stub_iam, configured):
    """IAA-T007 / AFR-IAA-007: submission sets status and puts the request in Finance review."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    finance_queue = run.get(FINANCE, "/records?queue=finance_review")

    assert submitted["status"] == "submitted"
    assert submitted["id"] in {item["id"] for item in finance_queue["results"]}


def test_iaa_t008__afr_iaa_008_prevent_ordinary_creator_edits_after_submission(
        stub_iam, configured):
    """IAA-T008 / AFR-IAA-008: ordinary post-submission creator edits are refused unchanged."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    before = run.get(CREATOR, f"/records/{submitted['id']}")
    history_before = run.history(submitted["id"])

    refused = run.request(CREATOR, "patch", f"/records/{submitted['id']}",
                          {"title": "Changed after submission"})
    after = run.get(CREATOR, f"/records/{submitted['id']}")

    assert refused.status_code == 409
    assert after["status"] == before["status"] == "submitted"
    assert after["title"] == before["title"]
    assert run.history(submitted["id"]) == history_before


def test_iaa_t009__afr_iaa_009_view_request_status_and_action_history(stub_iam, configured):
    """IAA-T009 / AFR-IAA-009: current request status and recorded actions are available."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    detail = run.get(CREATOR, f"/records/{submitted['id']}")
    history = run.history(submitted["id"])

    assert detail["status"] == "submitted"
    assert any(item["action"] == "submit" and item["to_status"] == "submitted"
               for item in history)


def test_iaa_t010__afr_iaa_010_lifecycle_history_records_timestamp_and_identity(
        stub_iam, configured):
    """IAA-T010 / AFR-IAA-010: a lifecycle history item has its timestamp and actor identity."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    submit_action = next(item for item in run.history(submitted["id"])
                         if item["action"] == "submit")

    assert submit_action["actor_user_id"] == 101
    assert submit_action["actor_role"] == "faculty"
    assert submit_action["created_at"]


def test_iaa_t011__afr_iaa_011_finance_can_review_a_submitted_request(stub_iam, configured):
    """IAA-T011 / AFR-IAA-011: Finance Staff can open a submitted request for review."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    visible = run.get(FINANCE, f"/records/{submitted['id']}")

    assert visible["id"] == submitted["id"]
    assert visible["status"] == "submitted"


def test_iaa_t012__afr_iaa_012_validate_financial_documents(stub_iam, configured):
    """IAA-T012 / AFR-IAA-012: Finance validation accepts a request with its financial document."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    finance_view = run.get(FINANCE, f"/records/{submitted['id']}")

    validated = run.validated(submitted["id"])

    assert finance_view["documents"][0]["title"] == "Invoice"
    assert validated["status"] == "finance_validated"


def test_iaa_t013__afr_iaa_013_validate_request_policy_compliance(stub_iam, configured):
    """IAA-T013 / AFR-IAA-013: Finance can validate a policy-compliant submitted request."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(amount="12000")

    validated = run.validated(submitted["id"])

    assert validated["status"] == "finance_validated"
    assert validated["amount"] == "12000.00"


def test_iaa_t014__afr_iaa_014_check_request_against_available_budget(stub_iam, configured):
    """IAA-T014 / AFR-IAA-014: Finance validation checks the funded department budget."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(department="CSE", amount="10000")

    validated = run.validated(submitted["id"])
    anomalies = run.get(FINANCE, "/anomalies")

    assert validated["status"] == "finance_validated"
    assert not anomalies["results"]


def test_iaa_t015__afr_iaa_015_finance_requests_creator_clarification(stub_iam, configured):
    """IAA-T015 / AFR-IAA-015: a Finance clarification request is recorded for the creator."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    queried = run.post(FINANCE, f"/records/{submitted['id']}/query",
                       {"text": "Please provide the original invoice."})

    assert queried["status"] == "query_raised"
    assert queried["queries"][0]["question"] == "Please provide the original invoice."


def test_iaa_t016__afr_iaa_016_creator_responds_to_finance_clarification(stub_iam, configured):
    """IAA-T016 / AFR-IAA-016: the creator's structured clarification response is recorded."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.post(FINANCE, f"/records/{submitted['id']}/query", {"text": "Which lab used this?"})

    answered = run.post(CREATOR, f"/records/{submitted['id']}/query-response",
                        {"text": "The electronics lab."})

    assert answered["status"] == "query_responded"
    assert answered["queries"][0]["response"] == "The electronics lab."


def test_iaa_t017__afr_iaa_017_resume_validation_after_clarification(stub_iam, configured):
    """IAA-T017 / AFR-IAA-017: Finance validation resumes after the creator answers."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.post(FINANCE, f"/records/{submitted['id']}/query", {"text": "Attach invoice."})
    run.post(CREATOR, f"/records/{submitted['id']}/query-response",
             {"text": "Invoice attached."})

    validated = run.validated(submitted["id"])

    assert validated["status"] == "finance_validated"
    assert validated["queries"][0]["response"] == "Invoice attached."


def test_iaa_t018__afr_iaa_018_handoff_finance_validated_request_to_route(stub_iam, configured):
    """IAA-T018 / AFR-IAA-018: Finance validation creates the configured approval hand-off."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    validated = run.validated(submitted["id"])

    assert validated["status"] == "finance_validated"
    assert validated["route_levels"] == [roles.HOD]
    assert validated["steps"][0]["designation"] == roles.HOD
    assert validated["steps"][0]["status"] == "pending"


def test_iaa_t019__afr_iaa_019_finance_records_internal_expense_processing(
        stub_iam, configured):
    """IAA-T019 / AFR-IAA-019: Finance records approved processing without a payment transfer."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    run.decide(submitted["id"], who=(301, roles.HOD), remarks="Approved for internal processing")

    recorded = run.post(FINANCE, f"/records/{submitted['id']}/processing", {
        "reference": "VCH-FR-019", "note": "Filed internally",
    })

    assert recorded["status"] == "recorded"
    assert recorded["processing_reference"] == "VCH-FR-019"


def test_iaa_t020__afr_iaa_020_completed_expense_record_is_available_to_auditor(
        stub_iam, configured):
    """IAA-T020 / AFR-IAA-020: the completed financial record remains available for audit."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    run.decide(submitted["id"], who=(301, roles.HOD))
    run.post(FINANCE, f"/records/{submitted['id']}/processing", {"reference": "VCH-FR-020"})

    auditor_view = run.get((401, roles.AUDITOR), f"/records/{submitted['id']}")

    assert auditor_view["id"] == submitted["id"]
    assert auditor_view["status"] == "recorded"
