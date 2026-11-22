"""FR specification cases for travel allowance and audit observations."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.iaa.domain import roles
from modules.iaa.tests.spec.fr.test_support import (
    AUDITOR,
    CREATOR,
    FINANCE,
    HOD,
    IaaHttp,
)

pytestmark = pytest.mark.django_db


def test_iaa_t038__afr_iaa_038_submit_complete_ta_claim(stub_iam, configured):
    """IAA-T038 / AFR-IAA-038: submit a TA claim with trip details and evidence."""
    run = IaaHttp(stub_iam)

    claim = run.submitted_ta(amount="10000", purpose="Research conference")
    detail = run.get(CREATOR, f"/records/{claim['id']}")

    assert claim["status"] == "submitted"
    assert claim["trip_start"]
    assert claim["trip_end"]
    assert claim["purpose"] == "Research conference"
    assert claim["amount"] == "10000.00"
    assert detail["documents"][0]["title"] == "Invoice"


def test_iaa_t039__afr_iaa_039_block_incomplete_ta_submission(stub_iam, configured):
    """IAA-T039 / AFR-IAA-039: missing TA evidence blocks submission without creating a claim."""
    run = IaaHttp(stub_iam)
    before = run.get(CREATOR, "/records?kind=ta")
    today = timezone.localdate()

    refused = run.request(CREATOR, "post", "/records", {
        "kind": "ta", "department": "CSE", "amount": "10000", "purpose": "Conference",
        "trip_start": str(today - timedelta(days=5)),
        "trip_end": str(today - timedelta(days=3)), "documents": [],
    })
    after = run.get(CREATOR, "/records?kind=ta")

    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "submission_incomplete"
    assert len(after["results"]) == len(before["results"])


def test_iaa_t040__afr_iaa_040_finance_verifies_ta_policy_compliance(stub_iam, configured):
    """IAA-T040 / AFR-IAA-040: Finance Staff can verify a policy-compliant TA claim."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="10000")

    verified = run.validated(claim["id"])

    assert verified["status"] == "verified"


def test_iaa_t041__afr_iaa_041_check_ta_claim_against_department_budget(stub_iam, configured):
    """IAA-T041 / AFR-IAA-041: Finance checks a TA claim against its available budget."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="10000", department="CSE")

    verified = run.validated(claim["id"])
    anomalies = run.get(FINANCE, "/anomalies")

    assert verified["status"] == "verified"
    assert not anomalies["results"]


def test_iaa_t042__afr_iaa_042_ta_clarification_and_response_cycle(stub_iam, configured):
    """IAA-T042 / AFR-IAA-042: Finance's TA query and claimant response are recorded."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="10000")
    asked = run.post(FINANCE, f"/records/{claim['id']}/query",
                     {"text": "Please provide the boarding pass."})

    answered = run.post(CREATOR, f"/records/{claim['id']}/query-response",
                        {"text": "The boarding pass is attached."})

    assert asked["status"] == "query_raised"
    assert answered["status"] == "query_responded"
    assert answered["queries"][0]["question"] == "Please provide the boarding pass."
    assert answered["queries"][0]["response"] == "The boarding pass is attached."


def test_iaa_t043__afr_iaa_043_route_high_value_ta_through_approval(stub_iam, configured):
    """IAA-T043 / AFR-IAA-043: a high-value TA claim enters its configured approval route."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="30000")

    routed = run.validated(claim["id"])

    assert routed["status"] == "approval_pending"
    assert routed["route_levels"] == [roles.HOD]
    assert routed["steps"][0]["designation"] == roles.HOD


def test_iaa_t044__afr_iaa_044_high_value_ta_decision_and_remarks_are_recorded(
        stub_iam, configured):
    """IAA-T044 / AFR-IAA-044: assigned authority records its high-value TA approval and remarks."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="30000")
    run.validated(claim["id"])

    approved = run.decide(claim["id"], who=HOD, remarks="Trip meets the travel policy")

    assert approved["status"] == "approved"
    assert approved["steps"][0]["decided_role"] == roles.HOD
    assert approved["steps"][0]["remarks"] == "Trip meets the travel policy"


