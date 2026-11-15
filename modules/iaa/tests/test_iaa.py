"""IAA expense/voucher lifecycle: BW-IAA-01 happy path, BW-IAA-03 rejection, and the BRs."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.iaa import domain
from modules.iaa.models import ExpenseRequest

CREATOR, FINANCE, APPROVER, OTHER = 1001, 2001, 3001, 1002
URL = "/api/v1/iaa/requests"
COMPLETE = {"department": "CSE", "purpose": "Lab consumables", "amount": "1500.00"}


def _as(stub_iam, user_id, *perms):
    stub_iam(make_session(user_id=user_id, kind="staff", modules=("iaa",),
                          permissions=perms), users={})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _validated(creator=CREATOR):
    return ExpenseRequest.objects.create(
        creator_user_id=creator, status=domain.FINANCE_VALIDATED, **COMPLETE)


def test_domain_rules():
    domain.check_submission_complete("Books", Decimal("10"), "CSE")
    with pytest.raises(domain.RuleViolation, match="IAA-BR-101"):
        domain.check_submission_complete("", None, "CSE")
    with pytest.raises(domain.RuleViolation, match="IAA-BR-001"):
        domain.check_not_self_approval(7, 7)
    with pytest.raises(domain.RuleViolation, match="IAA-BR-005"):
        domain.check_remarks("   ")
    with pytest.raises(domain.RuleViolation, match="IAA-BR-104"):
        domain.check_editable(domain.SUBMITTED)
    assert domain.status_after_decision("reject") == domain.REJECTED


@pytest.mark.django_db
def test_bw_iaa_01_draft_to_recorded(stub_iam):
    c = _as(stub_iam, CREATOR, "iaa.request.create")
    pk = c.post(URL, {"purpose": "Lab consumables"}, format="json").json()["id"]
    assert c.patch(f"{URL}/{pk}", COMPLETE, format="json").status_code == 200
    assert c.post(f"{URL}/{pk}/submit").json()["status"] == domain.SUBMITTED

    c = _as(stub_iam, FINANCE, "iaa.request.validate", "iaa.request.record")
    assert c.post(f"{URL}/{pk}/validate").json()["status"] == domain.FINANCE_VALIDATED

    c = _as(stub_iam, APPROVER, "iaa.request.decide")
    r = c.post(f"{URL}/{pk}/decide", {"decision": "approve", "remarks": "OK"}, format="json")
    assert r.json()["status"] == domain.APPROVED

    c = _as(stub_iam, FINANCE, "iaa.request.validate", "iaa.request.record")
    assert c.post(f"{URL}/{pk}/record").json()["status"] == domain.RECORDED


@pytest.mark.django_db
def test_bw_iaa_03_rejection_keeps_remarks(stub_iam):
    pk = _validated().pk
    c = _as(stub_iam, APPROVER, "iaa.request.decide")
    r = c.post(f"{URL}/{pk}/decide", {"decision": "reject", "remarks": "No budget head"},
               format="json")
    assert r.status_code == 200
    req = ExpenseRequest.objects.get(pk=pk)
    assert (req.status, req.decision_remarks, req.approver_user_id) == (
        domain.REJECTED, "No budget head", APPROVER)


@pytest.mark.django_db
def test_basic_user_cannot_validate(stub_iam):
    pk = ExpenseRequest.objects.create(creator_user_id=CREATOR, status=domain.SUBMITTED,
                                       **COMPLETE).pk
    c = _as(stub_iam, CREATOR, "iaa.request.create")
    assert c.post(f"{URL}/{pk}/validate").status_code == 403


@pytest.mark.django_db
def test_incomplete_submission_is_refused(stub_iam):
    c = _as(stub_iam, CREATOR, "iaa.request.create")
    pk = c.post(URL, {"purpose": "Travel"}, format="json").json()["id"]
    r = c.post(f"{URL}/{pk}/submit")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "incomplete_submission"
    assert ExpenseRequest.objects.get(pk=pk).status == domain.DRAFT


@pytest.mark.django_db
def test_creator_cannot_approve_own_request(stub_iam):
    pk = _validated(creator=APPROVER).pk
    c = _as(stub_iam, APPROVER, "iaa.request.create", "iaa.request.decide")
    r = c.post(f"{URL}/{pk}/decide", {"decision": "approve", "remarks": "Fine"},
               format="json")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "segregation_of_duties"


@pytest.mark.django_db
def test_decision_without_remarks_is_refused(stub_iam):
    pk = _validated().pk
    c = _as(stub_iam, APPROVER, "iaa.request.decide")
    r = c.post(f"{URL}/{pk}/decide", {"decision": "approve"}, format="json")
    assert (r.status_code, r.json()["error"]["code"]) == (422, "remarks_required")


@pytest.mark.django_db
def test_users_do_not_see_each_others_requests(stub_iam):
    pk = ExpenseRequest.objects.create(creator_user_id=CREATOR, **COMPLETE).pk
    c = _as(stub_iam, OTHER, "iaa.request.create")
    assert c.get(URL).json()["results"] == []
    assert c.get(f"{URL}/{pk}").status_code == 404
