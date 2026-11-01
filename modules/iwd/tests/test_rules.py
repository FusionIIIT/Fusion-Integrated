from decimal import Decimal
import pytest
from modules.iwd.domain.rules import (
    determine_cost_band,
    CostBand,
    validate_urgent_flag,
    validate_role_separation,
    can_initiate_procurement,
    can_resolve_complaint,
    can_proceed_to_settlement,
)


def test_cost_band_low():
    assert determine_cost_band(Decimal("15000.00")) == CostBand.LOW
    assert determine_cost_band(Decimal("24999.99")) == CostBand.LOW


def test_cost_band_mid():
    assert determine_cost_band(Decimal("25000.00")) == CostBand.MID
    assert determine_cost_band(Decimal("100000.00")) == CostBand.MID
    assert determine_cost_band(Decimal("250000.00")) == CostBand.MID


def test_cost_band_high():
    assert determine_cost_band(Decimal("250000.01")) == CostBand.HIGH
    assert determine_cost_band(Decimal("500000.00")) == CostBand.HIGH


def test_role_separation_dept_head_dean():
    # BR-IWD-001 & BR-IWD-018: Dept Head and Dean are distinct
    assert not validate_role_separation("DEAN", "DEPARTMENT_HEAD")
    assert not validate_role_separation("DEPARTMENT_HEAD", "DEAN")
    assert validate_role_separation("DEPARTMENT_HEAD", "DEPARTMENT_HEAD")
    assert validate_role_separation("DEAN", "DEAN")


def test_urgent_flag_preserves_controls():
    res = validate_urgent_flag(True, CostBand.HIGH)
    assert res["is_urgent"] is True
    assert res["preserves_cost_controls"] is True


def test_procurement_conditions():
    assert can_initiate_procurement(stock_available=False) is True
    assert can_initiate_procurement(stock_available=True) is False


def test_settlement_gate():
    assert can_proceed_to_settlement(auditor_validated=True, director_approved=True) is True
    assert can_proceed_to_settlement(auditor_validated=False, director_approved=True) is False
    assert can_proceed_to_settlement(auditor_validated=True, director_approved=False) is False

