"""Tests for RSPC management commands and registry readiness checks."""

from __future__ import annotations

import io

import pytest
from django.core.management import call_command

from modules.rspc import registry


@pytest.mark.django_db
def test_management_commands_output(monkeypatch):
    out_check = io.StringIO()
    call_command("rspc_check_deadlines", stdout=out_check)
    assert "checked deadlines: 0 project(s)" in out_check.getvalue()

    out_ready = io.StringIO()
    call_command("rspc_readiness", stdout=out_ready)
    assert "RSPC module is ready" in out_ready.getvalue()

    # Unmet readiness branch exiting 1
    from modules.rspc.management.commands import rspc_readiness

    monkeypatch.setattr(rspc_readiness, "readiness", lambda: ["Database issue detected"])
    out_err = io.StringIO()
    with pytest.raises(SystemExit):
        call_command("rspc_readiness", stdout=out_err)


def test_registry_readiness_error_branches(monkeypatch):
    """Verify registry.readiness fails closed when tables or beat schedules are missing."""
    from django.db import connection

    monkeypatch.setattr(connection.introspection, "table_names", list)
    unmet = registry.readiness()
    assert any("Database tables missing" in u for u in unmet)

    import config.celery

    fake_app = type("FakeCeleryApp", (), {"conf": type("FakeConf", (), {"beat_schedule": {}})()})()
    monkeypatch.setattr(config.celery, "app", fake_app)
    unmet2 = registry.readiness()
    assert any("Celery beat schedule missing" in u for u in unmet2)
