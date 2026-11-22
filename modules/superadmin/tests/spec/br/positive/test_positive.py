from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.br.conftest import run_br_case

pytestmark = pytest.mark.django_db

def test_tc_sa_br_004_01(sa_principal, stub_iam):
    """TC-SA-BR-004-01; source_id: BR-SA-004 eligible archival."""
    run_br_case("TC-SA-BR-004-01", sa_principal, stub_iam)

def test_tc_sa_br_005_01(sa_principal, stub_iam):
    """TC-SA-BR-005-01; source_id: BR-SA-005 restoration within reversible period with authorization."""
    run_br_case("TC-SA-BR-005-01", sa_principal, stub_iam)

def test_tc_sa_br_021_02(sa_principal, stub_iam):
    """TC-SA-BR-021-02; source_id: BR-SA-021 purge after retention."""
    run_br_case("TC-SA-BR-021-02", sa_principal, stub_iam)

def test_tc_sa_br_022_01(sa_principal, stub_iam):
    """TC-SA-BR-022-01; source_id: BR-SA-022 dual authorization granted."""
    run_br_case("TC-SA-BR-022-01", sa_principal, stub_iam)

def test_tc_sa_br_030_01(sa_principal, stub_iam):
    """TC-SA-BR-030-01; source_id: BR-SA-030 bulk operation at 1000-record limit."""
    run_br_case("TC-SA-BR-030-01", sa_principal, stub_iam)

def test_tc_sa_br_035_01(sa_principal, stub_iam):
    """TC-SA-BR-035-01; source_id: BR-SA-035 permitted configuration within policy bounds."""
    run_br_case("TC-SA-BR-035-01", sa_principal, stub_iam)

