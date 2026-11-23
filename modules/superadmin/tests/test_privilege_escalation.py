"""Every write endpoint returns 403 for a principal without the required permission."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.superadmin.domain.constants import (
    ARCHIVAL_STATUS_REVERSIBLE,
    PURGE_STATUS_APPROVED,
    PURGE_STATUS_PENDING_IT_HEAD,
)
from modules.superadmin.models.archival import (
    ArchivedUserRecord,
    HistoricalDataArchive,
    PurgeRequest,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, permissions, uid=999):
    stub_iam(
        make_session(
            user_id=uid,
            kind="staff",
            permissions=permissions,
            modules=("superadmin",),
            active_role="student",
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _archived_user(uid=5000):
    return ArchivedUserRecord.objects.create(
        user_id=uid,
        institute_id="2020BCS001",
        username=f"u{uid}",
        email=f"u{uid}@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=5),
        reversible_until=timezone.now() + timedelta(days=25),
        authorized_by=1,
        archival_reason="Test.",
    )


def _archive():
    today = date.today()
    return HistoricalDataArchive.objects.create(
        dataset_category="academics",
        title="Old dataset",
        date_range_start=today - timedelta(days=800),
        date_range_end=today - timedelta(days=400),
        record_count=100,
        backup_file_path="/b/x.tar.gz",
        backup_checksum="abc",
        retention_expires_at=today - timedelta(days=10),
        archived_by=1,
    )


# -- Dashboard (view only) ------------------------------------------------


def test_dashboard_requires_view_permission(stub_iam):
    client = _client(stub_iam, permissions=())
    assert client.get("/api/v1/superadmin/dashboard/").status_code == 403


# -- Archival: add requires superadmin.archival.add -----------------------


def test_archive_user_requires_add_permission(stub_iam):
    # Has view but not add
    client = _client(stub_iam, ("superadmin.archival.view",))
    response = client.post(
        "/api/v1/superadmin/archival/users/",
        {
            "user_id": 7001,
            "institute_id": "2021BCS001",
            "username": "u7001",
            "email": "u7001@iiitdmj.ac.in",
            "user_kind": "student",
            "is_deactivated": True,
            "deactivated_at": "2026-01-01T00:00:00Z",
            "has_pending_transactions": False,
            "archival_reason": "Graduated.",
        },
        format="json",
    )
    assert response.status_code == 403


def test_restore_user_requires_change_permission(stub_iam):
    record = _archived_user(5001)
    # Has view but not change
    client = _client(stub_iam, ("superadmin.archival.view",))
    response = client.post(
        f"/api/v1/superadmin/archival/users/{record.user_id}/restore/",
        {"restoration_reason": "Rejoining."},
        format="json",
    )
    assert response.status_code == 403


def test_archived_user_detail_requires_view_permission(stub_iam):
    """R1-01: ArchivedUserDetailView returns 403 when caller lacks superadmin.archival.view."""
    record = _archived_user(5002)
    # Principal has module grant and audit.view, but lacks archival.view
    client = _client(stub_iam, ("superadmin.audit.view",))
    response = client.get(f"/api/v1/superadmin/archival/users/{record.user_id}/")
    assert response.status_code == 403


# -- Purge: initiate requires superadmin.purge.add ------------------------


def test_create_purge_request_requires_add_permission(stub_iam):
    archive = _archive()
    client = _client(stub_iam, ("superadmin.purge.view",))
    response = client.post(
        "/api/v1/superadmin/purge/requests/",
        {
            "archive_id": archive.pk,
            "request_reason": "Retention lapsed.",
        },
        format="json",
    )
    assert response.status_code == 403


# -- Purge: authorize requires superadmin.purge.change --------------------


def test_decide_purge_requires_change_permission(stub_iam):
    archive = _archive()
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=1,
        request_reason="Need decision.",
    )
    # Has view and add but not change
    client = _client(stub_iam, ("superadmin.purge.view", "superadmin.purge.add"))
    response = client.post(
        f"/api/v1/superadmin/purge/requests/{req.pk}/decision/",
        {"approve": True, "comments": ""},
        format="json",
    )
    assert response.status_code == 403


# -- Purge: execute requires superadmin.purge.add -------------------------


def test_execute_purge_requires_add_permission(stub_iam):
    archive = _archive()
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_APPROVED,
        requested_by=1,
        request_reason="Approved.",
        it_head_id=200,
        it_head_decision_at=timezone.now(),
    )
    client = _client(stub_iam, ("superadmin.purge.view",))
    response = client.post(
        f"/api/v1/superadmin/purge/requests/{req.pk}/execute/",
        {},
        format="json",
    )
    assert response.status_code == 403


# -- Policy: change requires superadmin.policy.change --------------------


def test_supersede_policy_requires_change_permission(stub_iam):
    client = _client(stub_iam, ("superadmin.policy.view",))
    response = client.post(
        "/api/v1/superadmin/policy/parameters/",
        {
            "key": "archival.reversibility_window_days",
            "value": "45",
        },
        format="json",
    )
    assert response.status_code == 403


# -- Audit: view requires superadmin.audit.view ---------------------------


def test_audit_log_list_requires_view_permission(stub_iam):
    client = _client(stub_iam, permissions=())
    assert client.get("/api/v1/superadmin/audit/logs/").status_code == 403


# -- IT Head cannot initiate purge (no purge.add) -------------------------


def test_it_head_cannot_initiate_purge(stub_iam):
    from modules.superadmin.tests.conftest import IT_PERMS

    archive = _archive()
    client = _client(stub_iam, IT_PERMS, uid=200)
    response = client.post(
        "/api/v1/superadmin/purge/requests/",
        {
            "archive_id": archive.pk,
            "request_reason": "IT Head attempting initiate.",
        },
        format="json",
    )
    # IT Head lacks purge.add — should be 403
    assert response.status_code == 403


# -- CSRF enforcement on cookie-borne sessions ----------------------------


def test_cookie_authenticated_write_without_csrf_token_returns_403(stub_iam):
    """R1-05: Cookie-authenticated state-changing POST without X-CSRF-Token returns 403."""
    from django.conf import settings

    from modules.superadmin.tests.conftest import SA_PERMS

    stub_iam(
        make_session(
            user_id=100,
            kind="staff",
            roles=("super_admin",),
            active_role="super_admin",
            permissions=SA_PERMS,
            modules=("superadmin",),
        )
    )
    client = APIClient(enforce_csrf_checks=True)
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = "session-tok-superadmin"
    response = client.post(
        "/api/v1/superadmin/policy/parameters/",
        {
            "key": "archival.reversibility_window_days",
            "value": "45",
        },
        format="json",
    )
    assert response.status_code == 403


# -- Throttling rate limit enforcement ------------------------------------


def test_write_endpoint_throttled_returns_429(stub_iam):
    """R2-01: Exercising a throttled write endpoint beyond its rate returns HTTP 429."""
    from django.conf import settings
    from django.core.cache import cache
    from django.test import override_settings
    from rest_framework.settings import api_settings
    from rest_framework.throttling import SimpleRateThrottle

    from modules.superadmin.tests.conftest import SA_PERMS

    cache.clear()
    orig_rates = SimpleRateThrottle.THROTTLE_RATES
    try:
        client = _client(stub_iam, SA_PERMS, uid=100)
        with override_settings(
            REST_FRAMEWORK={
                **settings.REST_FRAMEWORK,
                "DEFAULT_THROTTLE_RATES": {
                    **settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
                    "superadmin_write": "1/min",
                },
            }
        ):
            SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
            payload = {
                "key": "archival.reversibility_window_days",
                "value": "45",
                "description": "Test throttle",
            }
            resp1 = client.post(
                "/api/v1/superadmin/policy/parameters/",
                payload,
                format="json",
            )
            assert resp1.status_code in (200, 201)

            resp2 = client.post(
                "/api/v1/superadmin/policy/parameters/",
                payload,
                format="json",
            )
            assert resp2.status_code == 429
    finally:
        SimpleRateThrottle.THROTTLE_RATES = orig_rates
        cache.clear()


# -- Comprehensive Audit: Every endpoint refuses callers without module grant
#    and callers with module grant but lacking the specific permission --------


ALL_ENDPOINTS = [
    ("get", "/api/v1/superadmin/dashboard/", None, "superadmin.dashboard.view"),
    ("get", "/api/v1/superadmin/archival/users/", None, "superadmin.archival.view"),
    (
        "post",
        "/api/v1/superadmin/archival/users/",
        {"user_id": 9999, "username": "u9999"},
        "superadmin.archival.add",
    ),
    (
        "get",
        "/api/v1/superadmin/archival/users/{user_id}/",
        None,
        "superadmin.archival.view",
    ),
    (
        "post",
        "/api/v1/superadmin/archival/users/{user_id}/restore/",
        {"restoration_reason": "r"},
        "superadmin.archival.change",
    ),
    ("get", "/api/v1/superadmin/archival/history/", None, "superadmin.archival.view"),
    ("post", "/api/v1/superadmin/archival/history/", {"title": "t"}, "superadmin.archival.add"),
    (
        "post",
        "/api/v1/superadmin/archival/history/{archive_id}/restore/",
        {},
        "superadmin.archival.change",
    ),
    ("get", "/api/v1/superadmin/purge/requests/", None, "superadmin.purge.view"),
    (
        "post",
        "/api/v1/superadmin/purge/requests/",
        {"archive_id": 1, "request_reason": "r"},
        "superadmin.purge.add",
    ),
    (
        "post",
        "/api/v1/superadmin/purge/requests/{pending_purge_id}/decision/",
        {"approve": True},
        "superadmin.purge.change",
    ),
    (
        "post",
        "/api/v1/superadmin/purge/requests/{approved_purge_id}/execute/",
        {},
        "superadmin.purge.add",
    ),
    ("get", "/api/v1/superadmin/policy/parameters/", None, "superadmin.policy.view"),
    (
        "post",
        "/api/v1/superadmin/policy/parameters/",
        {"key": "k", "value": "v"},
        "superadmin.policy.change",
    ),
    ("get", "/api/v1/superadmin/audit/logs/", None, "superadmin.audit.view"),
    ("get", "/api/v1/superadmin/audit/export/", None, "superadmin.audit.view"),
]


def _endpoint_fixtures():
    u = _archived_user(5050)
    a = _archive()
    p_pending = PurgeRequest.objects.create(
        archive=a,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=1,
        request_reason="Need decision.",
    )
    p_approved = PurgeRequest.objects.create(
        archive=a,
        status=PURGE_STATUS_APPROVED,
        requested_by=1,
        request_reason="Approved.",
        it_head_id=200,
        it_head_decision_at=timezone.now(),
    )
    return {
        "user_id": u.user_id,
        "archive_id": a.pk,
        "pending_purge_id": p_pending.pk,
        "approved_purge_id": p_approved.pk,
    }


@pytest.mark.parametrize("method,path_template,payload,required_perm", ALL_ENDPOINTS)
def test_all_endpoints_refuse_caller_without_module_grant(
    stub_iam, method, path_template, payload, required_perm
):
    """(a) Every endpoint returns 403 when caller lacks the superadmin module grant."""
    fix = _endpoint_fixtures()
    path = path_template.format(**fix)
    stub_iam(
        make_session(
            user_id=998,
            kind="staff",
            permissions=(required_perm,),
            modules=(),
            active_role="student",
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    resp = (
        client.get(path)
        if method == "get"
        else client.post(path, payload or {}, format="json")
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("method,path_template,payload,required_perm", ALL_ENDPOINTS)
def test_all_endpoints_refuse_caller_lacking_specific_permission(
    stub_iam, method, path_template, payload, required_perm
):
    """(b) Every endpoint returns 403 when caller has superadmin module grant but lacks the specific permission."""
    fix = _endpoint_fixtures()
    path = path_template.format(**fix)
    unrelated_perm = (
        "superadmin.audit.view" if "audit" not in required_perm else "superadmin.dashboard.view"
    )
    stub_iam(
        make_session(
            user_id=999,
            kind="staff",
            permissions=(unrelated_perm,),
            modules=("superadmin",),
            active_role="student",
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    resp = (
        client.get(path)
        if method == "get"
        else client.post(path, payload or {}, format="json")
    )
    assert resp.status_code == 403
