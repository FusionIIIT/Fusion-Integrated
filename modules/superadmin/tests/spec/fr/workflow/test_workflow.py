from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.fr.conftest import run_case

pytestmark = pytest.mark.django_db


def test_tc_037_workflow(sa_principal, it_principal, stub_iam):
    """TC-037; source_id: CFR-SA-007 / AFR-SA-034."""
    run_case("TC-037", sa_principal, it_principal, stub_iam)


def test_tc_044_workflow(sa_principal, it_principal, stub_iam):
    """TC-044; source_id: CFR-SA-008 / AFR-SA-039B."""
    run_case("TC-044", sa_principal, it_principal, stub_iam)


def test_tc_056_workflow(sa_principal, it_principal, stub_iam):
    """TC-056; source_id: CFR-SA-011 / AFR-SA-047."""
    run_case("TC-056", sa_principal, it_principal, stub_iam)


def test_tc_059_workflow(sa_principal, it_principal, stub_iam):
    """TC-059; source_id: CFR-SA-011 / AFR-SA-049B."""
    run_case("TC-059", sa_principal, it_principal, stub_iam)


def test_tc_061_workflow(sa_principal, it_principal, stub_iam):
    """TC-061; source_id: CFR-SA-012 / AFR-SA-051A."""
    run_case("TC-061", sa_principal, it_principal, stub_iam)


def test_tc_062_workflow(sa_principal, it_principal, stub_iam):
    """TC-062; source_id: CFR-SA-012 / AFR-SA-051B."""
    run_case("TC-062", sa_principal, it_principal, stub_iam)


def test_tc_066_workflow(sa_principal, it_principal, stub_iam):
    """TC-066; source_id: CFR-SA-013 / AFR-SA-054B."""
    run_case("TC-066", sa_principal, it_principal, stub_iam)


def test_tc_067_workflow(sa_principal, it_principal, stub_iam):
    """TC-067; source_id: CFR-SA-013 / AFR-SA-055A."""
    run_case("TC-067", sa_principal, it_principal, stub_iam)


def test_tc_069_workflow(sa_principal, it_principal, stub_iam):
    """TC-069; source_id: CFR-SA-014 / AFR-SA-056."""
    run_case("TC-069", sa_principal, it_principal, stub_iam)


def test_tc_070_workflow(sa_principal, it_principal, stub_iam):
    """TC-070; source_id: CFR-SA-015 / AFR-SA-057."""
    run_case("TC-070", sa_principal, it_principal, stub_iam)


def test_tc_071_workflow(sa_principal, it_principal, stub_iam):
    """TC-071; source_id: CFR-SA-014 / AFR-SA-058."""
    run_case("TC-071", sa_principal, it_principal, stub_iam)


def test_tc_072_workflow(sa_principal, it_principal, stub_iam):
    """TC-072; source_id: CFR-SA-014 / AFR-SA-059A."""
    run_case("TC-072", sa_principal, it_principal, stub_iam)


def test_tc_073_workflow(sa_principal, it_principal, stub_iam):
    """TC-073; source_id: CFR-SA-014 / AFR-SA-059B."""
    run_case("TC-073", sa_principal, it_principal, stub_iam)


def test_tc_074_workflow(sa_principal, it_principal, stub_iam):
    """TC-074; source_id: CFR-SA-014 / AFR-SA-060."""
    run_case("TC-074", sa_principal, it_principal, stub_iam)


def test_tc_075_workflow(sa_principal, it_principal, stub_iam):
    """TC-075; source_id: CFR-SA-016 / AFR-SA-061A."""
    run_case("TC-075", sa_principal, it_principal, stub_iam)


def test_tc_076_workflow(sa_principal, it_principal, stub_iam):
    """TC-076; source_id: CFR-SA-016 / AFR-SA-061B."""
    run_case("TC-076", sa_principal, it_principal, stub_iam)


def test_tc_090_workflow(sa_principal, it_principal, stub_iam):
    """TC-090; source_id: CFR-SA-020 / AFR-SA-072."""
    run_case("TC-090", sa_principal, it_principal, stub_iam)
