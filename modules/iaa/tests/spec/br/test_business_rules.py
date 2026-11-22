"""Backend tests for the frozen IAA BR design cases."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.iaa.domain import roles
from modules.iaa.registry import ROLE_GRANTS
from modules.iaa.tests.spec.fr.test_support import (
    ADMIN,
    AUDITOR,
    CREATOR,
    DEAN,
    FINANCE,
    HOD,
    IaaHttp,
    client_for_session,
    published_policy,
)

pytestmark = pytest.mark.django_db


def test_iaa_br_001_01_self_approval_is_refused_and_rerouted(stub_iam, configured):
    """IAA-BR-001-01; source_id: IAA-BR-001 creator/claimant self-approval prohibited."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense(user=(301, "faculty"))
    run.validated(item["id"])
    before = run.get((301, "faculty"), f"/records/{item['id']}")
    refused = run.request((301, roles.HOD), "post", f"/records/{item['id']}/decision",
                          {"decision": "approve", "remarks": "Self approval"})
    after = run.get(DEAN, f"/records/{item['id']}")
    assert refused.status_code >= 400
    assert after["status"] == before["status"] == "finance_validated"
    assert after["steps"][-1]["designation"] == roles.DEAN
    assert after["steps"][-1]["status"] == "pending"


def test_iaa_br_001_02_eligible_authority_decision_is_recorded(stub_iam, configured):
    """IAA-BR-001-02; source_id: IAA-BR-001 eligible non-creator/claimant approval."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    run.validated(item["id"])
    result = run.decide(item["id"], who=HOD, remarks="Approved after review")
    step = result["steps"][0]
    assert step["decided_role"] == roles.HOD
    assert step["remarks"] == "Approved after review"
    assert step["decided_at"]
    decision = next(row for row in run.history(item["id"]) if row["action"] == "approve")
    assert decision["actor_user_id"] == 301


def test_iaa_br_002_01_finance_validation_applies_configured_route(stub_iam, configured):
    """IAA-BR-002-01; source_id: IAA-BR-002 configured approval route."""
    run = IaaHttp(stub_iam)
    published_policy(run, routes=[
        {"kind": "expense", "department": "CSE", "request_type": "voucher",
         "min_amount": "0", "max_amount": "20000", "levels": [roles.DEAN],
         "escalation_designation": roles.DIRECTOR},
        {"kind": "ta", "min_amount": "0", "levels": [roles.HOD],
         "escalation_designation": roles.DEAN},
    ])
    item = run.submitted_expense(amount="12000")
    routed = run.validated(item["id"])
    assert routed["route_levels"] == [roles.DEAN]
    assert routed["steps"][0]["designation"] == roles.DEAN
    assert routed["steps"][0]["status"] == "pending"


def test_iaa_br_003_01_active_role_is_used_and_logged(stub_iam, configured):
    """IAA-BR-003-01; source_id: IAA-BR-003 multiple-role user selects active role."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    run.validated(item["id"])
    client = client_for_session(stub_iam, user_id=301, active_role=roles.HOD,
                                actor_roles=(roles.HOD, roles.DEAN),
                                permissions=ROLE_GRANTS[roles.HOD] + ROLE_GRANTS[roles.DEAN])
    response = client.post(f"/api/v1/iaa/records/{item['id']}/decision",
                           {"decision": "approve", "remarks": "Active HoD role"}, format="json")
    assert response.status_code == 200, response.content
    assert response.json()["steps"][0]["decided_role"] == roles.HOD
    assert run.history(item["id"])[-1]["actor_role"] == roles.HOD


