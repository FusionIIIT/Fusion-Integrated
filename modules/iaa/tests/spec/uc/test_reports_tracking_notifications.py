"""UC specification cases for reports, tracking, and notifications."""
import pytest

from modules.iaa.tests.spec.uc.test_support import (
    AUDITOR,
    CREATOR,
    FINANCE,
    HOD,
    OTHER,
    IaaHttp,
)

pytestmark = pytest.mark.django_db


def test_iaa_tc_601_01__uc_601_main_success_role_scoped_read_only_report(
        stub_iam, configured):
    """IAA-TC-601-01 / IAA-UC-601 Main Success Scenario."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    run.decide(submitted["id"], who=HOD)
    run.post(FINANCE, "/anomalies", {
        "category": "financial", "description": "Check the ledger entry.",
        "record_id": submitted["id"],
    }, expected_status=201)
    run.post(AUDITOR, "/observations", {
        "title": "Audit note", "detail": "A supporting note needs review.",
        "record_id": submitted["id"],
    }, expected_status=201)
    before = run.get(FINANCE, f"/records/{submitted['id']}")

    report = run.get(FINANCE, "/reports/summary")
    after = run.get(FINANCE, f"/records/{submitted['id']}")

    assert report["records"] == [{"kind": "expense", "status": "approved", "count": 1}]
    assert report["approval_turnaround"][0]["decisions"] == 1
    assert report["anomalies"] == [{"category": "financial", "status": "open", "count": 1}]
    assert report["observations"] == [{"status": "open", "count": 1}]
    assert after["status"] == before["status"] == "approved"


def test_iaa_tc_602_01__uc_602_main_success_export_authorized_report(stub_iam, configured):
    """IAA-TC-602-01 / IAA-UC-602 Main Success Scenario."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    export = run.get(FINANCE, "/reports/export")
    contents = b"".join(export.streaming_content).decode("utf-8")

    assert export.status_code == 200
    assert export["Content-Type"].startswith("text/csv")
    assert contents.startswith("id,kind,status,department,request_type,title,amount")
    assert f"{submitted['id']},expense,submitted" in contents


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: the A8_BASE export endpoint returns a header-only CSV for an empty report "
    "and exposes no informational no-data response."
))
def test_iaa_tc_602_02__uc_602_no_exportable_content_alternative():
    """IAA-TC-602-02 / IAA-UC-602 Alternative Flow - No data/export content."""


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE has no export failure injection or external export adapter that can "
    "be failed through an available interface."
))
def test_iaa_tc_602_03__uc_602_export_generation_failure():
    """IAA-TC-602-03 / IAA-UC-602 Exception Flow - Export generation fails."""


def test_iaa_tc_603_01__uc_603_main_success_own_records_and_visible_history(
        stub_iam, configured):
    """IAA-TC-603-01 / IAA-UC-603 Main Success Scenario."""
    run = IaaHttp(stub_iam)
    expense = run.submitted_expense()
    ta = run.submitted_ta(amount="10000")

    own_records = run.get(CREATOR, "/records")
    expense_detail = run.get(CREATOR, f"/records/{expense['id']}")
    ta_detail = run.get(CREATOR, f"/records/{ta['id']}")
    expense_history = run.history(expense["id"])
    ta_history = run.history(ta["id"])

    assert {expense["id"], ta["id"]} <= {item["id"] for item in own_records["results"]}
    assert expense_detail["status"] == "submitted"
    assert ta_detail["status"] == "submitted"
    assert any(item["to_status"] == "submitted" for item in expense_history)
    assert any(item["to_status"] == "submitted" for item in ta_history)


def test_iaa_tc_603_02__uc_603_no_matching_records_empty_state(stub_iam, configured):
    """IAA-TC-603-02 / IAA-UC-603 Alternative Flow - No matching records."""
    run = IaaHttp(stub_iam)

    empty = run.get(OTHER, "/records")

    assert empty["results"] == []
    assert empty["next"] is None


def test_iaa_tc_603_03__uc_603_deny_record_outside_ownership_scope(stub_iam, configured):
    """IAA-TC-603-03 / IAA-UC-603 Exception Flow - Record outside permitted ownership/scope."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    refused = run.get_response(OTHER, f"/records/{submitted['id']}")
    after = run.get(CREATOR, f"/records/{submitted['id']}")

    assert refused.status_code == 404
    assert after["status"] == submitted["status"] == "submitted"


def test_iaa_tc_604_01__uc_604_main_success_permitted_notifications_and_pending_actions(
        stub_iam, configured):
    """IAA-TC-604-01 / IAA-UC-604 Main Success Scenario."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(amount="60000")
    run.validated(submitted["id"])

    feed = run.get(HOD, "/notifications")
    approval_notice = next(item for item in feed["notifications"]
                           if item["entity_id"] == submitted["id"]
                           and item["kind"] == "approval_needed")
    target = run.get(HOD, f"/records/{approval_notice['entity_id']}")

    assert approval_notice["entity"] == "record"
    assert target["id"] == submitted["id"]
    assert target["status"] == "finance_validated"
    assert feed["pending"]


def test_iaa_tc_604_02__uc_604_no_notifications_empty_state(stub_iam, configured):
    """IAA-TC-604-02 / IAA-UC-604 Alternative Flow - No notifications."""
    run = IaaHttp(stub_iam)

    feed = run.get(OTHER, "/notifications")

    assert feed["notifications"] == []
    assert all(value == 0 for value in feed["pending"].values())


def test_iaa_tc_604_03__uc_604_notification_target_is_no_longer_authorized(
        stub_iam, configured):
    """IAA-TC-604-03 / IAA-UC-604 Exception Flow - Notification target no longer authorized."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(amount="60000")
    run.validated(submitted["id"])
    run.decide(submitted["id"], who=HOD, remarks="First approval completed")
    feed = run.get(HOD, "/notifications")
    notice = next(item for item in feed["notifications"]
                  if item["entity_id"] == submitted["id"]
                  and item["kind"] == "approval_needed")

    refused = run.get_response(HOD, f"/records/{notice['entity_id']}")
    creator_view = run.get(CREATOR, f"/records/{submitted['id']}")

    assert refused.status_code == 404
    assert creator_view["status"] == "approval_pending"
