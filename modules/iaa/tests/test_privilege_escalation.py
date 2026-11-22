"""Write authority is a permission and a role, never just visibility (IAA-BR-003, 004)."""
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.iaa import registry
from modules.iaa.domain import roles
from modules.iaa.models import FinancialRecord
from modules.iaa.services import (
    anomalies,
    configuration,
    decisions,
    observations,
    processing,
    records,
    reports,
    review,
)
from modules.iaa.tests.helpers import DOC, FACULTY, actor, api_client, new_expense

pytestmark = pytest.mark.django_db

NOBODY = actor(900, FACULTY, permissions=[])

CALLS = {
    "create_expense": lambda a, r: records.create_expense(a, department="CSE"),
    "update_draft": lambda a, r: records.update_draft(a, r.pk, title="x"),
    "add_document": lambda a, r: records.add_document(a, r.pk, **DOC),
    "submit": lambda a, r: records.submit(a, r.pk),
    "create_ta": lambda a, r: records.create_ta(a, department="CSE", amount=Decimal(1),
                                                purpose="p", trip_start=None, trip_end=None,
                                                documents=[]),
    "respond_query": lambda a, r: records.respond_query(a, r.pk, response="x"),
    "raise_query": lambda a, r: review.raise_query(a, r.pk, question="x"),
    "validate": lambda a, r: review.validate(a, r.pk),
    "decide": lambda a, r: decisions.decide(a, r.pk, decision="approve", remarks="x"),
    "record": lambda a, r: processing.record(a, r.pk, reference="x"),
    "flag": lambda a, r: anomalies.flag(a, category="policy", description="x"),
    "resolve": lambda a, r: anomalies.resolve(a, 1, resolution="x"),
    "escalate": lambda a, r: anomalies.escalate(a, 1, remarks="x"),
    "raise_observation": lambda a, r: observations.raise_observation(
        a, title="t", detail="d", respondent_user_id=1),
    "respond_observation": lambda a, r: observations.respond(a, 1, corrective_action="x"),
    "review_observation": lambda a, r: observations.review(a, 1, verdict="satisfactory"),
    "summary": lambda a, r: reports.summary(a),
    "export": lambda a, r: list(reports.export_rows(a)),
    "publish_policy": lambda a, r: configuration.publish_policy(a, {}),
    "add_year": lambda a, r: configuration.add_financial_year(a, code="x", starts_on=None,
                                                              ends_on=None),
    "add_budget": lambda a, r: configuration.add_budget_entry(
        a, financial_year_id=1, department="x", kind="allocation", amount=Decimal(1)),
}


@pytest.mark.parametrize("name", sorted(CALLS))
def test_an_actor_holding_no_permission_can_do_no_write_or_report(people, configured, name):
    rec = new_expense(people.creator)
    with pytest.raises(PermissionDeniedError) as exc:
        CALLS[name](NOBODY, rec)
    assert exc.value.code == "permission_denied"


@pytest.mark.parametrize("name", sorted(CALLS))
def test_an_unauthenticated_caller_is_refused_everywhere(people, configured, name):
    rec = new_expense(people.creator)
    with pytest.raises(PermissionDeniedError) as exc:
        CALLS[name](None, rec)
    assert exc.value.code == "not_authenticated"


def test_a_creator_cannot_use_finance_or_approval_powers_with_their_own_role(
        people, configured):
    rec = new_expense(people.creator)
    for call in ("raise_query", "validate", "decide", "record"):
        with pytest.raises(PermissionDeniedError):
            CALLS[call](people.creator, rec)


def test_holding_a_finance_permission_in_the_wrong_role_still_sees_nothing(
        people, configured):
    rec = new_expense(people.creator)
    wrong_role = actor(201, FACULTY, permissions=registry.ROLE_GRANTS[roles.FINANCE])
    with pytest.raises(NotFoundError):
        review.validate(wrong_role, rec.pk)                    # not office-wide in this role
    assert FinancialRecord.objects.get(pk=rec.pk).status == "submitted"