def test_iaa_br_004_01_system_admin_cannot_access_operational_data(stub_iam, configured):
    """IAA-BR-004-01; source_id: IAA-BR-004 operational access denied."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    run.validated(item["id"])
    before = run.get(FINANCE, f"/records/{item['id']}")
    list_refusal = run.request(ADMIN, "get", "/records")
    detail_refusal = run.request(ADMIN, "get", f"/records/{item['id']}")
    decision_refusal = run.request(ADMIN, "post", f"/records/{item['id']}/decision",
                                   {"decision": "approve", "remarks": "No"})
    after = run.get(FINANCE, f"/records/{item['id']}")
    assert all(response.status_code >= 400 for response in
               (list_refusal, detail_refusal, decision_refusal))
    assert after["status"] == before["status"]
    assert after["steps"] == before["steps"]


@pytest.mark.skip(reason="NOT_AUTOMATED: configuration updates have no audit-log interface to verify their logging and operational privilege boundary.")
def test_iaa_br_004_02_system_admin_can_change_configuration():
    """IAA-BR-004-02; source_id: IAA-BR-004 configuration metadata exception."""


def test_iaa_br_005_01_decision_requires_remarks_then_records(stub_iam, configured):
    """IAA-BR-005-01; source_id: IAA-BR-005 decision remarks required."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    run.validated(item["id"])
    before = run.get(CREATOR, f"/records/{item['id']}")
    refused = run.request(HOD, "post", f"/records/{item['id']}/decision",
                          {"decision": "approve", "remarks": ""})
    after_refusal = run.get(CREATOR, f"/records/{item['id']}")
    assert refused.status_code >= 400
    assert after_refusal["status"] == before["status"]
    accepted = run.decide(item["id"], who=HOD, remarks="Reviewed and approved")
    step = accepted["steps"][0]
    assert step["remarks"] == "Reviewed and approved"
    assert step["decided_role"] == roles.HOD
    assert step["decided_at"]


def test_iaa_br_006_01_internal_processing_records_without_transfer(stub_iam, configured):
    """IAA-BR-006-01; source_id: IAA-BR-006 internal processing is non-monetary."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    run.validated(item["id"])
    run.decide(item["id"], who=HOD)
    recorded = run.post(FINANCE, f"/records/{item['id']}/processing", {"reference": "BR-006"})
    assert recorded["status"] == "recorded"
    assert recorded["processing_reference"] == "BR-006"


def test_iaa_br_101_01_incomplete_expense_submission_is_refused_unchanged(stub_iam, configured):
    """IAA-BR-101-01; source_id: IAA-BR-101 submission completeness validation."""
    run = IaaHttp(stub_iam)
    draft = run.expense_draft(amount=None, title="", description="")
    before = run.history(draft["id"])
    refused = run.request(CREATOR, "post", f"/records/{draft['id']}/submit")
    after = run.get(CREATOR, f"/records/{draft['id']}")
    assert refused.status_code == 422
    assert after["status"] == "draft"
    assert after["title"] == ""
    assert run.history(draft["id"]) == before


def test_iaa_br_101_02_complete_expense_submission_routes_to_finance(stub_iam, configured):
    """IAA-BR-101-02; source_id: IAA-BR-101 complete submission."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    queue = run.get(FINANCE, "/records?queue=finance_review")
    assert item["status"] == "submitted"
    assert item["id"] in {row["id"] for row in queue["results"]}


def test_iaa_br_102_01_sufficient_budget_allows_validation(stub_iam, configured):
    """IAA-BR-102-01; source_id: IAA-BR-102 budget available."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense(department="CSE", amount="10000")
    validated = run.validated(item["id"])
    assert validated["status"] == "finance_validated"
    assert not run.get(FINANCE, "/anomalies")["results"]


def test_iaa_br_102_02_insufficient_budget_flags_without_rejection(stub_iam, configured):
    """IAA-BR-102-02; source_id: IAA-BR-102 budget insufficient."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense(department="ECE", amount="10000")
    validated = run.validated(item["id"])
    anomaly = next(row for row in run.get(FINANCE, "/anomalies")["results"]
                   if row["record"] == item["id"])
    assert validated["status"] == "finance_validated"
    assert anomaly["status"] == "open"
    assert anomaly["source"] == "automatic"


def test_iaa_br_103_01_anomaly_can_be_tracked_to_resolution(stub_iam, configured):
    """IAA-BR-103-01; source_id: IAA-BR-103 material anomaly flagged and tracked."""
    run = IaaHttp(stub_iam)
    anomaly = run.post(FINANCE, "/anomalies", {"category": "policy", "description": "Review."}, expected_status=201)
    resolved = run.post(FINANCE, f"/anomalies/{anomaly['id']}/resolve", {"text": "Reviewed."})
    assert anomaly["status"] == "open"
    assert resolved["status"] == "resolved"
    assert resolved["resolved_role"] == roles.FINANCE


