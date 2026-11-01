from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError as ModelValidationError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from modules.hreis.decisions import decide, settle, verify
from modules.hreis.models import (
    AuditEvent,
    EmployeeRecord,
    HRRequest,
    LeaveAccount,
    LeavePolicy,
    Notification,
    WorkflowRoute,
)
from modules.hreis.submissions import submit
from modules.hreis.support import route_for

pytestmark = pytest.mark.django_db
BASE = "/api/v1/hreis/"


def actor(user_id=1001, *permissions):
    return make_principal(
        user_id=user_id, kind="faculty", modules=("hreis",), permissions=permissions
    )


@pytest.fixture
def records():
    def employee(user):
        return EmployeeRecord.objects.create(
            user_id=user,
            category="faculty",
            department="CSE",
            designation="Teacher",
            appointment_date=date(2020, 1, 1),
        )

    owner, other = employee(1001), employee(1002)
    policy = LeavePolicy.objects.create(
        code="CASUAL", label="Casual", eligible_categories=["faculty"]
    )
    account = LeaveAccount.objects.create(employee=owner, policy=policy, available=10)
    route = WorkflowRoute.objects.create(
        employee_category="faculty", request_kind="LEAVE", department="CSE", steps=[2001, 2002]
    )
    return SimpleNamespace(employee=owner, other=other, policy=policy, account=account, route=route)


def leave(r, offset=10, days=1):
    start = timezone.localdate() + timedelta(days=offset)
    return {
        "kind": "LEAVE",
        "policy": r.policy,
        "start_date": start,
        "end_date": start + timedelta(days=days - 1),
        "purpose": "Personal leave",
    }


def submitted(r, **kwargs):
    return submit(actor(1001, "hreis.requests.submit"), leave(r, **kwargs))


def test_submit_ownership_audit_and_reservation(records):
    req = submitted(records, days=6)
    assert (req.employee_id, req.days, req.status) == (records.employee.pk, Decimal(6), "PENDING")
    records.account.refresh_from_db()
    assert records.account.available == 10
    assert AuditEvent.objects.filter(request=req, actor_id=1001).exists()
    assert Notification.objects.filter(request=req, recipient_id=1001).exists()
    for kwargs in ({"offset": 30, "days": 5}, {"offset": 10}):
        with pytest.raises(ValidationError):
            submitted(records, **kwargs)
    assert HRRequest.objects.count() == 1


@pytest.mark.parametrize("problem", ["account", "route", "policy", "category", "retired"])
def test_failed_submission_is_atomic(records, problem):
    if problem == "account":
        records.account.delete()
    elif problem == "route":
        records.route.delete()
    elif problem == "policy":
        records.policy.active = False
        records.policy.save()
    elif problem == "category":
        records.policy.eligible_categories = ["staff"]
        records.policy.save()
    else:
        records.employee.retired = True
        records.employee.save()
    with pytest.raises(ValidationError):
        submitted(records)
    assert not HRRequest.objects.exists() and not AuditEvent.objects.exists()


def test_approval_order_snapshot_and_replay(records):
    req = submitted(records)
    records.route.steps = [9999]
    records.route.save()
    with pytest.raises(PermissionDenied):
        decide(actor(9999, "hreis.requests.decide"), req.pk, "FORWARD")
    with pytest.raises(ValidationError):
        decide(actor(2001, "hreis.requests.decide"), req.pk, "APPROVE")
    decide(actor(2001, "hreis.requests.decide"), req.pk, "FORWARD")
    decide(actor(2002, "hreis.requests.decide"), req.pk, "APPROVE")
    with pytest.raises(ValidationError):
        decide(actor(2002, "hreis.requests.decide"), req.pk, "APPROVE")
    records.account.refresh_from_db()
    assert records.account.available == 9


def test_rejection_releases_pending_balance(records):
    req = submitted(records)
    decide(actor(2001, "hreis.requests.decide"), req.pk, "REJECT")
    assert submitted(records).status == "PENDING"
    records.account.refresh_from_db()
    assert records.account.available == 10