def test_iaa_t045__afr_iaa_045_claimant_cannot_approve_own_ta_claim(stub_iam, configured):
    """IAA-T045 / AFR-IAA-045: a claimant's own TA approval is refused."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(user=(301, "faculty"), amount="30000")
    run.validated(claim["id"])
    before = run.get((301, "faculty"), f"/records/{claim['id']}")

    refused = run.request((301, roles.HOD), "post", f"/records/{claim['id']}/decision",
                          {"decision": "approve", "remarks": "Self approval"})
    after = run.get((301, "faculty"), f"/records/{claim['id']}")

    assert refused.status_code == 403
    assert after["status"] == before["status"] == "approval_pending"
    assert not any(step["decided_role"] == roles.HOD for step in after["steps"])


def test_iaa_t046__afr_iaa_046_finance_processes_and_records_ta_internally(stub_iam, configured):
    """IAA-T046 / AFR-IAA-046: Finance records internal processing of a verified TA claim."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="10000")
    run.validated(claim["id"])

    recorded = run.post(FINANCE, f"/records/{claim['id']}/processing", {
        "reference": "TA-FR-046", "note": "Internal claim record completed",
    })

    assert recorded["status"] == "recorded"
    assert recorded["processing_reference"] == "TA-FR-046"


def test_iaa_t047__afr_iaa_047_recorded_ta_claim_is_read_only_and_terminal(
        stub_iam, configured):
    """IAA-T047 / AFR-IAA-047: a recorded TA claim cannot be edited and stays terminal."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="10000")
    run.validated(claim["id"])
    run.post(FINANCE, f"/records/{claim['id']}/processing", {"reference": "TA-FR-047"})
    before = run.get(CREATOR, f"/records/{claim['id']}")

    refused = run.request(CREATOR, "patch", f"/records/{claim['id']}", {"purpose": "Changed"})
    after = run.get(CREATOR, f"/records/{claim['id']}")

    assert refused.status_code == 409
    assert after["status"] == before["status"] == "recorded"
    assert after["purpose"] == before["purpose"]


def test_iaa_t048__afr_iaa_048_auditor_reviews_in_process_and_completed_records(
        stub_iam, configured):
    """IAA-T048 / AFR-IAA-048: Auditor can review in-process and completed in-scope records."""
    run = IaaHttp(stub_iam)
    in_process = run.submitted_expense()
    complete = run.submitted_expense()
    run.validated(complete["id"])
    run.decide(complete["id"], who=HOD)
    run.post(FINANCE, f"/records/{complete['id']}/processing", {"reference": "AUDIT-048"})

    visible = run.get(AUDITOR, "/records")
    visible_by_id = {item["id"]: item["status"] for item in visible["results"]}

    assert visible_by_id[in_process["id"]] == "submitted"
    assert visible_by_id[complete["id"]] == "recorded"


def test_iaa_t049__afr_iaa_049_raise_observation_linked_to_record(stub_iam, configured):
    """IAA-T049 / AFR-IAA-049: an Auditor can create a traceable record-linked observation."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    observation = run.post(AUDITOR, "/observations", {
        "title": "Missing approval note", "detail": "The record needs supporting approval evidence.",
        "record_id": submitted["id"],
    }, expected_status=201)

    assert observation["record"] == submitted["id"]
    assert observation["respondent_user_id"] == 101
    assert observation["status"] == "open"


def test_iaa_t050__afr_iaa_050_new_observation_enters_open_state(stub_iam, configured):
    """IAA-T050 / AFR-IAA-050: a newly raised observation enters Open state."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    observation = run.post(AUDITOR, "/observations", {
        "title": "Review finding", "detail": "A supporting record is missing.",
        "record_id": submitted["id"],
    }, expected_status=201)

    assert observation["status"] == "open"


def test_iaa_t051__afr_iaa_051_concerned_user_submits_corrective_action(stub_iam, configured):
    """IAA-T051 / AFR-IAA-051: the concerned user can submit corrective-action information."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    observation = run.post(AUDITOR, "/observations", {
        "title": "Corrective action needed", "detail": "Attach the missing invoice.",
        "record_id": submitted["id"],
    }, expected_status=201)

    response = run.post(CREATOR, f"/observations/{observation['id']}/respond", {
        "corrective_action": "The invoice has been added to the file.",
    })

    assert response["responses"][0]["corrective_action"] == (
        "The invoice has been added to the file."
    )


