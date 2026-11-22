"""Frozen WF design workflows exercised through the IAA HTTP API."""

import pytest

from modules.iaa.domain import roles
from modules.iaa.tests.spec.fr.test_support import (
    AUDITOR,
    CREATOR,
    DEAN,
    FINANCE,
    HOD,
    IaaHttp,
    published_policy,
)

pytestmark = pytest.mark.django_db


def expense_route(*levels):
    return [
        {"kind": "expense", "min_amount": "0", "levels": list(levels),
         "escalation_designation": roles.DIRECTOR},
        {"kind": "ta", "min_amount": "0", "levels": [roles.HOD],
         "escalation_designation": roles.DEAN},
    ]


def ta_route(*levels):
    return [
        {"kind": "expense", "min_amount": "0", "levels": [roles.HOD],
         "escalation_designation": roles.DEAN},
        {"kind": "ta", "min_amount": "0", "levels": list(levels),
         "escalation_designation": roles.DIRECTOR},
    ]


def manual_anomaly(run):
    return run.post(FINANCE, "/anomalies", {
        "category": "budget", "description": "Material discrepancy requires review.",
    }, expected_status=201)


def automatic_anomaly(run):
    claim = run.submitted_expense(department="ECE", amount="10000")
    run.validated(claim["id"])
    items = run.get(FINANCE, "/anomalies?status=open")["results"]
    return next(item for item in items if item["record"] == claim["id"]
                and item["source"] == "automatic")


def observation(run, submitted):
    return run.post(AUDITOR, "/observations", {
        "title": "Supporting evidence required",
        "detail": "Please provide evidence of the corrective action.",
        "record_id": submitted["id"],
    }, expected_status=201)


def test_iaa_wf_01__bw_iaa_01_standard_success_path(stub_iam, configured):
    """IAA-WF-01 / BW-IAA-01 standard success path."""
    run = IaaHttp(stub_iam)
    draft = run.expense_draft()
    run.post(CREATOR, f"/records/{draft['id']}/documents", {
        "title": "Invoice", "link": "https://files.example/invoice.pdf",
    }, expected_status=201)
    submitted = run.post(CREATOR, f"/records/{draft['id']}/submit")
    validated = run.validated(draft["id"])
    approved = run.decide(draft["id"], who=HOD)
    recorded = run.post(FINANCE, f"/records/{draft['id']}/processing", {"reference": "WF-01"})
    assert [draft["status"], submitted["status"], validated["status"],
            approved["status"], recorded["status"]] == [
        "draft", "submitted", "finance_validated", "approved", "recorded"]


def test_iaa_wf_02__bw_iaa_02_additional_approval_traversal(stub_iam, configured):
    """IAA-WF-02 / BW-IAA-02 additional approval traversal."""
    run = IaaHttp(stub_iam)
    published_policy(run, routes=expense_route(roles.HOD, roles.DEAN))
    submitted = run.submitted_expense(amount="60000")
    validated = run.validated(submitted["id"])
    first = run.decide(submitted["id"], who=HOD)
    second = run.decide(submitted["id"], who=DEAN)
    recorded = run.post(FINANCE, f"/records/{submitted['id']}/processing", {"reference": "WF-02"})
    assert [validated["status"], first["status"], second["status"], recorded["status"]] == [
        "finance_validated", "approval_pending", "approved", "recorded"]


def test_iaa_wf_03__bw_iaa_03_expense_voucher_rejection_path(stub_iam, configured):
    """IAA-WF-03 / BW-IAA-03 expense/voucher rejection path."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    rejected = run.decide(submitted["id"], who=HOD, decision="reject", remarks="Not eligible.")
    assert rejected["status"] == "rejected"


def test_iaa_wf_04__bw_iaa_04_expense_clarification_traversal(stub_iam, configured):
    """IAA-WF-04 / BW-IAA-04 expense/voucher clarification traversal."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    queried = run.post(FINANCE, f"/records/{submitted['id']}/query", {"text": "Clarify the total."})
    answered = run.post(CREATOR, f"/records/{submitted['id']}/query-response", {"text": "Includes tax."})
    validated = run.validated(submitted["id"])
    assert [submitted["status"], queried["status"], answered["status"], validated["status"]] == [
        "submitted", "query_raised", "query_responded", "finance_validated"]


