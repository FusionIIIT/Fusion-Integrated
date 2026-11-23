"""Tests for superadmin management commands."""

from __future__ import annotations

import io

import pytest
from django.core.management import call_command

from modules.superadmin.domain.constants import CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS
from modules.superadmin.models.config import SystemPolicyParameter

pytestmark = pytest.mark.django_db


def test_seed_superadmin_policy_command():
    out = io.StringIO()
    call_command("seed_superadmin_policy", stdout=out)
    output = out.getvalue()
    assert "seeded" in output

    # Idempotent re-run
    out_second = io.StringIO()
    call_command("seed_superadmin_policy", stdout=out_second)
    second_output = out_second.getvalue()
    assert "skip" in second_output

    assert SystemPolicyParameter.objects.filter(key=CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS).exists()


def test_run_archival_sweep_command():
    out = io.StringIO()
    call_command("run_archival_sweep", stdout=out)
    assert "Done:" in out.getvalue()


def test_run_purge_sweep_command():
    out = io.StringIO()
    call_command("run_purge_sweep", stdout=out)
    assert "Done:" in out.getvalue()
