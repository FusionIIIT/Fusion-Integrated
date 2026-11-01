"""Unit tests for IWD module skeleton and platform wiring (Increment 2).

Covers:
- AppConfig registration attributes (name, label)
- Registry module spec (code, base_path, status)
- Permission naming conventions (all start with 'iwd.')
- Completeness of permission definitions vs role grants
- Strict role separation: Department Head vs Dean (BR-IWD-001, BR-IWD-018, AFR-IWD-060)
- Contracts plural signature (ops/checks/contracts_are_plural.py)
"""
from collections.abc import Sequence
import inspect
from typing import get_origin, get_type_hints

from modules.iwd.apps import IwdConfig
from modules.iwd.contracts import get_complaints
import modules.iwd.permissions as perms
from modules.iwd.registry import (
    MODULE,
    NAV_ITEMS,
    PERMISSIONS,
    ROLE_GRANTS,
    SCOPE_PERMISSIONS,
    SYSTEM_PERMISSIONS,
)


def test_iwd_app_config():
    """Verify AppConfig configuration matches repository conventions."""
    assert IwdConfig.name == "modules.iwd"
    assert IwdConfig.label == "iwd"


def test_iwd_registry_module_spec():
    """Verify registry MODULE metadata."""
    assert MODULE["code"] == "iwd"
    assert MODULE["base_path"] == "/iwd"
    assert MODULE["status"] == "planned"
    assert MODULE["nav_section"] == "Campus"


def test_all_permissions_carry_module_prefix():
    """Every permission code must be prefixed with 'iwd.' (permission_manifest rule)."""
    assert len(PERMISSIONS) > 0
    for code, label in PERMISSIONS:
        assert code.startswith("iwd."), f"Permission {code} does not start with 'iwd.'"
        assert len(label.strip()) > 0


def test_permissions_grants_completeness():
    """Every declared permission must either be in ROLE_GRANTS or SYSTEM_PERMISSIONS."""
    declared = {code for code, _ in PERMISSIONS}
    system = set(SYSTEM_PERMISSIONS)
    granted = {code for codes in ROLE_GRANTS.values() for code in codes}

    # No ungranted / unreachable permissions
    unreachable = declared - system - granted
    assert not unreachable, f"Unreachable permissions: {unreachable}"

    # No unknown codes granted
    unknown = granted - declared
    assert not unknown, f"Granted permissions not in PERMISSIONS: {unknown}"

    # No collisions between system and granted
    collision = system & granted
    assert not collision, f"Permissions both system and granted: {collision}"


def test_strict_department_head_dean_role_separation():
    """Department Head and Dean must be separate roles with non-aliased permissions (BR-IWD-018, AFR-IWD-060)."""
    assert "Department Head" in ROLE_GRANTS
    assert "Dean" in ROLE_GRANTS

    dept_head_perms = set(ROLE_GRANTS["Department Head"])
    dean_perms = set(ROLE_GRANTS["Dean"])

    # Department Head has mid-range estimate review and physical verification
    assert perms.ESTIMATE_REVIEW_MID in dept_head_perms
    assert perms.WORK_VERIFY in dept_head_perms

    # Dean strictly does NOT hold mid-range estimate review or physical verification
    assert perms.ESTIMATE_REVIEW_MID not in dean_perms
    assert perms.WORK_VERIFY not in dean_perms


def test_contract_getters_are_plural():
    """Cross-module contract getters must accept a sequence (ADR-0013)."""
    sig = inspect.signature(get_complaints)
    first_param = list(sig.parameters.values())[0]
    assert first_param.name == "complaint_ids"

    # Resolve postponed type evaluation (from __future__ import annotations)
    hints = get_type_hints(get_complaints)
    assert "complaint_ids" in hints
    param_type = hints["complaint_ids"]
    origin = get_origin(param_type) or param_type
    assert issubclass(origin, Sequence)

