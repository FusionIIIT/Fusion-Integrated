"""Domain validator unit tests — no DB, pure Python."""

from __future__ import annotations

import pytest

from modules.superadmin.domain.constants import PERMITTED_CONFIG_KEYS
from modules.superadmin.domain.exceptions import DomainError
from modules.superadmin.domain.validators import (
    validate_bulk_size,
    validate_configuration_key,
    validate_institute_email,
    validate_institute_id,
    validate_no_self_modification,
)

# -- validate_institute_id -------------------------------------------------


def test_valid_institute_id_passes():
    validate_institute_id("2021BCS001")


def test_institute_id_too_short_raises():
    with pytest.raises(DomainError):
        validate_institute_id("AB")


def test_empty_institute_id_raises():
    with pytest.raises(DomainError):
        validate_institute_id("")


def test_institute_id_with_special_chars_raises():
    with pytest.raises(DomainError):
        validate_institute_id("2021-BCS-001!")


# -- validate_institute_email ----------------------------------------------


def test_valid_iiitdmj_email_passes():
    validate_institute_email("asha.verma@iiitdmj.ac.in")


def test_non_iiitdmj_email_raises():
    with pytest.raises(DomainError):
        validate_institute_email("asha@gmail.com")


def test_empty_email_raises():
    with pytest.raises(DomainError):
        validate_institute_email("")


def test_malformed_email_raises():
    with pytest.raises(DomainError):
        validate_institute_email("not-an-email")


# -- validate_bulk_size ----------------------------------------------------


def test_bulk_size_at_limit_passes():
    validate_bulk_size(1000, max_limit=1000)


def test_bulk_size_below_limit_passes():
    validate_bulk_size(1, max_limit=1000)


def test_bulk_size_zero_raises():
    with pytest.raises(DomainError):
        validate_bulk_size(0, max_limit=1000)


def test_bulk_size_over_limit_raises():
    with pytest.raises(DomainError):
        validate_bulk_size(1001, max_limit=1000)


# -- validate_configuration_key --------------------------------------------


def test_known_config_key_passes():
    validate_configuration_key("archival.reversibility_window_days", PERMITTED_CONFIG_KEYS)


def test_unknown_config_key_raises():
    with pytest.raises(DomainError):
        validate_configuration_key("evil.inject", PERMITTED_CONFIG_KEYS)


def test_empty_config_key_raises():
    with pytest.raises(DomainError):
        validate_configuration_key("", PERMITTED_CONFIG_KEYS)


# -- validate_no_self_modification -----------------------------------------


def test_different_actor_and_target_passes():
    validate_no_self_modification(actor_user_id=1, target_user_id=2)


def test_same_actor_and_target_raises():
    with pytest.raises(DomainError):
        validate_no_self_modification(actor_user_id=42, target_user_id=42)
