"""FR specification cases for approval routing and anomaly management."""
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


def test_iaa_t021__afr_iaa_021_route_expense_by_amount(stub_iam, configured):
    """IAA-T021 / AFR-IAA-021: amount criteria select the configured approval route."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(amount="60000")

    routed = run.validated(submitted["id"])

    assert routed["route_levels"] == [roles.HOD, roles.DEAN]
    assert [step["designation"] for step in routed["steps"]] == [roles.HOD]


def test_iaa_t022__afr_iaa_022_route_expense_by_request_type(stub_iam, configured):
    """IAA-T022 / AFR-IAA-022: request type criteria select their configured routes."""
    run = IaaHttp(stub_iam)
    routes = [
        {"kind": "expense", "request_type": "voucher", "min_amount": "0",
         "max_amount": "50000", "levels": [roles.HOD],
         "escalation_designation": roles.DEAN},
        {"kind": "expense", "request_type": "reimbursement", "min_amount": "0",
         "max_amount": "50000", "levels": [roles.DEAN],
         "escalation_designation": roles.DIRECTOR},
        {"kind": "ta", "min_amount": "0", "levels": [roles.HOD],
         "escalation_designation": roles.DEAN},
    ]
    published_policy(run, routes=routes)
    voucher = run.submitted_expense(request_type="voucher")
    reimbursement = run.submitted_expense(request_type="reimbursement")

    voucher_route = run.validated(voucher["id"])
    reimbursement_route = run.validated(reimbursement["id"])

    assert voucher_route["route_levels"] == [roles.HOD]
    assert reimbursement_route["route_levels"] == [roles.DEAN]


def test_iaa_t023__afr_iaa_023_route_expense_by_department(stub_iam, configured):
    """IAA-T023 / AFR-IAA-023: department criteria select their configured routes."""
    run = IaaHttp(stub_iam)
    routes = [
        {"kind": "expense", "department": "CSE", "min_amount": "0",
         "levels": [roles.HOD], "escalation_designation": roles.DEAN},
        {"kind": "expense", "department": "ECE", "min_amount": "0",
         "levels": [roles.DEAN], "escalation_designation": roles.DIRECTOR},
        {"kind": "ta", "min_amount": "0", "levels": [roles.HOD],
         "escalation_designation": roles.DEAN},
    ]
    published_policy(run, routes=routes)
    cse = run.submitted_expense(department="CSE")
    ece = run.submitted_expense(department="ECE")

    cse_route = run.validated(cse["id"])
    ece_route = run.validated(ece["id"])

    assert cse_route["route_levels"] == [roles.HOD]
    assert ece_route["route_levels"] == [roles.DEAN]


def test_iaa_t024__afr_iaa_024_advance_through_each_approval_level(stub_iam, configured):
    """IAA-T024 / AFR-IAA-024: a request follows every required approval level in order."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(amount="60000")
    run.validated(submitted["id"])

    first = run.decide(submitted["id"], who=HOD, remarks="First level approved")
    second = run.decide(submitted["id"], who=DEAN, remarks="Final level approved")

    assert first["status"] == "approval_pending"
    assert first["steps"][-1]["designation"] == roles.DEAN
    assert second["status"] == "approved"
    assert [step["decided_role"] for step in second["steps"]] == [roles.HOD, roles.DEAN]


def test_iaa_t025__afr_iaa_025_represent_distinct_approver_roles(stub_iam, configured):
    """IAA-T025 / AFR-IAA-025: HoD, Dean, and Director remain distinct route roles."""
    run = IaaHttp(stub_iam)
    routes = [
        {"kind": "expense", "min_amount": "0", "levels": [
            roles.HOD, roles.DEAN, roles.DIRECTOR,
        ], "escalation_designation": roles.DIRECTOR},
        {"kind": "ta", "min_amount": "0", "levels": [roles.HOD],
         "escalation_designation": roles.DEAN},
    ]
    published_policy(run, routes=routes)
    submitted = run.submitted_expense()

    routed = run.validated(submitted["id"])

    assert routed["route_levels"] == [roles.HOD, roles.DEAN, roles.DIRECTOR]
    assert len(set(routed["route_levels"])) == 3


def test_iaa_t026__afr_iaa_026_assigned_authority_approves_with_remarks(stub_iam, configured):
    """IAA-T026 / AFR-IAA-026: assigned authority approval and remarks are recorded."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])

    approved = run.decide(submitted["id"], who=HOD, remarks="Within the approved plan")

    assert approved["status"] == "approved"
    assert approved["steps"][0]["decided_role"] == roles.HOD
    assert approved["steps"][0]["remarks"] == "Within the approved plan"


def test_iaa_t027__afr_iaa_027_assigned_authority_rejects_with_remarks(stub_iam, configured):
    """IAA-T027 / AFR-IAA-027: assigned authority rejection and remarks are recorded."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])

    rejected = run.decide(submitted["id"], who=HOD, decision="reject",
                          remarks="The expense is outside the approved plan")

    assert rejected["status"] == "rejected"
    assert rejected["steps"][0]["decided_role"] == roles.HOD
    assert rejected["steps"][0]["remarks"] == "The expense is outside the approved plan"


