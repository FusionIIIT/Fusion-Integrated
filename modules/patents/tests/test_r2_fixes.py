"""Tests for review round 2 findings (R2-03, R2-04, R2-05)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from modules.accesscontrol.management.commands.permission_manifest import collect
from modules.patents.domain import permissions as p
from modules.patents.domain import state_machine as sm
from modules.patents.models import PatentApplication
from modules.patents.selectors import scoping
from modules.patents.services import applications as app_service

pytestmark = pytest.mark.django_db


def test_dual_role_user_gets_only_the_acting_role_view():
    """R2-03: a principal acting as student does not get pcc_admin access."""
    dual = make_principal(
        user_id=1, kind="student", roles=("student", "pcc_admin"), active_role="student",
        modules=("patents",), permissions=(),
    )
    assert scoping.is_pcc_admin(dual) is False
    assert scoping.is_applicant(dual) is True

    as_admin = make_principal(
        user_id=1, kind="student", roles=("student", "pcc_admin"), active_role="pcc_admin",
        modules=("patents",), permissions=(),
    )
    assert scoping.is_pcc_admin(as_admin) is True


def test_withdraw_on_granted_application_is_refused_with_409(stub_iam):
    """R2-04: a state conflict returns 409, and the record is unchanged."""
    stub_iam(
        make_session(
            user_id=101, kind="student", roles=("student",), active_role="student",
            modules=("patents",), permissions=(p.P_APPLICATION_WITHDRAW, p.P_APPLICATION_VIEW_SELF),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    applicant = make_principal(
        user_id=101, kind="student", roles=("student",), active_role="student",
        modules=("patents",),
        permissions=(p.P_APPLICATION_CREATE, p.P_APPLICATION_VIEW_SELF),
    )
    app = app_service.create_application(
        actor=applicant, title="T", abstract="A", description="D", claims="C",
        domain_category="Computer Science", jurisdiction="IN",
    )
    PatentApplication.objects.filter(pk=app.pk).update(status=sm.GRANTED)

    resp = client.post(
        f"/api/v1/patents/applications/{app.id}/withdraw", {"reason": "changed mind"}, format="json",
    )
    assert resp.status_code == status.HTTP_409_CONFLICT
    app.refresh_from_db()
    assert app.status == sm.GRANTED


def test_permission_registry_matches_committed_manifest():
    """R2-05: the module's declared permissions match registry/permissions.json."""
    committed = json.loads(Path(settings.BASE_DIR, "registry", "permissions.json").read_text())
    current = collect()
    assert current == committed, "registry/permissions.json is stale; run `make permissions`"
    assert "patents" in committed["modules"]


def test_mutating_endpoint_is_refused_with_429_when_throttled(monkeypatch):
    """R2-04: a write endpoint refuses with 429 once its scope's rate is used up."""
    from types import SimpleNamespace

    from core.api.throttling import PrincipalScopedThrottle
    from modules.patents.api import views as v

    scope = v.ApplicationConsentView.throttle_scope
    assert scope == "patent_mutate"
    monkeypatch.setitem(PrincipalScopedThrottle.THROTTLE_RATES, scope, "2/minute")
    user_id = 990_001
    request = SimpleNamespace(principal=SimpleNamespace(kind="student", user_id=user_id), META={})
    throttle = PrincipalScopedThrottle()
    throttle.scope = scope
    throttle.rate = "2/minute"
    throttle.num_requests, throttle.duration = 2, 60
    throttle.cache_format = "throttle_%(scope)s_%(ident)s"
    from django.core.cache import cache

    cache.delete(throttle.cache_format % {"scope": scope, "ident": f"user:{user_id}"})
    results = [throttle.allow_request(request, v.ApplicationConsentView()) for _ in range(3)]
    assert results == [True, True, False]


def test_director_review_default_is_pinned():
    """Step 5.15 mutation check: the 15-day Director review default is asserted by a test."""
    from modules.patents.domain import deadlines as dl

    assert dl.DEFAULT_REVIEW_DAYS == 15
    assert dl.DEFAULT_REVISION_DAYS == 60