def test_iaa_t052__afr_iaa_052_attach_evidence_to_observation_response(stub_iam, configured):
    """IAA-T052 / AFR-IAA-052: supporting evidence is associated with the response."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    observation = run.post(AUDITOR, "/observations", {
        "title": "Evidence needed", "detail": "Provide the corrected statement.",
        "record_id": submitted["id"],
    }, expected_status=201)

    response = run.post(CREATOR, f"/observations/{observation['id']}/respond", {
        "corrective_action": "Corrected statement attached.",
        "evidence_link": "https://files.example/corrected-statement.pdf",
    })

    assert response["responses"][0]["evidence_link"] == (
        "https://files.example/corrected-statement.pdf"
    )


def test_iaa_t053__afr_iaa_053_response_moves_observation_to_responded(stub_iam, configured):
    """IAA-T053 / AFR-IAA-053: submitting a response moves the observation to Responded."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    observation = run.post(AUDITOR, "/observations", {
        "title": "Response requested", "detail": "Explain the discrepancy.",
        "record_id": submitted["id"],
    }, expected_status=201)

    responded = run.post(CREATOR, f"/observations/{observation['id']}/respond", {
        "corrective_action": "The discrepancy has been corrected.",
    })

    assert responded["status"] == "responded"


def test_iaa_t054__afr_iaa_054_auditor_verifies_response_and_evidence(stub_iam, configured):
    """IAA-T054 / AFR-IAA-054: an Auditor verifies submitted corrective action and evidence."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    observation = run.post(AUDITOR, "/observations", {
        "title": "Evidence review", "detail": "Confirm the invoice correction.",
        "record_id": submitted["id"],
    }, expected_status=201)
    run.post(CREATOR, f"/observations/{observation['id']}/respond", {
        "corrective_action": "Invoice corrected.",
        "evidence_link": "https://files.example/invoice-corrected.pdf",
    })

    verified = run.post(AUDITOR, f"/observations/{observation['id']}/review", {
        "verdict": "satisfactory",
    })

    assert verified["status"] == "closed"
    assert verified["responses"][0]["verdict"] == "satisfactory"
    assert verified["responses"][0]["evidence_link"] == (
        "https://files.example/invoice-corrected.pdf"
    )


def test_iaa_t055__afr_iaa_055_response_cannot_be_closed_before_auditor_verification(
        stub_iam, configured):
    """IAA-T055 / AFR-IAA-055: a respondent cannot close an unverified response."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    observation = run.post(AUDITOR, "/observations", {
        "title": "Unverified response", "detail": "Wait for Auditor review.",
        "record_id": submitted["id"],
    }, expected_status=201)
    run.post(CREATOR, f"/observations/{observation['id']}/respond", {
        "corrective_action": "Response submitted for review.",
    })
    before = run.get(CREATOR, "/observations")

    refused = run.request(CREATOR, "post", f"/observations/{observation['id']}/review", {
        "verdict": "satisfactory",
    })
    after = run.get(CREATOR, "/observations")

    assert refused.status_code == 403
    before_item = next(item for item in before["results"] if item["id"] == observation["id"])
    after_item = next(item for item in after["results"] if item["id"] == observation["id"])
    assert after_item["status"] == before_item["status"] == "responded"


def test_iaa_t056__afr_iaa_056_unsatisfactory_response_returns_to_open(stub_iam, configured):
    """IAA-T056 / AFR-IAA-056: an unsatisfactory response returns to Open without Reopened."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    observation = run.post(AUDITOR, "/observations", {
        "title": "Evidence not sufficient", "detail": "Provide a signed invoice.",
        "record_id": submitted["id"],
    }, expected_status=201)
    run.post(CREATOR, f"/observations/{observation['id']}/respond", {
        "corrective_action": "An unsigned invoice was attached.",
    })

    returned = run.post(AUDITOR, f"/observations/{observation['id']}/review", {
        "verdict": "unsatisfactory", "remarks": "Please provide a signed invoice.",
    })

    assert returned["status"] == "open"
    assert returned["cycle"] == 2
    assert returned["status"] != "reopened"


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE exposes no observation deletion route, so the attempted deletion "
    "and resulting history retention cannot be exercised through an available interface."
))
def test_iaa_t057__afr_iaa_057_preserve_observation_history_when_deletion_is_attempted():
    """IAA-T057 / AFR-IAA-057: attempted deletion must not destroy observation history."""
