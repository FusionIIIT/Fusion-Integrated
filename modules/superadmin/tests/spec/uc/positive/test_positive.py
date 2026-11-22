from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.uc._cases import run_case

pytestmark = pytest.mark.django_db
















def test_tc_052_uc(sa_principal, it_principal, stub_iam):
    """TC-052; source_id: UC-SA-015 Main Success Scenario."""
    run_case("TC-052", sa_principal, it_principal, stub_iam)


def test_tc_056_uc(sa_principal, it_principal, stub_iam):
    """TC-056; source_id: UC-SA-016 Main Success Scenario."""
    run_case("TC-056", sa_principal, it_principal, stub_iam)


def test_tc_060_uc(sa_principal, it_principal, stub_iam):
    """TC-060; source_id: UC-SA-017 Main Success Scenario."""
    run_case("TC-060", sa_principal, it_principal, stub_iam)


def test_tc_063_uc(sa_principal, it_principal, stub_iam):
    """TC-063; source_id: UC-SA-018 Main Success Scenario."""
    run_case("TC-063", sa_principal, it_principal, stub_iam)


def test_tc_067_uc(sa_principal, it_principal, stub_iam):
    """TC-067; source_id: UC-SA-019 Main Success Scenario."""
    run_case("TC-067", sa_principal, it_principal, stub_iam)




def test_tc_076_uc(sa_principal, it_principal, stub_iam):
    """TC-076; source_id: UC-SA-022 Main Success Scenario."""
    run_case("TC-076", sa_principal, it_principal, stub_iam)


def test_tc_079_uc(sa_principal, it_principal, stub_iam):
    """TC-079; source_id: UC-SA-023 Main Success Scenario."""
    run_case("TC-079", sa_principal, it_principal, stub_iam)


def test_tc_082_uc(sa_principal, it_principal, stub_iam):
    """TC-082; source_id: UC-SA-024 Main Success Scenario."""
    run_case("TC-082", sa_principal, it_principal, stub_iam)


def test_tc_085_uc(sa_principal, it_principal, stub_iam):
    """TC-085; source_id: UC-SA-025 Main Success Scenario."""
    run_case("TC-085", sa_principal, it_principal, stub_iam)


def test_tc_088_uc(sa_principal, it_principal, stub_iam):
    """TC-088; source_id: UC-SA-026 Main Success Scenario."""
    run_case("TC-088", sa_principal, it_principal, stub_iam)


def test_tc_091_uc(sa_principal, it_principal, stub_iam):
    """TC-091; source_id: UC-SA-027 Main Success Scenario."""
    run_case("TC-091", sa_principal, it_principal, stub_iam)





def test_tc_104_uc(sa_principal, it_principal, stub_iam):
    """TC-104; source_id: UC-SA-031 Main Success Scenario."""
    run_case("TC-104", sa_principal, it_principal, stub_iam)