def test_iaa_t028__afr_iaa_028_creator_cannot_approve_their_own_request(stub_iam, configured):
    """IAA-T028 / AFR-IAA-028: a creator's own approval decision is refused."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(user=(301, "faculty"))
    run.validated(submitted["id"])
    before = run.get((301, "faculty"), f"/records/{submitted['id']}")

    refused = run.request((301, roles.HOD), "post", f"/records/{submitted['id']}/decision",
                          {"decision": "approve", "remarks": "Self approval"})
    after = run.get((301, "faculty"), f"/records/{submitted['id']}")

    assert refused.status_code == 403
    assert after["status"] == before["status"] == "finance_validated"
    assert not any(step["decided_role"] == roles.HOD for step in after["steps"])


def test_iaa_t029__afr_iaa_029_reroute_from_ineligible_assigned_authority(stub_iam, configured):
    """IAA-T029 / AFR-IAA-029: an ineligible assignee is routed to the next eligible authority."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(user=(301, "faculty"))
    run.validated(submitted["id"])

    run.decide(submitted["id"], who=HOD, expected_status=403)
    rerouted = run.get(DEAN, f"/records/{submitted['id']}")

    assert rerouted["status"] == "finance_validated"
    assert rerouted["steps"][-1]["designation"] == roles.DEAN
    assert rerouted["steps"][-1]["status"] == "pending"


def test_iaa_t030__afr_iaa_030_escalate_approval_after_configured_timeout(stub_iam, configured):
    """IAA-T030 / AFR-IAA-030: an overdue pending approval is automatically escalated."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])

    report = run.overdue()
    escalated = run.get(CREATOR, f"/records/{submitted['id']}")

    assert report.escalated == 1
    assert escalated["status"] == "escalated"
    assert escalated["steps"][-1]["designation"] == roles.DEAN
    assert escalated["steps"][-1]["status"] == "pending"


def test_iaa_t031__afr_iaa_031_escalation_is_traceable_in_request_history(stub_iam, configured):
    """IAA-T031 / AFR-IAA-031: an escalated approval appears in the request history."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    run.overdue()

    escalation = next(item for item in run.history(submitted["id"])
                      if item["action"] == "escalate")

    assert escalation["to_status"] == "escalated"
    assert escalation["actor_role"] == "system"
    assert escalation["created_at"]


def test_iaa_t032__afr_iaa_032_receiving_authority_resolves_escalated_approval(
        stub_iam, configured):
    """IAA-T032 / AFR-IAA-032: an authority receiving escalation can approve it with remarks."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    run.overdue()

    approved = run.decide(submitted["id"], who=DEAN, remarks="Resolved after escalation")

    assert approved["status"] == "approved"
    assert approved["steps"][-1]["decided_role"] == roles.DEAN
    assert approved["steps"][-1]["remarks"] == "Resolved after escalation"


def test_iaa_t033__afr_iaa_033_budget_shortfall_routes_anomaly_without_auto_rejection(
        stub_iam, configured):
    """IAA-T033 / AFR-IAA-033: budget insufficiency raises review and does not auto-reject."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(department="ECE", amount="10000")

    validated = run.validated(submitted["id"])
    anomalies = run.get(FINANCE, "/anomalies")
    budget_anomaly = next(item for item in anomalies["results"]
                          if item["record"] == submitted["id"])

    assert validated["status"] == "finance_validated"
    assert budget_anomaly["status"] == "open"
    assert budget_anomaly["source"] == "automatic"
    assert budget_anomaly["assigned_role"] == roles.FINANCE


def test_iaa_t034__afr_iaa_034_finance_manually_flags_material_anomaly(stub_iam, configured):
    """IAA-T034 / AFR-IAA-034: Finance Staff can manually flag a material anomaly."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    flagged = run.post(FINANCE, "/anomalies", {
        "category": "policy", "description": "The invoice conflicts with policy.",
        "record_id": submitted["id"],
    }, expected_status=201)

    assert flagged["status"] == "open"
    assert flagged["source"] == "manual"
    assert flagged["record"] == submitted["id"]


def test_iaa_t035__afr_iaa_035_auditor_manually_flags_material_anomaly(stub_iam, configured):
    """IAA-T035 / AFR-IAA-035: an Auditor can manually flag a material anomaly."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    flagged = run.post(AUDITOR, "/anomalies", {
        "category": "financial", "description": "Ledger entry needs review.",
        "record_id": submitted["id"],
    }, expected_status=201)

    assert flagged["status"] == "open"
    assert flagged["source"] == "manual"
    assert flagged["record"] == submitted["id"]


def test_iaa_t036__afr_iaa_036_configured_condition_flags_anomaly_automatically(
        stub_iam, configured):
    """IAA-T036 / AFR-IAA-036: an automatic anomaly is created for a configured condition."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense(department="ECE", amount="10000")

    run.validated(submitted["id"])
    anomalies = run.get(FINANCE, "/anomalies?status=open")

    automatic = [item for item in anomalies["results"]
                 if item["source"] == "automatic" and item["record"] == submitted["id"]]
    assert len(automatic) == 1
    assert automatic[0]["category"] == "budget"


def test_iaa_t037__afr_iaa_037_track_anomaly_to_designated_resolved_outcome(
        stub_iam, configured):
    """IAA-T037 / AFR-IAA-037: a designated resolver moves an Open anomaly to Resolved."""
    run = IaaHttp(stub_iam)
    flagged = run.post(FINANCE, "/anomalies", {
        "category": "budget", "description": "Allocation needs reconciliation.",
    }, expected_status=201)

    resolved = run.post(FINANCE, f"/anomalies/{flagged['id']}/resolve",
                        {"text": "The budget allocation was reconciled."})

    assert flagged["status"] == "open"
    assert resolved["status"] == "resolved"
    assert resolved["resolved_role"] == roles.FINANCE
