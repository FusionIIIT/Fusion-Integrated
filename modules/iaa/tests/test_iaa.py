from decimal import Decimal
import pytest
from modules.iaa.domain import rules, workflow

def test_expense_submission_requires_core_fields():
    issues = rules.submission_errors({})
    assert {x.field for x in issues} >= {"request_type", "department", "description", "amount"}

def test_complete_expense_submission_passes():
    assert rules.submission_errors({
        "request_type": "Stationery", "department": "CSE",
        "description": "Office supplies", "amount": Decimal("1250")
    }) == []

def test_ta_submission_requires_trip_dates_purpose_and_evidence():
    issues = rules.submission_errors({
        "request_type": "TA", "department": "CSE", "description": "Trip",
        "amount": "1200", "trip_start_date": "2026-11-05",
        "trip_end_date": "2026-11-04", "trip_purpose": ""
    }, kind="ta", required_documents=True)
    assert {x.field for x in issues} >= {"trip_end_date", "trip_purpose", "attachments"}

def test_budget_shortfall_does_not_mean_automatic_rejection():
    assert rules.budget_shortfall(amount=1200, allocated=5000, spent=3000,
                                  committed=1000) == Decimal("200")
    assert rules.budget_shortfall(amount=500, allocated=5000, spent=1000,
                                  committed=500) == 0

def test_creator_cannot_approve_own_request():
    assert rules.may_approve(creator_id=10, actor_id=11)
    assert not rules.may_approve(creator_id=10, actor_id=10)

def test_specific_approval_rule_wins():
    chosen = rules.select_approval_rule([
        {"record_kind": "", "request_type": "", "department": "",
         "levels": [{"role": "hod"}], "priority": 100},
        {"record_kind": "expense_voucher", "request_type": "equipment",
         "department": "CSE", "min_amount": "1000",
         "levels": [{"role": "dean"}], "priority": 100},
    ], kind="expense_voucher", request_type="equipment",
       department="CSE", amount=Decimal("2000"))
    assert chosen["levels"][0]["role"] == "dean"

def test_observation_closure_requires_evidence():
    assert rules.may_close_observation(satisfactory=True, has_response=True, has_evidence=True)
    assert not rules.may_close_observation(satisfactory=True, has_response=True, has_evidence=False)

def test_record_state_transitions():
    workflow.assert_record_transition(workflow.DRAFT, workflow.SUBMITTED)
    workflow.assert_record_transition(workflow.VERIFIED, workflow.RECORDED)
    with pytest.raises(workflow.InvalidTransition):
        workflow.assert_record_transition(workflow.DRAFT, workflow.APPROVED)

def test_anomaly_and_observation_state_transitions():
    workflow.assert_anomaly_transition(workflow.ANOMALY_OPEN, workflow.ANOMALY_ESCALATED)
    workflow.assert_anomaly_transition(workflow.ANOMALY_ESCALATED, workflow.ANOMALY_RESOLVED)
    workflow.assert_observation_transition(workflow.OBSERVATION_OPEN, workflow.OBSERVATION_RESPONDED)
    workflow.assert_observation_transition(workflow.OBSERVATION_RESPONDED, workflow.OBSERVATION_OPEN)
    workflow.assert_observation_transition(workflow.OBSERVATION_RESPONDED, workflow.OBSERVATION_CLOSED)

@pytest.mark.django_db
def test_audit_log_is_append_only():
    from modules.iaa.models import AuditLog
    row = AuditLog.objects.create(actor_user_id=10, actor_role="auditor",
                                  action="test.add", resource_type="test")
    row.action = "tampered"
    with pytest.raises(ValueError, match="append-only"):
        row.save()

@pytest.mark.django_db
def test_observation_deletion_is_prohibited():
    from modules.iaa.models import AuditObservation
    row = AuditObservation.objects.create(record_kind="expense_voucher", record_id=1,
        title="Missing documents", details="No evidence", raised_by_id=4)
    with pytest.raises(ValueError, match="deletion is prohibited"):
        row.delete()
