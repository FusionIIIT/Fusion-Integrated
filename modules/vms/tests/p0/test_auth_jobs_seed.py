"""Visitor session auth, jobs merger, contracts stub, seed_vms."""
import types
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.request import Request

from core.api import csrf
from modules.vms import auth, contracts, schedule
from modules.vms.models import AccessPolicy, BlacklistVersion, Gate, Zone
from modules.vms.tests import factories as f

# --- VisitorSessionAuthentication ----------------------------------------------------

RAW = "visitor-token-123"


def _request(method="get", cookie=RAW, csrf_token=None):
    rf = RequestFactory()
    extra = {"HTTP_X_CSRF_TOKEN": csrf_token} if csrf_token else {}
    req = getattr(rf, method)("/api/v1/vms/x", **extra)
    if cookie is not None:
        req.COOKIES[auth.COOKIE_NAME] = cookie
    return Request(req)


def _session(**kw):
    return f.make_visitor_session(
        token_hash=auth.hash_token(RAW), verified_at=timezone.now(), **kw)


@pytest.mark.django_db
def test_valid_cookie_sets_request_visitor_and_principal():
    s = _session()
    req = _request()
    principal, token = auth.VisitorSessionAuthentication().authenticate(req)
    assert principal.visitor_id == s.visitor_id and token == RAW
    assert req.visitor == s.visitor
    assert auth.IsVisitorSession().has_permission(req, None) is True


@pytest.mark.django_db
def test_no_cookie_is_anonymous():
    assert auth.VisitorSessionAuthentication().authenticate(_request(cookie=None)) is None


@pytest.mark.django_db
def test_unknown_token_is_rejected():
    _session()
    with pytest.raises(AuthenticationFailed):
        auth.VisitorSessionAuthentication().authenticate(_request(cookie="other"))


@pytest.mark.django_db
def test_unverified_session_is_rejected():
    f.make_visitor_session(token_hash=auth.hash_token(RAW), verified_at=None)
    with pytest.raises(AuthenticationFailed):
        auth.VisitorSessionAuthentication().authenticate(_request())


@pytest.mark.django_db
def test_expired_session_is_rejected():
    _session(expires_at=timezone.now() - timedelta(seconds=1))
    with pytest.raises(AuthenticationFailed):
        auth.VisitorSessionAuthentication().authenticate(_request())


@pytest.mark.django_db
def test_the_raw_token_is_never_stored():
    s = _session()
    assert RAW not in s.token_hash and len(s.token_hash) == 64


@pytest.mark.django_db
def test_unsafe_method_needs_the_csrf_token():
    _session()
    with pytest.raises(PermissionDenied):
        auth.VisitorSessionAuthentication().authenticate(_request("post"))
    ok = _request("post", csrf_token=csrf.token_for(RAW))
    assert auth.VisitorSessionAuthentication().authenticate(ok)


def test_visitor_principal_holds_no_iam_permission():
    p = auth.VisitorPrincipal(visitor_id=1, email="", display_name="v")
    assert not p.has_permission("vms.request.decide") and not p.has_module("vms")
    assert not hasattr(p, "user_id")


def test_is_visitor_session_denies_an_iam_principal():
    req = types.SimpleNamespace(principal=f.make_actor())
    assert auth.IsVisitorSession().has_permission(req, None) is False


# --- jobs merger ---------------------------------------------------------------------

def _mod(name, routes=None, beat=None):
    return types.SimpleNamespace(__name__=name, TASK_ROUTES=routes or {},
                                 BEAT_SCHEDULE=beat or {})


def test_merge_combines_every_jobs_module():
    routes, beat = schedule.merge([
        _mod("a", {"vms.a": {"queue": "x"}}, {"a-entry": {"task": "vms.a"}}),
        _mod("b", {"vms.b": {"queue": "y"}}, {"b-entry": {"task": "vms.b"}}),
        types.SimpleNamespace(__name__="empty"),
    ])
    assert set(routes) == {"vms.a", "vms.b"} and set(beat) == {"a-entry", "b-entry"}


def test_merge_refuses_a_duplicate_key():
    with pytest.raises(RuntimeError):
        schedule.merge([_mod("a", beat={"k": {}}), _mod("b", beat={"k": {}})])


def test_job_modules_discovers_the_package(tmp_path, monkeypatch):
    import sys

    from modules.vms import jobs
    (tmp_path / "zz_probe.py").write_text(
        "TASK_ROUTES = {'vms.probe': {'queue': 'q'}}\n"
        "BEAT_SCHEDULE = {'probe': {'task': 'vms.probe', 'schedule': 5.0}}\n")
    monkeypatch.setattr(jobs, "__path__", [*jobs.__path__, str(tmp_path)])
    try:
        routes, beat = schedule.merge(schedule.job_modules())
    finally:
        sys.modules.pop("modules.vms.jobs.zz_probe", None)
    assert "vms.probe" in routes and "probe" in beat


def test_celery_app_includes_the_vms_dicts():
    from config.celery import app
    assert set(schedule.BEAT_SCHEDULE) <= set(app.conf.beat_schedule)
    assert set(schedule.TASK_ROUTES) <= set(app.conf.task_routes)


def test_tasks_module_imports():
    import modules.vms.tasks as tasks
    assert isinstance(tasks.JOB_MODULES, list)


# --- contracts -----------------------------------------------------------------------

def test_get_visit_status_is_plural_and_a_stub():
    import inspect
    assert "Sequence" in str(inspect.signature(contracts.get_visit_status))
    assert contracts.get_visit_status([1, 2]) == {}


# --- seed_vms ------------------------------------------------------------------------

@pytest.mark.django_db
def test_seed_vms_creates_reference_data():
    call_command("seed_vms")
    assert set(Zone.objects.values_list("name", flat=True)) >= {"Lobby", "Academic block", "Hostel"}
    assert Zone.objects.get(name="Hostel").is_restricted
    assert not Zone.objects.get(name="Lobby").is_restricted
    assert Gate.objects.count() == 2
    p = AccessPolicy.objects.get(status="published")
    assert (p.version, p.max_visit_hours, p.walk_in_pass_hours,
            p.approval_timeout_hours, p.advance_registration_hours) == (1, 8, 4, 24, 2)
    assert p.restricted_zones.filter(name="Hostel").exists()
    bv = BlacklistVersion.objects.get(status="published")
    assert bv.version == 1 and not bv.entries.exists()


@pytest.mark.django_db
def test_seed_vms_is_idempotent():
    call_command("seed_vms")
    call_command("seed_vms")
    assert Zone.objects.count() == 3 and Gate.objects.count() == 2
    assert AccessPolicy.objects.count() == 1 and BlacklistVersion.objects.count() == 1
