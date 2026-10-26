from datetime import date
from types import SimpleNamespace

import pytest
from rest_framework.test import APIRequestFactory

from modules.elm.api import views
from modules.elm.services.entitlements import credit_annual_entitlements

ALL = ("elm.leave.apply", "elm.leave.view_self", "elm.leave.withdraw")


def _call(view, method, user_id=1, codes=ALL, data=None, with_principal=True, **kwargs):
    request = getattr(APIRequestFactory(), method)("/x/", data, format="json")
    if with_principal:
        request.principal = SimpleNamespace(
            user_id=user_id, kind="staff",
            has_any_permission=lambda *wanted: any(c in codes for c in wanted))
    return view(request, **kwargs)


def _apply(user_id=1, **overrides):
    body = {"category": "CL", "start_date": "2026-10-26", "end_date": "2026-10-27",
            "reason": "family"}
    body.update(overrides)
    return _call(views.LeaveRequestListView.as_view(), "post", user_id=user_id, data=body)


@pytest.mark.django_db
def test_apply_without_principal_is_refused():
    resp = _call(views.LeaveRequestListView.as_view(), "post", with_principal=False, data={})
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_apply_without_permission_is_forbidden():
    resp = _call(views.LeaveRequestListView.as_view(), "post", codes=(), data={})
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_apply_creates_request():
    credit_annual_entitlements(1, 2026, is_faculty=False)
    resp = _apply()
    assert resp.status_code == 201
    assert resp.data["status"] == "Awaiting Unit Head Review"
    assert resp.data["category"] == "CL"


@pytest.mark.django_db
def test_apply_rejects_unknown_category_with_400():
    assert _apply(category="annual").status_code == 400


@pytest.mark.django_db
def test_apply_without_balance_is_a_client_error():
    resp = _apply()
    assert 400 <= resp.status_code < 500


@pytest.mark.django_db
def test_list_shows_only_own_requests():
    credit_annual_entitlements(1, 2026, is_faculty=False)
    credit_annual_entitlements(2, 2026, is_faculty=False)
    _apply(user_id=1)
    _apply(user_id=2)
    resp = _call(views.LeaveRequestListView.as_view(), "get", user_id=1)
    assert resp.status_code == 200
    assert len(resp.data) == 1


@pytest.mark.django_db
def test_other_users_request_is_404_not_403():
    credit_annual_entitlements(1, 2026, is_faculty=False)
    pk = _apply(user_id=1).data["id"]
    resp = _call(views.LeaveRequestDetailView.as_view(), "get", user_id=2, pk=pk)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_withdraw_own_request():
    credit_annual_entitlements(1, 2026, is_faculty=False)
    pk = _apply(user_id=1).data["id"]
    resp = _call(views.LeaveRequestWithdrawView.as_view(), "post", user_id=1, pk=pk)
    assert resp.status_code == 200
    assert resp.data["status"] == "Withdrawn"


@pytest.mark.django_db
def test_withdraw_other_users_request_is_404():
    credit_annual_entitlements(1, 2026, is_faculty=False)
    pk = _apply(user_id=1).data["id"]
    resp = _call(views.LeaveRequestWithdrawView.as_view(), "post", user_id=2, pk=pk)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_balance_bad_year_is_400():
    req = APIRequestFactory().get("/x/", {"year": "abc"})
    req.principal = SimpleNamespace(user_id=1, kind="staff",
                                    has_any_permission=lambda *w: True)
    assert views.BalanceView.as_view()(req).status_code == 400


@pytest.mark.django_db
def test_balance_lists_every_category():
    credit_annual_entitlements(1, 2026, is_faculty=False)
    req = APIRequestFactory().get("/x/", {"year": "2026"})
    req.principal = SimpleNamespace(user_id=1, kind="staff",
                                    has_any_permission=lambda *w: True)
    resp = views.BalanceView.as_view()(req)
    assert resp.status_code == 200
    assert {r["category"]: r["amount"] for r in resp.data}["CL"] in ("8", "8.00")

