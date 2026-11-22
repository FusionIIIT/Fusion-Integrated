"""FR specification cases for reports, status tracking, and notifications."""
import pytest

from modules.iaa.tests.spec.fr.test_support import (
    AUDITOR,
    CREATOR,
    FINANCE,
    HOD,
    IaaHttp,
)

pytestmark = pytest.mark.django_db


def test_iaa_t058__afr_iaa_058_authorized_user_views_request_status_report(stub_iam, configured):
    """IAA-T058 / AFR-IAA-058: an authorized reporting user can view status summaries."""
    run = IaaHttp(stub_iam)
    run.submitted_expense()

    report = run.get(FINANCE, "/reports/summary")

    assert report["records"] == [{"kind": "expense", "status": "submitted", "count": 1}]


def test_iaa_t059__afr_iaa_059_report_approval_turnaround_information(stub_iam, configured):
    """IAA-T059 / AFR-IAA-059: the report includes approval turnaround information."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    run.decide(submitted["id"], who=HOD)

    report = run.get(FINANCE, "/reports/summary")

    assert len(report["approval_turnaround"]) == 1
    turnaround = report["approval_turnaround"][0]
    assert turnaround["designation"] == HOD[1]
    assert turnaround["decisions"] == 1
    assert turnaround["average_hours"] >= 0


def test_iaa_t060__afr_iaa_060_report_anomaly_and_audit_information(stub_iam, configured):
    """IAA-T060 / AFR-IAA-060: authorized reports include anomalies and observations."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.post(FINANCE, "/anomalies", {
        "category": "financial", "description": "A ledger entry needs review.",
        "record_id": submitted["id"],
    }, expected_status=201)
    run.post(AUDITOR, "/observations", {
        "title": "Audit finding", "detail": "A supporting note is missing.",
        "record_id": submitted["id"],
    }, expected_status=201)

    report = run.get(FINANCE, "/reports/summary")

    assert report["anomalies"] == [{"category": "financial", "status": "open", "count": 1}]
    assert report["observations"] == [{"status": "open", "count": 1}]


def test_iaa_t061__afr_iaa_061_export_read_only_report(stub_iam, configured):
    """IAA-T061 / AFR-IAA-061: an authorized user can export a report for offline reference."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    before = run.get(CREATOR, f"/records/{submitted['id']}")

    export = run.get(FINANCE, "/reports/export")
    csv_text = b"".join(export.streaming_content).decode("utf-8")
    after = run.get(CREATOR, f"/records/{submitted['id']}")

    assert export.status_code == 200
    assert export["Content-Type"].startswith("text/csv")
    assert csv_text.startswith("id,kind,status,department,request_type,title,amount")
    assert f"{submitted['id']},expense,submitted" in csv_text
    assert after["status"] == before["status"]


def test_iaa_t062__afr_iaa_062_basic_user_tracks_own_requests_and_ta_claims(
        stub_iam, configured):
    """IAA-T062 / AFR-IAA-062: a Basic User can track their own request and TA histories."""
    run = IaaHttp(stub_iam)
    expense = run.submitted_expense()
    ta = run.submitted_ta(amount="10000")

    own_records = run.get(CREATOR, "/records")
    expense_history = run.history(expense["id"])
    ta_history = run.history(ta["id"])

    assert {expense["id"], ta["id"]} <= {item["id"] for item in own_records["results"]}
    assert any(item["to_status"] == "submitted" for item in expense_history)
    assert any(item["to_status"] == "submitted" for item in ta_history)


def test_iaa_t063__afr_iaa_063_notify_actors_of_submission_and_status_change(stub_iam, configured):
    """IAA-T063 / AFR-IAA-063: submission notifications reach the creator and Finance."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    creator_feed = run.get(CREATOR, "/notifications")
    finance_feed = run.get(FINANCE, "/notifications")

    assert any(item["kind"] == "submitted" and item["entity_id"] == submitted["id"]
               for item in creator_feed["notifications"])
    assert any(item["kind"] == "submitted" and item["entity_id"] == submitted["id"]
               for item in finance_feed["notifications"])


def test_iaa_t064__afr_iaa_064_notify_relevant_actors_of_approval_event(stub_iam, configured):
    """IAA-T064 / AFR-IAA-064: approval notifications reach the creator and Finance queue."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    run.decide(submitted["id"], who=HOD)

    creator_feed = run.get(CREATOR, "/notifications")
    finance_feed = run.get(FINANCE, "/notifications")

    assert any(item["kind"] == "approved" and item["entity_id"] == submitted["id"]
               for item in creator_feed["notifications"])
    assert any(item["kind"] == "ready_to_record" and item["entity_id"] == submitted["id"]
               for item in finance_feed["notifications"])


def test_iaa_t065__afr_iaa_065_notify_anomaly_and_observation_events(stub_iam, configured):
    """IAA-T065 / AFR-IAA-065: anomaly and observation events notify their relevant actors."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    anomaly = run.post(FINANCE, "/anomalies", {
        "category": "budget", "description": "Budget needs reconciliation.",
        "record_id": submitted["id"],
    }, expected_status=201)
    observation = run.post(AUDITOR, "/observations", {
        "title": "Audit follow-up", "detail": "Attach the missing note.",
        "record_id": submitted["id"],
    }, expected_status=201)

    finance_feed = run.get(FINANCE, "/notifications")
    creator_feed = run.get(CREATOR, "/notifications")

    assert any(item["kind"] == "anomaly" and item["entity_id"] == anomaly["id"]
               for item in finance_feed["notifications"])
    assert any(item["kind"] == "observation" and item["entity_id"] == observation["id"]
               for item in creator_feed["notifications"])


def test_iaa_t066__afr_iaa_066_notify_pending_and_overdue_followups(stub_iam, configured):
    """IAA-T066 / AFR-IAA-066: pending and overdue approval actions notify relevant actors."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])

    hod_before = run.get(HOD, "/notifications")
    run.overdue()
    dean_after = run.get((302, "iaa_dean"), "/notifications")
    creator_after = run.get(CREATOR, "/notifications")

    assert any(item["kind"] == "approval_needed" and item["entity_id"] == submitted["id"]
               for item in hod_before["notifications"])
    assert any(item["kind"] == "escalated" and item["entity_id"] == submitted["id"]
               for item in dean_after["notifications"])
    assert any(item["kind"] == "escalated" and item["entity_id"] == submitted["id"]
               for item in creator_after["notifications"])


def test_iaa_t067__afr_iaa_067_notification_is_visible_on_fusion_dashboard(stub_iam, configured):
    """IAA-T067 / AFR-IAA-067: the generated IAA notification is visible on the dashboard feed."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    dashboard = run.get(CREATOR, "/notifications")

    assert any(item["entity"] == "record" and item["entity_id"] == submitted["id"]
               and item["kind"] == "submitted" for item in dashboard["notifications"])
