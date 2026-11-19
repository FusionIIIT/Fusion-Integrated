"""Service requirements: AFR-IAA-001..030 and AFR-IAA-043..047."""
from types import SimpleNamespace

import pytest

from modules.iaa.domain import state_machine as sm
from modules.iaa.models import (
    ApprovalRouteRule, ApprovalStep, DepartmentBudget, FinancialYear,
    IaaRoleAssignment,
)
from modules.iaa.services.records import (
    IaaAccessError, decide_request, record_request, review_request,
    save_request, submit_request,
)


def actor(user_id, role, *, kind="staff"):
    return SimpleNamespace(user_id=user_id, roles=(role,), kind=kind)


@pytest.mark.django_db
def test_incomplete_draft_is_allowed_but_submission_is_rejected():
    creator = actor(10, sm.BASIC_USER)
    draft = save_request(principal=creator, role=sm.BASIC_USER, values={})
    assert draft.status == "Draft"
    with pytest.raises(sm.GuardFailed):
        submit_request(principal=creator, role=sm.BASIC_USER, request_id=draft.pk)
    draft.refresh_from_db()
    assert draft.status == "Draft"


@pytest.mark.django_db
def test_budget_insufficiency_creates_anomaly_event_without_rejecting():
    year = FinancialYear.objects.create(code="FY-test", starts_on="2026-04-01",
        ends_on="2027-03-31", is_active=True, created_by_id=1)
    DepartmentBudget.objects.create(financial_year=year, department="CSE",
        available_amount="10.00", updated_by_id=1)
    route = ApprovalRouteRule.objects.create(request_type="", department="",
        levels=[sm.HOD], escalation_roles=[sm.DEAN], timeout_seconds=60,
        updated_by_id=1)
    IaaRoleAssignment.objects.create(user_id=40, role=sm.HOD, department="CSE",
                                     assigned_by_id=1)
    creator = actor(10, sm.BASIC_USER)
    draft = save_request(principal=creator, role=sm.BASIC_USER, values={
        "department": "CSE", "request_type": "equipment", "amount": "50.00",
        "description": "Equipment for teaching"})
    submit_request(principal=creator, role=sm.BASIC_USER, request_id=draft.pk)
    reviewed = review_request(principal=actor(20, sm.FINANCE), role=sm.FINANCE,
                              request_id=draft.pk, action="validate")
    assert reviewed.status == "Approval Pending"
    assert reviewed.status != "Rejected"
    assert reviewed.active_route_id == route.pk
    from modules.iaa.models import AutomaticAnomalyEvent
    assert AutomaticAnomalyEvent.objects.filter(
        record_type="request", record_id=draft.pk,
        condition="budget_insufficient").exists()


@pytest.mark.django_db
def test_request_creator_cannot_approve_their_own_request():
    year = FinancialYear.objects.create(code="FY-test", starts_on="2026-04-01",
        ends_on="2027-03-31", is_active=True, created_by_id=1)
    DepartmentBudget.objects.create(financial_year=year, department="CSE",
        available_amount="1000.00", updated_by_id=1)
    ApprovalRouteRule.objects.create(request_type="", department="",
        levels=[sm.HOD], updated_by_id=1)
    IaaRoleAssignment.objects.create(user_id=40, role=sm.HOD, department="CSE",
                                     assigned_by_id=1)
    creator = actor(10, sm.BASIC_USER)
    draft = save_request(principal=creator, role=sm.BASIC_USER, values={
        "department": "CSE", "request_type": "equipment", "amount": "50.00",
        "description": "Equipment"})
    submit_request(principal=creator, role=sm.BASIC_USER, request_id=draft.pk)
    review_request(principal=actor(20, sm.FINANCE), role=sm.FINANCE,
                   request_id=draft.pk, action="validate")
    with pytest.raises(IaaAccessError):
        decide_request(principal=SimpleNamespace(user_id=10,
            roles=(sm.BASIC_USER, sm.HOD), kind="staff"), role=sm.HOD,
            request_id=draft.pk, decision="Approved", remarks="Not allowed")
    assert ApprovalStep.objects.filter(record_id=draft.pk, status="Pending").exists()


@pytest.mark.django_db
def test_approved_request_is_recorded_as_internal_non_monetary_completion():
    year = FinancialYear.objects.create(code="FY-test", starts_on="2026-04-01",
        ends_on="2027-03-31", is_active=True, created_by_id=1)
    DepartmentBudget.objects.create(financial_year=year, department="CSE",
        available_amount="1000.00", updated_by_id=1)
    ApprovalRouteRule.objects.create(request_type="", department="",
        levels=[sm.HOD], updated_by_id=1)
    IaaRoleAssignment.objects.create(user_id=40, role=sm.HOD, department="CSE",
                                     assigned_by_id=1)
    creator = actor(10, sm.BASIC_USER)
    draft = save_request(principal=creator, role=sm.BASIC_USER, values={
        "department": "CSE", "request_type": "equipment", "amount": "50.00",
        "description": "Equipment"})
    submit_request(principal=creator, role=sm.BASIC_USER, request_id=draft.pk)
    review_request(principal=actor(20, sm.FINANCE), role=sm.FINANCE,
                   request_id=draft.pk, action="validate")
    approved = decide_request(principal=actor(40, sm.HOD), role=sm.HOD,
                              request_id=draft.pk, decision="Approved", remarks="Approved")
    recorded = record_request(principal=actor(20, sm.FINANCE), role=sm.FINANCE,
                              request_id=draft.pk,
                              processing_details="Internal processing documented")
    assert approved.status == "Approved"
    assert recorded.status == "Recorded"
    assert recorded.recorded_at is not None
    from modules.iaa.models import ActionHistory
    assert ActionHistory.objects.filter(record_id=draft.pk,
        details__monetary_transfer=False).exists()
