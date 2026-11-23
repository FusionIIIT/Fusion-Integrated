"""Tests for patents management commands (Step 4.8)."""
from __future__ import annotations

import io

import pytest
from django.core.management import call_command

from modules.patents.models import PatentPolicy

pytestmark = pytest.mark.django_db


def test_pms_seed_policy_command():
    out = io.StringIO()
    call_command("pms_seed_policy", stdout=out)
    output = out.getvalue()
    assert "Created active PatentPolicy" in output

    policy = PatentPolicy.objects.filter(is_active=True).first()
    assert policy is not None
    assert policy.director_review_days == 15
    assert policy.revision_resubmission_days == 60
    assert len(policy.withdrawal_eligible_states) == 8

    # Second call without --force does not duplicate
    out2 = io.StringIO()
    call_command("pms_seed_policy", stdout=out2)
    assert "Active policy already exists" in out2.getvalue()

    # Call with --force creates new active policy
    out3 = io.StringIO()
    call_command("pms_seed_policy", "--force", "--threshold", "25000.00", stdout=out3)
    assert "Created active PatentPolicy" in out3.getvalue()
    new_policy = PatentPolicy.objects.filter(is_active=True).first()
    assert new_policy.cost_escalation_threshold == 25000.00


def test_pms_sweep_deadlines_command():
    out = io.StringIO()
    call_command("pms_sweep_deadlines", stdout=out)
    output = out.getvalue()
    assert "PMS deadline sweep completed" in output


def test_pms_readiness_command():
    PatentPolicy.objects.all().delete()
    with pytest.raises(SystemExit):
        call_command("pms_readiness")

    call_command("pms_seed_policy")
    out = io.StringIO()
    call_command("pms_readiness", stdout=out)
    assert "Patents module is ready for operation" in out.getvalue()