def test_iaa_br_104_01_creator_cannot_edit_submitted_item(stub_iam, configured):
    """IAA-BR-104-01; source_id: IAA-BR-104 post-submission record lock."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    before = run.get(CREATOR, f"/records/{item['id']}")
    refused = run.request(CREATOR, "patch", f"/records/{item['id']}", {"title": "Changed"})
    after = run.get(CREATOR, f"/records/{item['id']}")
    assert refused.status_code >= 400
    assert after["status"] == before["status"] == "submitted"
    assert after["title"] == before["title"]


def test_iaa_br_104_02_creator_can_respond_to_finance_query(stub_iam, configured):
    """IAA-BR-104-02; source_id: IAA-BR-104 structured Finance response exception."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    run.post(FINANCE, f"/records/{item['id']}/query", {"text": "Clarify the invoice."})
    response = run.post(CREATOR, f"/records/{item['id']}/query-response", {"text": "Invoice attached."})
    assert response["status"] == "query_responded"
    assert response["queries"][0]["response"] == "Invoice attached."


def test_iaa_br_201_01_complete_ta_verification_continues_by_policy(stub_iam, configured):
    """IAA-BR-201-01; source_id: IAA-BR-201 TA verification policy."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="10000")
    verified = run.validated(claim["id"])
    assert verified["status"] == "verified"


def test_iaa_br_201_02_ta_clarification_response_resumes_verification(stub_iam, configured):
    """IAA-BR-201-02; source_id: IAA-BR-201 TA clarification."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="10000")
    run.post(FINANCE, f"/records/{claim['id']}/query", {"text": "Provide boarding pass."})
    response = run.post(CREATOR, f"/records/{claim['id']}/query-response", {"text": "Attached."})
    assert response["status"] == "query_responded"
    assert run.validated(claim["id"])["status"] == "verified"


def test_iaa_br_202_01_high_value_ta_routes_to_authority(stub_iam, configured):
    """IAA-BR-202-01; source_id: IAA-BR-202 high-value TA approval required."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="30000")
    routed = run.validated(claim["id"])
    assert routed["status"] == "approval_pending"
    assert routed["route_levels"] == [roles.HOD]


def test_iaa_br_202_02_low_value_ta_proceeds_to_finance(stub_iam, configured):
    """IAA-BR-202-02; source_id: IAA-BR-202 high-value criteria not met."""
    run = IaaHttp(stub_iam)
    claim = run.submitted_ta(amount="10000")
    verified = run.validated(claim["id"])
    assert verified["status"] == "verified"
    processed = run.post(FINANCE, f"/records/{claim['id']}/processing", {"reference": "BR-202"})
    assert processed["status"] == "recorded"


def test_iaa_br_301_01_unsatisfactory_observation_repeats_open_cycle(stub_iam, configured):
    """IAA-BR-301-01; source_id: IAA-BR-301 observation lifecycle."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    obs = run.post(AUDITOR, "/observations", {"title": "Finding", "detail": "Evidence needed.", "record_id": item["id"]}, expected_status=201)
    run.post(CREATOR, f"/observations/{obs['id']}/respond", {"corrective_action": "Answered.", "evidence_link": "https://files.example/evidence.pdf"})
    opened = run.post(AUDITOR, f"/observations/{obs['id']}/review", {"verdict": "unsatisfactory", "remarks": "More evidence."})
    assert opened["status"] == "open"
    assert opened["cycle"] == 2
    assert opened["status"] != "reopened"
    assert len(opened["responses"]) == 1


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE exposes no observation deletion route, so deletion and retained history cannot be exercised through an available interface.")
def test_iaa_br_301_02_observation_history_is_not_deletable():
    """IAA-BR-301-02; source_id: IAA-BR-301 observation history cannot be deleted."""


def test_iaa_br_302_01_satisfactory_response_can_be_closed(stub_iam, configured):
    """IAA-BR-302-01; source_id: IAA-BR-302 satisfactory closure verification."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    obs = run.post(AUDITOR, "/observations", {"title": "Finding", "detail": "Fix it.", "record_id": item["id"]}, expected_status=201)
    run.post(CREATOR, f"/observations/{obs['id']}/respond", {"corrective_action": "Fixed.", "evidence_link": "https://files.example/fixed.pdf"})
    closed = run.post(AUDITOR, f"/observations/{obs['id']}/review", {"verdict": "satisfactory"})
    assert closed["status"] == "closed"
    assert closed["responses"][0]["verdict"] == "satisfactory"


def test_iaa_br_302_02_unsatisfactory_response_returns_to_open(stub_iam, configured):
    """IAA-BR-302-02; source_id: IAA-BR-302 unsatisfactory closure verification."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    obs = run.post(AUDITOR, "/observations", {"title": "Finding", "detail": "Fix it.", "record_id": item["id"]}, expected_status=201)
    run.post(CREATOR, f"/observations/{obs['id']}/respond", {"corrective_action": "Attempted."})
    returned = run.post(AUDITOR, f"/observations/{obs['id']}/review", {"verdict": "unsatisfactory"})
    assert returned["status"] == "open"
    assert returned["cycle"] == 2