@pytest.mark.parametrize("kind", ["LTC", "CPDA"])
def test_claim_verification_approval_and_settlement(records, kind):
    WorkflowRoute.objects.create(
        employee_category="faculty", request_kind=kind, department="CSE", steps=[2001]
    )
    req = submit(
        actor(1001, "hreis.requests.submit"),
        {
            "kind": kind,
            "mode": "ADVANCE",
            "purpose": "Travel",
            "amount": Decimal(100),
            "documents": ["evidence/ref"],
        },
    )
    assert req.status == "SUBMITTED"
    with pytest.raises(ValidationError):
        decide(actor(2001, "hreis.requests.decide"), req.pk, "APPROVE")
    with pytest.raises(ValidationError):
        settle(actor(4001, "hreis.claims.settle"), req.pk, "REF-01")
    verify(actor(3001, "hreis.claims.verify"), req.pk)
    decide(actor(2001, "hreis.requests.decide"), req.pk, "APPROVE")
    with pytest.raises(ValidationError):
        settle(actor(4001, "hreis.claims.settle"), req.pk, " ")
    settle(actor(4001, "hreis.claims.settle"), req.pk, "REF-01")
    with pytest.raises(ValidationError):
        settle(actor(4001, "hreis.claims.settle"), req.pk, "REF-01")
    req.refresh_from_db()
    assert req.status == "SETTLED"
    assert AuditEvent.objects.filter(request=req, details__reference="REF-01").count() == 1


@pytest.mark.parametrize("change", [{"documents": []}, {"amount": 0}, {"mode": ""}])
def test_invalid_claim(records, change):
    data = {
        "kind": "CPDA",
        "mode": "REIMBURSEMENT",
        "purpose": "Conference",
        "amount": Decimal(100),
        "documents": ["evidence/ref"],
    }
    data.update(change)
    with pytest.raises(ValidationError):
        submit(actor(1001, "hreis.requests.submit"), data)
    assert not HRRequest.objects.exists()


@pytest.mark.parametrize("steps", [[], [True], ["2001"], [2001, 2001]])
def test_invalid_route(records, steps):
    records.route.steps = steps
    records.route.save()
    with pytest.raises(ValidationError):
        route_for(records.employee, "LEAVE")


def test_department_and_active_route_selection(records):
    records.route.department = "ECE"
    records.route.save()
    with pytest.raises(ValidationError):
        route_for(records.employee, "LEAVE")
    records.route.department, records.route.active = "CSE", False
    records.route.save()
    with pytest.raises(ValidationError):
        route_for(records.employee, "LEAVE")
    WorkflowRoute.objects.create(
        employee_category="faculty", request_kind="LEAVE", department="", steps=[3001]
    )
    assert route_for(records.employee, "LEAVE") == [3001]


def test_audit_guards_and_rollback(records, monkeypatch):
    event = AuditEvent.objects.create(actor_id=3001, action="record.created")
    with pytest.raises(ModelValidationError):
        event.save()
    with pytest.raises(ModelValidationError):
        event.delete()

    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic audit failure")

    monkeypatch.setattr("modules.hreis.submissions.emit", fail)
    with pytest.raises(RuntimeError):
        submitted(records)
    assert not HRRequest.objects.exists()


def api(stub_iam, user=1001, permissions=(), modules=("hreis",)):
    stub_iam(make_session(user_id=user, kind="faculty", modules=modules, permissions=permissions))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token synthetic-test")
    return client


def test_employee_reads_scoped_and_writes_require_admin(records, stub_iam):
    c = api(stub_iam, permissions=("hreis.records.view",))
    assert [x["user_id"] for x in c.get(BASE + "employees/").data["results"]] == [1001]
    assert c.get(BASE + f"employees/{records.other.pk}/").status_code == 404
    assert (
        c.patch(BASE + f"employees/{records.employee.pk}/", {"designation": "Other"}).status_code
        == 403
    )
    c = api(stub_iam, 3001, ("hreis.records.view", "hreis.records.manage"))
    data = {
        "user_id": 1003,
        "category": "staff",
        "department": "HR",
        "designation": "Officer",
        "appointment_date": "2020-01-01",
        "service_history": [{"event": "appointed"}],
    }
    result = c.post(BASE + "employees/", data, format="json")
    assert result.status_code == 201, result.data
    assert c.post(BASE + "employees/", data, format="json").status_code == 400
    assert c.patch(BASE + f"employees/{result.data['id']}/", {"user_id": 1004}).status_code == 400
    assert AuditEvent.objects.filter(actor_id=3001, action="record.created").exists()


def test_module_grant_and_private_notifications(records, stub_iam):
    c = api(stub_iam, permissions=("hreis.records.view",), modules=())
    assert c.get(BASE + "employees/").status_code == 403
    Notification.objects.create(recipient_id=1001, event="own")
    Notification.objects.create(recipient_id=1002, event="foreign")
    c = api(stub_iam, permissions=("hreis.notifications.view",))
    assert [x["event"] for x in c.get(BASE + "notifications/").data["results"]] == ["own"]


