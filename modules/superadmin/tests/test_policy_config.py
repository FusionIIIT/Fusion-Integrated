"""Policy config: supersede creates versioned records; forbidden keys raise errors."""

from __future__ import annotations

import pytest

from core.api.exceptions import DomainError
from modules.superadmin.domain.constants import (
    CONFIG_KEY_BULK_MAX_BATCH_SIZE,
    CONFIG_KEY_PURGE_APPROVAL_TTL_HOURS,
    CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
    DEFAULT_POLICY_VALUES,
)
from modules.superadmin.selectors.config import get_active_policy_param, get_active_policy_value
from modules.superadmin.services.config import supersede_policy_param

pytestmark = pytest.mark.django_db


def test_supersede_creates_first_version(sa_principal):
    param = supersede_policy_param(
        sa_principal,
        key=CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
        value="45",
    )

    assert param.version == 1
    assert param.value == "45"
    assert param.effective_to is None


def test_supersede_creates_second_version_and_closes_first(sa_principal):
    first = supersede_policy_param(
        sa_principal,
        key=CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
        value="30",
    )
    second = supersede_policy_param(
        sa_principal,
        key=CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
        value="45",
    )

    first.refresh_from_db()
    assert first.effective_to is not None
    assert second.version == 2
    assert second.effective_to is None


def test_supersede_forbidden_key_raises(sa_principal):
    with pytest.raises(DomainError):
        supersede_policy_param(
            sa_principal,
            key="evil.inject",
            value="bad",
        )


def test_get_active_policy_param_returns_latest(sa_principal):
    supersede_policy_param(sa_principal, key=CONFIG_KEY_PURGE_APPROVAL_TTL_HOURS, value="48")
    supersede_policy_param(sa_principal, key=CONFIG_KEY_PURGE_APPROVAL_TTL_HOURS, value="96")

    active = get_active_policy_param(CONFIG_KEY_PURGE_APPROVAL_TTL_HOURS)
    assert active is not None
    assert active.value == "96"
    assert active.version == 2


def test_get_active_policy_param_returns_none_when_unseeded():
    result = get_active_policy_param(CONFIG_KEY_BULK_MAX_BATCH_SIZE)
    assert result is None


def test_get_active_policy_value_falls_back_to_default():
    # No seeded value — should return DEFAULT_POLICY_VALUES fallback
    value = get_active_policy_value(CONFIG_KEY_BULK_MAX_BATCH_SIZE)
    assert str(value) == str(DEFAULT_POLICY_VALUES[CONFIG_KEY_BULK_MAX_BATCH_SIZE])


def test_get_active_policy_value_returns_seeded_over_default(sa_principal):
    supersede_policy_param(sa_principal, key=CONFIG_KEY_BULK_MAX_BATCH_SIZE, value="500")

    value = get_active_policy_value(CONFIG_KEY_BULK_MAX_BATCH_SIZE)
    assert str(value) == "500"


def test_supersede_records_audit_event(sa_principal):
    from modules.superadmin.models.audit import SuperAdminAuditLog

    before = SuperAdminAuditLog.objects.count()
    supersede_policy_param(sa_principal, key=CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS, value="60")
    after = SuperAdminAuditLog.objects.count()

    assert after == before + 1
    latest = SuperAdminAuditLog.objects.order_by("-timestamp").first()
    assert latest.action == "policy.superseded"
    assert latest.target_id == CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS
