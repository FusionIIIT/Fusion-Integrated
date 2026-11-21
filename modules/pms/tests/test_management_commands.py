"""PMS readiness and manual-task commands report their effects clearly."""

from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from modules.pms import registry


def test_readiness_names_unavailable_integrations():
    output = StringIO()
    with pytest.raises(CommandError, match="3 PMS prerequisite"):
        call_command("pms_readiness", stdout=output)
    rendered = output.getvalue()
    assert "IAM-owned Director-domain assignment projection" in rendered
    assert "trusted malware scanner and private binary-storage path" in rendered
    assert "supported external prior-art source" in rendered


def test_seed_command_only_creates_missing_specification_defaults(monkeypatch):
    from modules.pms.management.commands import seed_pms_configuration

    created = []
    existing = set()

    def get_or_create(*, key, defaults):
        was_created = key not in existing
        existing.add(key)
        if was_created:
            created.append((key, defaults["value"]))
        return SimpleNamespace(key=key), was_created

    monkeypatch.setattr(
        seed_pms_configuration.PmsConfiguration.objects,
        "get_or_create",
        get_or_create,
    )
    output = StringIO()
    call_command("seed_pms_configuration", stdout=output)
    second_output = StringIO()
    call_command("seed_pms_configuration", stdout=second_output)
    assert created == [
        ("review_business_days", 15),
        ("revision_days", 60),
        ("alert_offsets", [30, 15, 5]),
    ]
    assert "Created 3 missing" in output.getvalue()
    assert second_output.getvalue().strip() == "Created 0 missing PMS policy value(s)."


def test_deadline_command_runs_task_synchronously(monkeypatch):
    from modules.pms.management.commands import run_pms_deadlines

    monkeypatch.setattr(
        run_pms_deadlines.monitor_deadlines,
        "run",
        lambda: {"alerts_sent": 2, "escalations": 1},
    )
    output = StringIO()
    call_command("run_pms_deadlines", stdout=output)
    assert output.getvalue().strip() == "alerts_sent=2 escalations=1"


def test_notification_command_runs_task_with_limit(monkeypatch):
    from modules.pms.management.commands import run_pms_notifications

    calls = []
    monkeypatch.setattr(
        run_pms_notifications.deliver_notifications,
        "run",
        lambda **kwargs: calls.append(kwargs) or 4,
    )
    output = StringIO()
    call_command("run_pms_notifications", "--limit", "12", stdout=output)
    assert calls == [{"limit": 12}]
    assert output.getvalue().strip() == "sent=4"


def test_readiness_registry_lists_unmet_prerequisites():
    assert len(registry.readiness()) == 3