@pytest.mark.parametrize(
    "forged", [{"employee": 1002}, {"status": "APPROVED"}, {"route": [1001]}, {"step": 99}]
)
def test_submission_rejects_forged_fields(records, stub_iam, forged):
    c = api(stub_iam, permissions=("hreis.requests.submit",))
    data = leave(records)
    data["policy"] = records.policy.pk
    data.update(forged)
    assert c.post(BASE + "requests/", data, format="json").status_code == 400
    assert not HRRequest.objects.exists()


def test_request_submission_is_immutable_and_private(records, stub_iam):
    c = api(stub_iam, permissions=("hreis.requests.submit", "hreis.requests.view"))
    data = leave(records)
    data["policy"] = records.policy.pk
    result = c.post(BASE + "requests/", data, format="json")
    assert result.status_code == 201, result.data
    pk = result.data["id"]
    assert c.patch(BASE + f"requests/{pk}/", {"status": "APPROVED"}).status_code in (403, 405)
    assert c.delete(BASE + f"requests/{pk}/").status_code in (403, 405)
    assert HRRequest.objects.get(pk=pk).status == "PENDING"
    c = api(stub_iam, 1002, ("hreis.requests.view",))
    assert c.get(BASE + f"requests/{pk}/").status_code == 404


def test_audit_requires_permission_and_has_no_write_api(records, stub_iam):
    c = api(stub_iam, permissions=("hreis.records.view",))
    assert c.get(BASE + "audit/").status_code == 403
    c = api(stub_iam, 3001, ("hreis.audit.view",))
    assert c.get(BASE + "audit/").status_code == 200
    assert c.post(BASE + "audit/", {"action": "fake"}).status_code in (403, 405)


@pytest.mark.parametrize("steps", [[True], [-1], [2001, 2001], []])
def test_route_serializer_rejects_bad_configuration(records, stub_iam, steps):
    c = api(stub_iam, 3001, ("hreis.config.manage",))
    assert (
        c.patch(BASE + f"routes/{records.route.pk}/", {"steps": steps}, format="json").status_code
        == 400
    )


@pytest.mark.parametrize("kind", ["LEAVE", "CPDA"])
def test_api_workflow_transitions(records, stub_iam, kind):
    c = api(stub_iam, permissions=("hreis.requests.submit", "hreis.requests.view"))
    if kind == "LEAVE":
        data = leave(records)
        data["policy"] = records.policy.pk
    else:
        WorkflowRoute.objects.create(
            employee_category="faculty", request_kind=kind, department="CSE", steps=[2001]
        )
        data = {
            "kind": kind,
            "mode": "ADVANCE",
            "purpose": "Conference",
            "amount": "100.00",
            "documents": ["evidence/ref"],
        }
    response = c.post(BASE + "requests/", data, format="json")
    assert response.status_code == 201, response.data
    pk = response.data["id"]
    if kind != "LEAVE":
        c = api(stub_iam, 3001, ("hreis.claims.verify",))
        response = c.post(BASE + f"requests/{pk}/verify/", {}, format="json")
        assert response.status_code == 200, response.data
    c = api(stub_iam, 2001, ("hreis.requests.decide",))
    if kind == "LEAVE":
        response = c.post(BASE + f"requests/{pk}/decide/", {"outcome": "FORWARD"}, format="json")
        assert response.status_code == 200, response.data
        c = api(stub_iam, 2002, ("hreis.requests.decide",))
    response = c.post(BASE + f"requests/{pk}/decide/", {"outcome": "APPROVE"}, format="json")
    assert response.status_code == 200, response.data
    if kind != "LEAVE":
        c = api(stub_iam, 4001, ("hreis.claims.settle",))
        response = c.post(BASE + f"requests/{pk}/settle/", {"reference": "REF-test"}, format="json")
        assert response.status_code == 200, response.data
        assert response.data["status"] == "SETTLED"
    else:
        records.account.refresh_from_db()
        assert records.account.available == 9


def test_account_api_prevents_negative_balance_and_owner_reassignment(records, stub_iam):
    c = api(stub_iam, 3001, ("hreis.config.manage", "hreis.records.manage"))
    url = BASE + f"accounts/{records.account.pk}/"
    assert c.patch(url, {"available": "-1.00"}, format="json").status_code == 400
    assert c.patch(url, {"employee": records.other.pk}, format="json").status_code == 400
    assert c.patch(url, {"available": "12.00"}, format="json").status_code == 200
    assert AuditEvent.objects.filter(actor_id=3001, action="config.updated").exists()
