from datetime import timedelta

import pytest
from django.db import DatabaseError, transaction
from django.utils import timezone
from freezegun import freeze_time

from modules.iaa import services
from modules.iaa.domain.rules import Role
from modules.iaa.models import (
    Anomaly,
    ApprovalRoute,
    AuditEntry,
    Budget,
    FinancialRequest,
    Notification,
    Observation,
    RoleAssignment,
)
from modules.iaa.tests.conftest import (
    ADMIN,
    AUDITOR,
    BASIC,
    DEAN,
    DIRECTOR,
    FINANCE,
    HOD,
    action,
    draft,
    submitted,
    validated,
)

pytestmark = pytest.mark.django_db


def test_incomplete_draft_survives_but_cannot_be_submitted(world, client_as):
    c = client_as(BASIC)
    r = c.post("/api/v1/iaa/requests", {"kind": "expense"}, format="json")
    assert r.status_code == 201
    assert "amount" in r.json()["missing_fields"]
    pk = r.json()["id"]
    assert c.get(f"/api/v1/iaa/requests/{pk}").status_code == 200
    assert action(c, pk, "submit").status_code == 400
    assert FinancialRequest.objects.get(pk=pk).status == "draft"


def test_expense_complete_multilevel_route_and_internal_record(world, client_as):
    pk = validated(client_as)
    assert FinancialRequest.objects.get(pk=pk).status == "finance_validated"
    for uid, status in [
        (HOD, "approval_pending"),
        (DEAN, "approval_pending"),
        (DIRECTOR, "approved"),
    ]:
        r = action(client_as(uid), pk, "decide", approve=True, remarks="Approved after review")
        assert r.status_code == 200, r.json()
        assert r.json()["status"] == status
    r = action(client_as(FINANCE), pk, "record", reference="Internal record 1")
    assert r.json()["status"] == "recorded"
    entry = AuditEntry.objects.filter(request_id=pk, action="record_internal_completion").get()
    assert entry.details["monetary_transfer"] is False
    assert entry.active_role == Role.FINANCE and entry.actor_id == FINANCE
    assert action(client_as(FINANCE), pk, "record", reference="duplicate").status_code == 409
    assert Notification.objects.filter(
        request_id=pk, user_id=BASIC, event="record_internal_completion"
    ).exists()


def test_clarification_preserves_creator_content_and_history(world, client_as):
    pk = submitted(client_as)
    assert (
        action(client_as(FINANCE), pk, "query", remarks="Supply receipt").json()["status"]
        == "query_raised"
    )
    c = client_as(BASIC)
    assert (
        c.patch(f"/api/v1/iaa/requests/{pk}", {"amount": "9999"}, format="json").status_code == 409
    )
    assert (
        action(
            c, pk, "respond", response="Receipt attached", evidence=["https://example.org/receipt"]
        ).json()["status"]
        == "query_responded"
    )
    assert action(client_as(FINANCE), pk, "validate", remarks="Satisfied").status_code == 200
    req = FinancialRequest.objects.get(pk=pk)
    assert req.amount == 100
    assert req.clarifications.get().response == "Receipt attached"
    assert req.history.filter(action="query_responded").get().details["evidence"]


@pytest.mark.parametrize("amount,expected", [("100", "verified"), ("500", "approval_pending")])
def test_ta_threshold_is_configured_and_inclusive(world, client_as, amount, expected):
    pk = validated(
        client_as, kind="ta", amount=amount, trip_start="2027-02-25", trip_end="2027-02-26"
    )
    assert FinancialRequest.objects.get(pk=pk).status == expected
    if expected == "verified":
        assert (
            action(client_as(FINANCE), pk, "record", reference="TA internal record").status_code
            == 200
        )


@pytest.mark.parametrize(
    "over", [{"trip_start": None}, {"trip_end": "2027-02-20"}, {"documents": []}]
)
def test_invalid_ta_never_leaves_a_partial_draft(world, client_as, over):
    r = draft(
        client_as(BASIC),
        **{"kind": "ta", "trip_start": "2027-02-25", "trip_end": "2027-02-26", **over},
    )
    assert r.status_code == 400, r.json()
    assert not FinancialRequest.objects.exists()
    assert not AuditEntry.objects.filter(action="create_draft").exists()


def test_ta_policy_rejection_and_cap(world, client_as):
    pk = submitted(
        client_as, kind="ta", amount="2001", trip_start="2027-02-25", trip_end="2027-02-25"
    )
    assert action(client_as(FINANCE), pk, "validate", remarks="Over daily cap").status_code == 409
    r = action(client_as(FINANCE), pk, "validate", remarks="Policy violation", compliant=False)
    assert r.json()["status"] == "rejected"


