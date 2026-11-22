from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.fr.conftest import run_case

pytestmark = pytest.mark.django_db


def test_tc_009_access(sa_principal, it_principal, stub_iam):
    """TC-009; source_id: CFR-SA-001 / AFR-SA-008."""
    run_case("TC-009", sa_principal, it_principal, stub_iam)


def test_tc_011_access(sa_principal, it_principal, stub_iam):
    """TC-011; source_id: CFR-SA-002 / AFR-SA-010."""
    run_case("TC-011", sa_principal, it_principal, stub_iam)


def test_tc_024_access(sa_principal, it_principal, stub_iam):
    """TC-024; source_id: CFR-SA-005 / AFR-SA-021."""
    run_case("TC-024", sa_principal, it_principal, stub_iam)


def test_tc_036_access(sa_principal, it_principal, stub_iam):
    """TC-036; source_id: CFR-SA-007 / AFR-SA-033."""
    run_case("TC-036", sa_principal, it_principal, stub_iam)


def test_tc_040_access(sa_principal, it_principal, stub_iam):
    """TC-040; source_id: CFR-SA-007 / AFR-SA-036."""
    run_case("TC-040", sa_principal, it_principal, stub_iam)


def test_tc_043_access(sa_principal, it_principal, stub_iam):
    """TC-043; source_id: CFR-SA-008 / AFR-SA-039A."""
    run_case("TC-043", sa_principal, it_principal, stub_iam)


def test_tc_055_access(sa_principal, it_principal, stub_iam):
    """TC-055; source_id: CFR-SA-010 / AFR-SA-046."""
    run_case("TC-055", sa_principal, it_principal, stub_iam)


def test_tc_081_access(sa_principal, it_principal, stub_iam):
    """TC-081; source_id: CFR-SA-018 / AFR-SA-065B."""
    run_case("TC-081", sa_principal, it_principal, stub_iam)


def test_tc_084_access(sa_principal, it_principal, stub_iam):
    """TC-084; source_id: CFR-SA-005 / AFR-SA-067."""
    run_case("TC-084", sa_principal, it_principal, stub_iam)