def test_iaa_wf_05__bw_iaa_05_escalated_expense_approval_path(stub_iam, configured):
    """IAA-WF-05 / BW-IAA-05 escalated expense/voucher approval path."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    run.overdue()
    escalated = run.get(CREATOR, f"/records/{submitted['id']}")
    approved = run.decide(submitted["id"], who=DEAN)
    assert escalated["status"] == "escalated"
    assert approved["status"] in {"approval_pending", "approved"}


def test_iaa_wf_06__bw_iaa_06_escalated_expense_rejection_path(stub_iam, configured):
    """IAA-WF-06 / BW-IAA-06 escalated expense/voucher rejection path."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    run.overdue()
    rejected = run.decide(submitted["id"], who=DEAN, decision="reject", remarks="Rejected.")
    assert rejected["status"] == "rejected"


def test_iaa_wf_07__bw_iaa_07_standard_ta_processing_path(stub_iam, configured):
    """IAA-WF-07 / BW-IAA-07 standard TA processing path."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="10000")
    verified = run.validated(claim["id"])
    recorded = run.post(FINANCE, f"/records/{claim['id']}/processing", {"reference": "WF-07"})
    refused = run.request(CREATOR, "patch", f"/records/{claim['id']}", {"purpose": "Changed"})
    after = run.get(CREATOR, f"/records/{claim['id']}")
    assert [claim["status"], verified["status"], recorded["status"]] == [
        "submitted", "verified", "recorded"]
    assert refused.status_code == 409
    assert after["status"] == "recorded" and after["purpose"] == claim["purpose"]


def test_iaa_wf_08__bw_iaa_08_high_value_ta_approval_path(stub_iam, configured):
    """IAA-WF-08 / BW-IAA-08 high-value TA approval path."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="30000")
    routed = run.validated(claim["id"])
    approved = run.decide(claim["id"], who=HOD)
    recorded = run.post(FINANCE, f"/records/{claim['id']}/processing", {"reference": "WF-08"})
    assert [routed["status"], approved["status"], recorded["status"]] == [
        "approval_pending", "approved", "recorded"]


def test_iaa_wf_09__bw_iaa_09_high_value_ta_additional_approval_traversal(stub_iam, configured):
    """IAA-WF-09 / BW-IAA-09 high-value TA additional approval traversal."""
    run = IaaHttp(stub_iam)
    published_policy(run, routes=ta_route(roles.HOD, roles.DEAN))
    claim = run.submitted_ta(amount="30000")
    routed = run.validated(claim["id"])
    first = run.decide(claim["id"], who=HOD)
    second = run.decide(claim["id"], who=DEAN)
    recorded = run.post(FINANCE, f"/records/{claim['id']}/processing", {"reference": "WF-09"})
    assert [routed["status"], first["status"], second["status"], recorded["status"]] == [
        "approval_pending", "approval_pending", "approved", "recorded"]


def test_iaa_wf_10__bw_iaa_10_high_value_ta_rejection_path(stub_iam, configured):
    """IAA-WF-10 / BW-IAA-10 high-value TA rejection path."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="30000")
    run.validated(claim["id"])
    rejected = run.decide(claim["id"], who=HOD, decision="reject", remarks="Outside policy.")
    assert rejected["status"] == "rejected"


def test_iaa_wf_11__bw_iaa_11_ta_clarification_traversal(stub_iam, configured):
    """IAA-WF-11 / BW-IAA-11 TA clarification traversal."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="10000")
    queried = run.post(FINANCE, f"/records/{claim['id']}/query", {"text": "Provide boarding pass."})
    answered = run.post(CREATOR, f"/records/{claim['id']}/query-response", {"text": "Attached."})
    verified = run.validated(claim["id"])
    assert [claim["status"], queried["status"], answered["status"], verified["status"]] == [
        "submitted", "query_raised", "query_responded", "verified"]


def test_iaa_wf_12__bw_iaa_16_escalated_high_value_ta_approval_path(stub_iam, configured):
    """IAA-WF-12 / BW-IAA-16 escalated high-value TA approval path."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="30000")
    run.validated(claim["id"])
    run.overdue()
    escalated = run.get(CREATOR, f"/records/{claim['id']}")
    approved = run.decide(claim["id"], who=DEAN)
    recorded = run.post(FINANCE, f"/records/{claim['id']}/processing", {"reference": "WF-12"})
    assert escalated["status"] == "escalated"
    assert approved["status"] in {"approval_pending", "approved"}
    assert recorded["status"] == "recorded"


def test_iaa_wf_13__bw_iaa_17_escalated_high_value_ta_rejection_path(stub_iam, configured):
    """IAA-WF-13 / BW-IAA-17 escalated high-value TA rejection path."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="30000")
    run.validated(claim["id"])
    run.overdue()
    rejected = run.decide(claim["id"], who=DEAN, decision="reject", remarks="Rejected.")
    assert rejected["status"] == "rejected"