def test_an_approver_cannot_approve_an_item_not_assigned_to_their_role(people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    with pytest.raises(NotFoundError):                         # the Dean has no step yet
        decisions.decide(people.dean, rec.pk, decision="approve", remarks="Jump the queue")
    with pytest.raises(NotFoundError):                         # the other department's HoD
        decisions.decide(people.hod_ece, rec.pk, decision="approve", remarks="Wrong dept")
    assert FinancialRecord.objects.get(pk=rec.pk).status == "finance_validated"


def test_an_approver_holding_the_right_permission_cannot_record_or_validate(
        people, configured):
    rec = new_expense(people.creator)
    review.validate(people.finance, rec.pk)
    decisions.decide(people.hod, rec.pk, decision="approve", remarks="ok")
    for call in ("record", "validate", "raise_query"):
        with pytest.raises(PermissionDeniedError):
            CALLS[call](people.hod, rec)


def test_the_system_admin_has_no_operational_power_whatever_the_request(people, configured):
    rec = new_expense(people.creator)
    for call in ("validate", "decide", "record", "raise_query", "submit", "flag",
                 "raise_observation", "summary", "export"):
        with pytest.raises(PermissionDeniedError):
            CALLS[call](people.admin, rec)
    assert not set(registry.ROLE_GRANTS[roles.SYSTEM_ADMIN]) - {
        "iaa.configuration.view", "iaa.configuration.update"}


def test_nobody_but_the_admin_role_configures_even_with_the_code(people, configured):
    for role in (roles.FINANCE, roles.HOD, roles.AUDITOR):
        holder = actor(700, role, permissions=["iaa.configuration.update"])
        with pytest.raises(ConflictError):
            configuration.add_financial_year(holder, code="Z", starts_on=None, ends_on=None)


def test_an_auditor_can_flag_and_observe_but_not_change_a_request(people, configured):
    rec = new_expense(people.creator)
    for call in ("validate", "decide", "record", "raise_query"):
        with pytest.raises(PermissionDeniedError):
            CALLS[call](people.auditor, rec)
    assert anomalies.flag(people.auditor, category="financial", description="x").pk


def test_finance_cannot_raise_an_observation_or_close_one(people, configured):
    rec = new_expense(people.creator)
    with pytest.raises(PermissionDeniedError):
        CALLS["raise_observation"](people.finance, rec)
    with pytest.raises(PermissionDeniedError):
        CALLS["review_observation"](people.finance, rec)


# ── over HTTP: two gates, module grant then permission ──────────────────────────────────

URLS = [
    ("get", "/api/v1/iaa/records"), ("post", "/api/v1/iaa/records"),
    ("get", "/api/v1/iaa/anomalies"), ("get", "/api/v1/iaa/observations"),
    ("get", "/api/v1/iaa/reports/summary"), ("get", "/api/v1/iaa/reports/export"),
    ("get", "/api/v1/iaa/notifications"), ("get", "/api/v1/iaa/config/policies"),
    ("post", "/api/v1/iaa/config/policies"), ("get", "/api/v1/iaa/config/financial-years"),
    ("get", "/api/v1/iaa/config/budget-entries"),
]


@pytest.mark.parametrize("method,url", URLS)
def test_without_the_module_grant_every_endpoint_is_403(stub_iam, method, url):
    client = api_client(stub_iam, 101, FACULTY, modules=())
    assert getattr(client, method)(url, {}, format="json").status_code == 403


@pytest.mark.parametrize("method,url", URLS)
def test_without_the_permission_every_endpoint_is_403(stub_iam, method, url):
    client = api_client(stub_iam, 101, FACULTY, permissions=[])
    assert getattr(client, method)(url, {}, format="json").status_code == 403


@pytest.mark.parametrize("method,url", URLS)
def test_an_anonymous_caller_is_401(stub_iam, method, url):
    from rest_framework.test import APIClient

    stub_iam(None)
    assert getattr(APIClient(), method)(url, {}, format="json").status_code in (401, 403)


def test_a_creator_is_403_on_finance_approval_and_configuration_endpoints(
        stub_iam, people, configured):
    rec = new_expense(people.creator)
    client = api_client(stub_iam, 101, FACULTY)
    for url, body in ((f"/api/v1/iaa/records/{rec.pk}/query", {"text": "x"}),
                      (f"/api/v1/iaa/records/{rec.pk}/validate", {}),
                      (f"/api/v1/iaa/records/{rec.pk}/decision",
                       {"decision": "approve", "remarks": "me"}),
                      (f"/api/v1/iaa/records/{rec.pk}/processing", {"reference": "x"}),
                      ("/api/v1/iaa/anomalies", {"category": "policy", "description": "x"}),
                      ("/api/v1/iaa/config/policies", {})):
        assert client.post(url, body, format="json").status_code == 403, url