def test_iaa_br_401_01_overdue_approval_escalates_to_next_authority(stub_iam, configured):
    """IAA-BR-401-01; source_id: IAA-BR-401 approval timeout exceeded."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    run.validated(item["id"])
    report = run.overdue()
    escalated = run.get(CREATOR, f"/records/{item['id']}")
    assert report.escalated == 1
    assert escalated["status"] == "escalated"
    assert escalated["steps"][-1]["designation"] == roles.DEAN
    assert any(n["kind"] == "escalated" and n["entity_id"] == item["id"]
               for n in run.get(CREATOR, "/notifications")["notifications"])


def test_iaa_br_401_02_unexpired_approval_is_not_escalated(stub_iam, configured):
    """IAA-BR-401-02; source_id: IAA-BR-401 approval timeout not exceeded."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    run.validated(item["id"])
    from modules.iaa.services import decisions
    report = decisions.escalate_overdue(at=timezone.now())
    assert report.escalated == 0
    assert run.status(item["id"]) == "finance_validated"


def test_iaa_br_401_03_finance_review_is_outside_approval_timeout(stub_iam, configured):
    """IAA-BR-401-03; source_id: IAA-BR-401 non-approval work is outside timeout rule."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    from modules.iaa.services import decisions
    report = decisions.escalate_overdue(at=timezone.now() + timedelta(days=30))
    assert report.escalated == 0
    assert run.status(item["id"]) == "submitted"


def test_iaa_br_501_01_authorized_user_can_access_scoped_record(stub_iam, configured):
    """IAA-BR-501-01; source_id: IAA-BR-501 permitted active-role scope."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    own = run.get(CREATOR, f"/records/{item['id']}")
    assert own["id"] == item["id"]


def test_iaa_br_501_02_user_cannot_access_out_of_scope_record(stub_iam, configured):
    """IAA-BR-501-02; source_id: IAA-BR-501 access outside active-role or record scope denied."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    from modules.iaa.tests.spec.fr.test_support import client_for_session
    client = client_for_session(stub_iam, user_id=102, active_role="faculty",
                                actor_roles=("faculty",), permissions=())
    refused = client.get(f"/api/v1/iaa/records/{item['id']}")
    assert refused.status_code == 404


def test_iaa_br_502_01_role_change_preserves_historical_action(stub_iam, configured):
    """IAA-BR-502-01; source_id: IAA-BR-502 historical role integrity."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    run.post(FINANCE, f"/records/{item['id']}/query", {"text": "Clarify total."})
    history = run.history(item["id"])
    action = next(row for row in history if row["action"] == "raise_query")
    assert action["actor_user_id"] == 201
    assert action["actor_role"] == roles.FINANCE


def test_iaa_br_503_01_operational_action_writes_audit_trail(stub_iam, configured):
    """IAA-BR-503-01; source_id: IAA-BR-503 state-changing operational action."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    submit = next(row for row in run.history(item["id"]) if row["action"] == "submit")
    assert submit["actor_user_id"] == 101
    assert submit["actor_role"] == "faculty"
    assert submit["created_at"]
    assert submit["action"] == "submit"
    assert submit["to_status"] == "submitted"


@pytest.mark.skip(reason="NOT_AUTOMATED: A8_BASE has no audit-trail read interface for configuration changes.")
def test_iaa_br_503_02_configuration_action_writes_audit_trail():
    """IAA-BR-503-02; source_id: IAA-BR-503 configuration action."""


def test_iaa_br_504_01_event_creates_dashboard_notification(stub_iam, configured):
    """IAA-BR-504-01; source_id: IAA-BR-504 notification trigger events."""
    run = IaaHttp(stub_iam)
    item = run.submitted_expense()
    creator_feed = run.get(CREATOR, "/notifications")
    finance_feed = run.get(FINANCE, "/notifications")
    assert any(n["kind"] == "submitted" and n["entity_id"] == item["id"]
               for n in creator_feed["notifications"])
    assert any(n["kind"] == "submitted" and n["entity_id"] == item["id"]
               for n in finance_feed["notifications"])
