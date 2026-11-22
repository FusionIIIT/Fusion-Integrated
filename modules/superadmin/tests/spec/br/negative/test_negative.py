from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.br.conftest import run_br_case

pytestmark = pytest.mark.django_db

def test_tc_sa_br_004_02(sa_principal, stub_iam):
    """TC-SA-BR-004-02; source_id: BR-SA-004 ineligible archival."""
    run_br_case("TC-SA-BR-004-02", sa_principal, stub_iam)

def test_tc_sa_br_005_03(sa_principal, stub_iam):
    """TC-SA-BR-005-03; source_id: BR-SA-005 restoration after reversible period."""
    run_br_case("TC-SA-BR-005-03", sa_principal, stub_iam)

def test_tc_sa_br_021_01(sa_principal, stub_iam):
    """TC-SA-BR-021-01; source_id: BR-SA-021 purge within retention."""
    run_br_case("TC-SA-BR-021-01", sa_principal, stub_iam)

def test_tc_sa_br_022_02(sa_principal, stub_iam):
    """TC-SA-BR-022-02; source_id: BR-SA-022 IT Head approval absent or rejected."""
    run_br_case("TC-SA-BR-022-02", sa_principal, stub_iam)

def test_tc_sa_br_025_01(sa_principal, stub_iam):
    """TC-SA-BR-025-01; source_id: BR-SA-025 audit immutability and permanent retention."""
    run_br_case("TC-SA-BR-025-01", sa_principal, stub_iam)

def test_tc_sa_br_030_02(sa_principal, stub_iam):
    """TC-SA-BR-030-02; source_id: BR-SA-030 bulk operation above 1000-record limit."""
    run_br_case("TC-SA-BR-030-02", sa_principal, stub_iam)

def test_tc_sa_br_035_02(sa_principal, stub_iam):
    """TC-SA-BR-035-02; source_id: BR-SA-035 excluded configuration categories."""
    run_br_case("TC-SA-BR-035-02", sa_principal, stub_iam)

