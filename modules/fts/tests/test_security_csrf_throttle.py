"""Security, CSRF, Throttling, and Permission Registry verification for FTS.

Validates CFR-FTS-01, CFR-FTS-02, BR-FTS-006, BR-FTS-010, AFR-FTS-011.
"""
from __future__ import annotations

import pytest
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient

from core.api import csrf
from modules.fts.registry import PERMISSIONS, ROLE_GRANTS, SYSTEM_PERMISSIONS
from modules.fts.tests.conftest import make_fts_session

pytestmark = pytest.mark.django_db
COOKIE_NAME = settings.IAM_AUTH_COOKIE_NAME


def test_cookie_write_without_csrf_token_is_refused(stub_iam):
    """AFR-FTS-011: Cookie-authenticated write without X-CSRF-Token returns 403."""
    session = make_fts_session(
        user_id=101,
        kind="faculty",
        roles=("faculty",),
        active_role="Professor",
        permissions=("fts.file.create",),
    )
    stub_iam(session)

    client = APIClient()
    client.cookies[COOKIE_NAME] = "session-tok-123"

    payload = {
        "subject": "Proposal without CSRF",
        "comment": "Initial note.",
        "is_draft": True,
    }
    # Attempt write without CSRF token header
    res = client.post("/api/v1/fts/files/", payload, format="json")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_cookie_write_with_valid_csrf_token_is_allowed(stub_iam):
    """AFR-FTS-011: Cookie-authenticated write with valid X-CSRF-Token is accepted."""
    session = make_fts_session(
        user_id=101,
        kind="faculty",
        roles=("faculty",),
        active_role="Professor",
        permissions=("fts.file.create",),
    )
    stub_iam(session)

    client = APIClient()
    client.cookies[COOKIE_NAME] = "session-tok-123"
    token = csrf.token_for("session-tok-123")

    payload = {
        "subject": "Proposal with CSRF",
        "comment": "Initial note.",
        "is_draft": True,
    }
    res = client.post(
        "/api/v1/fts/files/",
        payload,
        format="json",
        HTTP_X_CSRF_TOKEN=token,
    )
    assert res.status_code == status.HTTP_201_CREATED


def test_create_file_throttling_refusal_answers_429(fts_client, monkeypatch):
    """CFR-FTS-01: Exceeding write rate limits triggers HTTP 429 Too Many Requests."""
    from django.core.cache import cache
    from rest_framework.settings import api_settings
    cache.clear()

    monkeypatch.setitem(api_settings.DEFAULT_THROTTLE_RATES, "fts_file_create", "2/min")

    client = fts_client(user_id=201)
    payload = {
        "subject": "Rate Limited File",
        "comment": "Initial note.",
        "is_draft": True,
    }

    # First request: OK
    r1 = client.post("/api/v1/fts/files/", payload, format="json")
    assert r1.status_code == status.HTTP_201_CREATED

    # Second request: OK
    r2 = client.post("/api/v1/fts/files/", payload, format="json")
    assert r2.status_code == status.HTTP_201_CREATED

    # Third request: Throttled -> 429
    r3 = client.post("/api/v1/fts/files/", payload, format="json")
    assert r3.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_permission_codes_do_not_drift():
    """Verify that every permission used in tests and grants matches registry declarations."""
    declared = {code for code, _ in PERMISSIONS} | set(SYSTEM_PERMISSIONS)
    granted = {code for codes in ROLE_GRANTS.values() for code in codes}

    # All granted codes must be declared
    for code in granted:
        assert code in declared, f"Granted permission {code} is not in registry.PERMISSIONS"

    # Known permissions used in FTS test suite fixtures
    test_fixture_codes = {
        "fts.file.create",
        "fts.file.forward",
        "fts.file.return",
        "fts.file.archive",
        "fts.file.view",
        "fts.governance.view",
        "fts.integration.access",
        "fts.notification.dispatch",
    }
    for code in test_fixture_codes:
        assert code in declared, f"Test fixture code {code} is not in registry.PERMISSIONS"