def test_iaa_wf_14__bw_iaa_12_manual_anomaly_direct_resolution_path(stub_iam, configured):
    """IAA-WF-14 / BW-IAA-12 manual anomaly direct resolution path."""
    run = IaaHttp(stub_iam)
    anomaly = manual_anomaly(run)
    resolved = run.post(FINANCE, f"/anomalies/{anomaly['id']}/resolve", {"text": "Reconciled."})
    assert anomaly["status"] == "open" and resolved["status"] == "resolved"


def test_iaa_wf_15__bw_iaa_13_manual_anomaly_escalation_traversal(stub_iam, configured):
    """IAA-WF-15 / BW-IAA-13 manual anomaly escalation traversal."""
    run = IaaHttp(stub_iam)
    anomaly = manual_anomaly(run)
    escalated = run.post(FINANCE, f"/anomalies/{anomaly['id']}/escalate", {"text": "Dean review."})
    resolved = run.post(DEAN, f"/anomalies/{anomaly['id']}/resolve", {"text": "Corrected."})
    assert anomaly["status"] == "open"
    assert escalated["status"] == "escalated" and resolved["status"] == "resolved"


def test_iaa_wf_16__bw_iaa_18_automatic_anomaly_direct_resolution_path(stub_iam, configured):
    """IAA-WF-16 / BW-IAA-18 automatic anomaly direct resolution path."""
    run = IaaHttp(stub_iam)
    anomaly = automatic_anomaly(run)
    resolved = run.post(FINANCE, f"/anomalies/{anomaly['id']}/resolve", {"text": "Corrected."})
    assert anomaly["status"] == "open" and anomaly["source"] == "automatic"
    assert resolved["status"] == "resolved"


def test_iaa_wf_17__bw_iaa_19_automatic_anomaly_escalation_traversal(stub_iam, configured):
    """IAA-WF-17 / BW-IAA-19 automatic anomaly escalation traversal."""
    run = IaaHttp(stub_iam)
    anomaly = automatic_anomaly(run)
    escalated = run.post(FINANCE, f"/anomalies/{anomaly['id']}/escalate", {"text": "Dean review."})
    resolved = run.post(DEAN, f"/anomalies/{anomaly['id']}/resolve", {"text": "Corrected."})
    assert anomaly["status"] == "open" and anomaly["source"] == "automatic"
    assert escalated["status"] == "escalated" and resolved["status"] == "resolved"


def test_iaa_wf_18__bw_iaa_14_audit_observation_straight_closure_path(stub_iam, configured):
    """IAA-WF-18 / BW-IAA-14 audit observation straight closure path."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    item = observation(run, submitted)
    responded = run.post(CREATOR, f"/observations/{item['id']}/respond", {
        "corrective_action": "Evidence has been attached.",
        "evidence_link": "https://files.example/approval.pdf",
    })
    closed = run.post(AUDITOR, f"/observations/{item['id']}/review", {"verdict": "satisfactory"})
    assert item["status"] == "open"
    assert responded["status"] == "responded" and closed["status"] == "closed"


def test_iaa_wf_19__bw_iaa_15_audit_observation_revision_traversal(stub_iam, configured):
    """IAA-WF-19 / BW-IAA-15 audit observation revision traversal."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    item = observation(run, submitted)
    first = run.post(CREATOR, f"/observations/{item['id']}/respond", {
        "corrective_action": "Initial response is incomplete.",
    })
    returned = run.post(AUDITOR, f"/observations/{item['id']}/review", {
        "verdict": "unsatisfactory", "remarks": "Provide signed evidence.",
    })
    revised = run.post(CREATOR, f"/observations/{item['id']}/respond", {
        "corrective_action": "Signed evidence has been provided.",
        "evidence_link": "https://files.example/signed-evidence.pdf",
    })
    closed = run.post(AUDITOR, f"/observations/{item['id']}/review", {"verdict": "satisfactory"})
    assert item["status"] == "open"
    assert [first["status"], returned["status"], revised["status"], closed["status"]] == [
        "responded", "open", "responded", "closed"]