def test_insufficient_budget_creates_anomaly_without_rejecting(world, client_as):
    Budget.objects.update(allocated=50)
    pk = submitted(client_as)
    r = action(client_as(FINANCE), pk, "validate", remarks="Budget review")
    assert r.status_code == 200 and r.json()["status"] == "submitted"
    anomaly = Anomaly.objects.get(request_id=pk)
    assert anomaly.automatic and anomaly.status == "open"
    assert AuditEntry.objects.filter(
        object_id=anomaly.pk, action="automatic_anomaly", active_role="System"
    ).exists()
    assert action(client_as(FINANCE), pk, "validate", remarks="Retry").status_code == 409
    c = client_as(FINANCE)
    assert (
        c.post(
            f"/api/v1/iaa/anomalies/{anomaly.pk}/resolve",
            {"remarks": "Funding added"},
            format="json",
        ).status_code
        == 200
    )
    Budget.objects.update(allocated=1000)
    assert (
        action(client_as(FINANCE), pk, "validate", remarks="Recheck").json()["status"]
        == "finance_validated"
    )


def test_budget_reservations_cover_inflight_requests(world, client_as):
    Budget.objects.update(allocated=150)
    first = validated(client_as)
    second = submitted(client_as)
    r = action(client_as(FINANCE), second, "validate", remarks="Review")
    assert r.json()["status"] == "submitted"
    assert FinancialRequest.objects.get(pk=first).reservation == 100
    assert (
        action(client_as(HOD), first, "decide", approve=False, remarks="Declined").status_code
        == 200
    )
    assert FinancialRequest.objects.get(pk=first).reservation == 0


def test_manual_anomaly_escalation_is_independent(world, client_as):
    pk = validated(client_as)
    r = action(
        client_as(AUDITOR), pk, "anomaly", category="policy", description="Material discrepancy"
    )
    aid = r.json()["id"]
    assert action(client_as(HOD), pk, "decide", approve=True, remarks="Review").status_code == 409
    r = client_as(FINANCE).post(
        f"/api/v1/iaa/anomalies/{aid}/resolve",
        {"escalate": True, "remarks": "Audit review needed"},
        format="json",
    )
    assert r.json()["status"] == "escalated"
    r = client_as(AUDITOR).post(
        f"/api/v1/iaa/anomalies/{aid}/resolve", {"remarks": "Resolved with evidence"}, format="json"
    )
    assert r.json()["status"] == "resolved"
    assert FinancialRequest.objects.get(pk=pk).status == "finance_validated"


def test_audit_observation_rework_and_verified_closure(world, client_as):
    pk = submitted(client_as)
    r = action(client_as(AUDITOR), pk, "observation", description="Explain procurement evidence")
    oid = r.json()["id"]
    url = f"/api/v1/iaa/observations/{oid}"
    assert (
        client_as(AUDITOR)
        .post(url + "/review", {"satisfactory": True, "verification": "Seen"}, format="json")
        .status_code
        == 409
    )
    assert (
        client_as(BASIC)
        .post(url + "/respond", {"response": "Corrected", "evidence": []}, format="json")
        .status_code
        == 400
    )
    for satisfied in (False, True):
        r = client_as(BASIC).post(
            url + "/respond",
            {"response": "Corrective action", "evidence": ["https://example.org/correction"]},
            format="json",
        )
        assert r.json()["status"] == "responded"
        r = client_as(AUDITOR).post(
            url + "/review",
            {"satisfactory": satisfied, "verification": "Evidence reviewed"},
            format="json",
        )
        assert r.json()["status"] == ("closed" if satisfied else "open")
    assert Observation.objects.get(pk=oid).status == "closed"
    assert (
        AuditEntry.objects.filter(
            object_type="observation", object_id=oid, action="respond_observation"
        ).count()
        == 2
    )
    assert (
        client_as(BASIC)
        .post(
            url + "/respond",
            {"response": "again", "evidence": ["https://example.org/x"]},
            format="json",
        )
        .status_code
        == 409
    )


def test_overdue_approval_escalates_once_per_assignment(world, client_as):
    pk = validated(client_as)
    now = timezone.now() + timedelta(hours=25)
    assert services.escalate_overdue(now)["escalated"] == 1
    assert services.escalate_overdue(now)["escalated"] == 0
    req = FinancialRequest.objects.get(pk=pk)
    assert req.status == "escalated" and req.assignee_id == DEAN
    assert action(client_as(HOD), pk, "decide", approve=True, remarks="Too late").status_code == 404
    assert (
        action(client_as(DEAN), pk, "decide", approve=True, remarks="Escalated review").json()[
            "assignee_id"
        ]
        == DIRECTOR
    )


