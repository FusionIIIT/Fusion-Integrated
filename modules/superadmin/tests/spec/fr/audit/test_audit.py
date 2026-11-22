from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.fr.conftest import run_case

pytestmark = pytest.mark.django_db


def test_tc_008_audit(sa_principal, it_principal, stub_iam):
    """TC-008; source_id: CFR-SA-001 / AFR-SA-007."""
    run_case("TC-008", sa_principal, it_principal, stub_iam)


def test_tc_015_audit(sa_principal, it_principal, stub_iam):
    """TC-015; source_id: CFR-SA-017 / AFR-SA-014."""
    run_case("TC-015", sa_principal, it_principal, stub_iam)


def test_tc_022_audit(sa_principal, it_principal, stub_iam):
    """TC-022; source_id: CFR-SA-004 / AFR-SA-019B."""
    run_case("TC-022", sa_principal, it_principal, stub_iam)


def test_tc_034_audit(sa_principal, it_principal, stub_iam):
    """TC-034; source_id: CFR-SA-017 / AFR-SA-031."""
    run_case("TC-034", sa_principal, it_principal, stub_iam)


def test_tc_039_audit(sa_principal, it_principal, stub_iam):
    """TC-039; source_id: CFR-SA-017 / AFR-SA-035B."""
    run_case("TC-039", sa_principal, it_principal, stub_iam)


def test_tc_046_audit(sa_principal, it_principal, stub_iam):
    """TC-046; source_id: CFR-SA-017 / AFR-SA-039D."""
    run_case("TC-046", sa_principal, it_principal, stub_iam)


def test_tc_054_audit(sa_principal, it_principal, stub_iam):
    """TC-054; source_id: CFR-SA-010 / AFR-SA-045."""
    run_case("TC-054", sa_principal, it_principal, stub_iam)


def test_tc_058_audit(sa_principal, it_principal, stub_iam):
    """TC-058; source_id: CFR-SA-011 / AFR-SA-049A."""
    run_case("TC-058", sa_principal, it_principal, stub_iam)


def test_tc_060_audit(sa_principal, it_principal, stub_iam):
    """TC-060; source_id: CFR-SA-011 / AFR-SA-050."""
    run_case("TC-060", sa_principal, it_principal, stub_iam)


def test_tc_077_audit(sa_principal, it_principal, stub_iam):
    """TC-077; source_id: CFR-SA-017 / AFR-SA-062."""
    run_case("TC-077", sa_principal, it_principal, stub_iam)


def test_tc_078_audit(sa_principal, it_principal, stub_iam):
    """TC-078; source_id: CFR-SA-017 / AFR-SA-063."""
    run_case("TC-078", sa_principal, it_principal, stub_iam)


def test_tc_079_audit(sa_principal, it_principal, stub_iam):
    """TC-079; source_id: CFR-SA-018 / AFR-SA-064."""
    run_case("TC-079", sa_principal, it_principal, stub_iam)


def test_tc_083_audit(sa_principal, it_principal, stub_iam):
    """TC-083; source_id: CFR-SA-018 / AFR-SA-066."""
    run_case("TC-083", sa_principal, it_principal, stub_iam)


def test_tc_091_audit(sa_principal, it_principal, stub_iam):
    """TC-091; source_id: CFR-SA-021 / AFR-SA-073A."""
    run_case("TC-091", sa_principal, it_principal, stub_iam)


def test_tc_092_audit(sa_principal, it_principal, stub_iam):
    """TC-092; source_id: CFR-SA-021 / AFR-SA-073B."""
    run_case("TC-092", sa_principal, it_principal, stub_iam)


def test_tc_093_audit(sa_principal, it_principal, stub_iam):
    """TC-093; source_id: CFR-SA-021 / AFR-SA-073C."""
    run_case("TC-093", sa_principal, it_principal, stub_iam)


def test_tc_096_audit(sa_principal, it_principal, stub_iam):
    """TC-096; source_id: CFR-SA-021 / AFR-SA-074C."""
    run_case("TC-096", sa_principal, it_principal, stub_iam)


def test_tc_102_audit(sa_principal, it_principal, stub_iam):
    """TC-102; source_id: CFR-SA-021 / AFR-SA-080A."""
    run_case("TC-102", sa_principal, it_principal, stub_iam)


def test_tc_103_audit(sa_principal, it_principal, stub_iam):
    """TC-103; source_id: CFR-SA-021 / AFR-SA-080B."""
    run_case("TC-103", sa_principal, it_principal, stub_iam)


def test_tc_104_audit(sa_principal, it_principal, stub_iam):
    """TC-104; source_id: CFR-SA-017 / AFR-SA-081A."""
    run_case("TC-104", sa_principal, it_principal, stub_iam)


def test_tc_105_audit(sa_principal, it_principal, stub_iam):
    """TC-105; source_id: CFR-SA-017 / AFR-SA-081B."""
    run_case("TC-105", sa_principal, it_principal, stub_iam)


def test_tc_106_audit(sa_principal, it_principal, stub_iam):
    """TC-106; source_id: CFR-SA-017 / AFR-SA-081C."""
    run_case("TC-106", sa_principal, it_principal, stub_iam)


def test_tc_107_audit(sa_principal, it_principal, stub_iam):
    """TC-107; source_id: CFR-SA-017 / AFR-SA-081D."""
    run_case("TC-107", sa_principal, it_principal, stub_iam)
