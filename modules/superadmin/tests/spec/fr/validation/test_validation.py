from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.fr.conftest import run_case

pytestmark = pytest.mark.django_db


def test_tc_003_validation(sa_principal, it_principal, stub_iam):
    """TC-003; source_id: CFR-SA-001 / AFR-SA-003A."""
    run_case("TC-003", sa_principal, it_principal, stub_iam)


def test_tc_004_validation(sa_principal, it_principal, stub_iam):
    """TC-004; source_id: CFR-SA-002 / AFR-SA-003B."""
    run_case("TC-004", sa_principal, it_principal, stub_iam)


def test_tc_005_validation(sa_principal, it_principal, stub_iam):
    """TC-005; source_id: CFR-SA-001 / AFR-SA-004."""
    run_case("TC-005", sa_principal, it_principal, stub_iam)


def test_tc_006_validation(sa_principal, it_principal, stub_iam):
    """TC-006; source_id: CFR-SA-001 / AFR-SA-005."""
    run_case("TC-006", sa_principal, it_principal, stub_iam)


def test_tc_027_validation(sa_principal, it_principal, stub_iam):
    """TC-027; source_id: CFR-SA-006 / AFR-SA-024."""
    run_case("TC-027", sa_principal, it_principal, stub_iam)


def test_tc_065_validation(sa_principal, it_principal, stub_iam):
    """TC-065; source_id: CFR-SA-013 / AFR-SA-054A."""
    run_case("TC-065", sa_principal, it_principal, stub_iam)


def test_tc_095_validation(sa_principal, it_principal, stub_iam):
    """TC-095; source_id: CFR-SA-021 / AFR-SA-074B."""
    run_case("TC-095", sa_principal, it_principal, stub_iam)


def test_tc_097_validation(sa_principal, it_principal, stub_iam):
    """TC-097; source_id: CFR-SA-020 / AFR-SA-075."""
    run_case("TC-097", sa_principal, it_principal, stub_iam)


def test_tc_099_validation(sa_principal, it_principal, stub_iam):
    """TC-099; source_id: CFR-SA-023 / AFR-SA-077."""
    run_case("TC-099", sa_principal, it_principal, stub_iam)


def test_tc_100_validation(sa_principal, it_principal, stub_iam):
    """TC-100; source_id: CFR-SA-004 / AFR-SA-078."""
    run_case("TC-100", sa_principal, it_principal, stub_iam)


def test_tc_101_validation(sa_principal, it_principal, stub_iam):
    """TC-101; source_id: CFR-SA-022 / AFR-SA-079."""
    run_case("TC-101", sa_principal, it_principal, stub_iam)


def test_tc_108_validation(sa_principal, it_principal, stub_iam):
    """TC-108; source_id: CFR-SA-021 / AFR-SA-082."""
    run_case("TC-108", sa_principal, it_principal, stub_iam)