def test_top_level_timeout_does_not_auto_reject(world, client_as):
    pk = validated(client_as)
    action(client_as(HOD), pk, "decide", approve=True, remarks="Okay")
    action(client_as(DEAN), pk, "decide", approve=True, remarks="Okay")
    now = timezone.now() + timedelta(hours=100)
    assert services.escalate_overdue(now)["blocked"] == 1
    services.escalate_overdue(now)
    assert AuditEntry.objects.filter(request_id=pk, action="escalation_blocked:2").count() == 1
    assert FinancialRequest.objects.get(pk=pk).status == "approval_pending"


def test_creator_authority_is_skipped_with_multiple_roles(world, client_as):
    RoleAssignment.objects.create(user_id=BASIC, role=Role.HOD, department="CSE")
    route = ApprovalRoute.objects.get(kind="expense")
    route.steps[0]["user_id"] = BASIC
    route.save()
    pk = validated(client_as)
    assert FinancialRequest.objects.get(pk=pk).assignee_id == DEAN
    assert (
        action(client_as(BASIC, Role.HOD), pk, "decide", approve=True, remarks="Self").status_code
        == 404
    )


def test_all_self_route_is_blocked_without_reservation(world, client_as):
    route = ApprovalRoute.objects.get(kind="expense")
    route.steps = [{"user_id": BASIC, "role": Role.HOD, "timeout_hours": 24}]
    route.save()
    pk = submitted(client_as)
    r = action(client_as(FINANCE), pk, "validate", remarks="Checked")
    assert r.status_code == 409 and r.json()["error"]["code"] == "self_routing"
    assert FinancialRequest.objects.get(pk=pk).reservation == 0


def test_audit_entries_are_immutable_through_bulk_sql(world, client_as):
    submitted(client_as)
    entry = AuditEntry.objects.first()
    for mutate in (
        lambda: AuditEntry.objects.filter(pk=entry.pk).update(active_role="tampered"),
        lambda: AuditEntry.objects.filter(pk=entry.pk).delete(),
    ):
        with pytest.raises(DatabaseError), transaction.atomic():
            mutate()
    entry.refresh_from_db()
    assert entry.active_role == Role.BASIC


def test_configuration_rejects_overlap_and_unsafe_budget_reduction(world, client_as):
    c = client_as(ADMIN)
    r = c.post(
        "/api/v1/iaa/config/years",
        {"name": "overlap", "starts_on": "2027-01-01", "ends_on": "2027-12-31", "active": True},
        format="json",
    )
    assert r.status_code == 409
    validated(client_as)
    budget = Budget.objects.get()
    c = client_as(ADMIN)
    r = c.post(
        "/api/v1/iaa/config/budgets",
        {"id": budget.pk, "department": "CSE", "year": budget.year_id, "allocated": "50"},
        format="json",
    )
    assert r.status_code == 409


def test_reports_are_read_only_and_scope_turnaround(world, client_as):
    validated(client_as)
    before = FinancialRequest.objects.count()
    r = client_as(AUDITOR).get("/api/v1/iaa/reports")
    assert r.status_code == 200 and r.json()["requests"] == 1
    assert r.json()["average_turnaround_seconds"] is None
    r = client_as(AUDITOR).get("/api/v1/iaa/reports?export=csv")
    assert r.status_code == 200 and b"Department" in r.content
    assert FinancialRequest.objects.count() == before


def test_report_measures_authority_turnaround_separately_from_processing(world, client_as):
    pk = validated(client_as)
    with freeze_time("2027-03-01 11:00:00"):
        response = action(client_as(HOD), pk, "decide", approve=True, remarks="Two hour review")
        assert response.status_code == 200
    response = client_as(AUDITOR).get("/api/v1/iaa/reports")
    assert response.json()["average_approval_turnaround_seconds"] == 7200
    assert response.json()["average_turnaround_seconds"] is None


def test_recorded_financial_data_is_immutable_at_database_level(world, client_as):
    pk = validated(
        client_as, kind="ta", amount="100", trip_start="2027-02-25", trip_end="2027-02-26"
    )
    assert (
        action(client_as(FINANCE), pk, "record", reference="Immutable completion").status_code
        == 200
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        FinancialRequest.objects.filter(pk=pk).update(amount="200")
    assert FinancialRequest.objects.get(pk=pk).amount == 100


def test_observation_cannot_be_deleted_even_before_closure(world, client_as):
    pk = submitted(client_as)
    oid = action(client_as(AUDITOR), pk, "observation", description="Retain evidence").json()["id"]
    with pytest.raises(DatabaseError), transaction.atomic():
        Observation.objects.filter(pk=oid).delete()
    assert Observation.objects.filter(pk=oid).exists()
