"""Schema-level tests: factories build valid rows, constraints bite,
append-only tables refuse updates."""
import inspect
import uuid
from datetime import timedelta

import pytest
from django.apps import apps
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.vms import models as m
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


def _factories():
    return {n: fn for n, fn in inspect.getmembers(f, inspect.isfunction)
            if n.startswith("make_") and fn.__module__ == f.__name__}


def test_every_model_has_a_factory():
    names = {fn.__name__.removeprefix("make_").replace("_", "")
             for fn in _factories().values()}
    missing = [mod.__name__ for mod in apps.get_app_config("vms").get_models()
               if mod.__name__.lower() not in names]
    assert not missing, missing


@pytest.mark.parametrize("name", sorted(
    n for n in _factories() if n != "make_actor"))
def test_factory_builds_a_row(name):
    assert _factories()[name]().pk


def test_make_actor_builds_principal():
    p = f.make_actor("staff", ["host"], ["vms.request.decide"])
    assert p.has_permission("vms.request.decide") and p.has_module("vms")


def test_awaiting_admin_status_is_valid():
    assert f.make_visit_request(status="awaiting_admin").pk


def test_bad_request_status_rejected():
    with pytest.raises(IntegrityError), transaction.atomic():
        f.make_visit_request(status="cancelled")   # D-4: not modelled


def test_bad_severity_rejected():
    with pytest.raises(IntegrityError), transaction.atomic():
        f.make_blacklist_entry(severity="extreme")


def test_role_assignment_scope_and_window_checks():
    with pytest.raises(IntegrityError), transaction.atomic():
        f.make_role_assignment(scope_type="zone", scope_id=None)
    now = timezone.now()
    with pytest.raises(IntegrityError), transaction.atomic():
        f.make_role_assignment(starts_at=now, ends_at=now - timedelta(hours=1))


def test_preauth_used_cannot_exceed_max():
    with pytest.raises(IntegrityError), transaction.atomic():
        f.make_pre_authorization(max_visits=1, used_visits=2)


def test_qr_token_unique():
    p = f.make_visit_pass()
    with pytest.raises(IntegrityError), transaction.atomic():
        f.make_visit_pass(qr_token=p.qr_token)


def test_client_event_id_unique_but_null_repeatable():
    f.make_visit_log()
    f.make_visit_log()                      # two NULLs allowed
    cid = uuid.uuid4()
    f.make_visit_log(client_event_id=cid)
    with pytest.raises(IntegrityError), transaction.atomic():
        f.make_visit_log(client_event_id=cid)


def test_notification_dedupe_key_unique():
    n = f.make_notification()
    with pytest.raises(IntegrityError), transaction.atomic():
        f.make_notification(dedupe_key=n.dedupe_key)


def test_muster_entry_unique_per_pass():
    e = f.make_muster_entry()
    with pytest.raises(IntegrityError), transaction.atomic():
        f.make_muster_entry(muster=e.muster, visit_pass=e.visit_pass)


@pytest.mark.parametrize("make", [f.make_visit_log, f.make_audit_log])
def test_append_only_rejects_update_and_delete(make):
    row = make()
    with pytest.raises(m.AppendOnlyError):
        row.save()
    with pytest.raises(m.AppendOnlyError):
        row.delete()


def test_policy_defaults():
    p = f.make_access_policy()
    assert (p.advance_registration_hours, p.contingency_sla_minutes) == (2, 15)
    assert p.visiting_hours_start < p.visiting_hours_end


def test_only_one_open_muster_in_the_database():
    f.make_emergency_muster(status="open")
    with pytest.raises(IntegrityError), transaction.atomic():
        f.make_emergency_muster(status="open")
    f.make_emergency_muster(status="closed")
    f.make_emergency_muster(status="closed")
