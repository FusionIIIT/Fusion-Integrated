from datetime import date
from types import SimpleNamespace

import pytest
from django.core.management import CommandError, call_command

from modules.phc.models import ReimbursementPolicy
from modules.phc.registry import readiness

pytestmark = pytest.mark.django_db


def test_phc_br_06_policy_seed_is_idempotent():
    assert readiness() == []
    call_command("seed_phc_policy")
    assert ReimbursementPolicy.objects.filter(
        effective_period__contains=date(2026, 1, 1), submission_window_days=30,
    ).exists()


def test_phc_br_06_readiness_names_missing_policy(monkeypatch):
    class EmptyQuery:
        def exists(self):
            return False

    monkeypatch.setattr(ReimbursementPolicy.objects, "filter", lambda **kwargs: EmptyQuery())
    assert readiness() == [
        "Seed the effective-dated 30-day PHC reimbursement policy before enabling claims."]
    with pytest.raises(CommandError, match="PHC is not ready"):
        call_command("phc_readiness")


def test_phc_br_06_seed_command_refuses_an_unapproved_current_policy(monkeypatch):
    class ExistingQuery:
        def first(self):
            return SimpleNamespace(submission_window_days=14)

    monkeypatch.setattr(ReimbursementPolicy.objects, "filter", lambda **kwargs: ExistingQuery())
    with pytest.raises(CommandError, match="not the approved 30-day policy"):
        call_command("seed_phc_policy")
