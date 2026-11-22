from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.fr.conftest import run_case

pytestmark = pytest.mark.django_db


def test_tc_001_positive(sa_principal, it_principal, stub_iam):
    """TC-001; source_id: CFR-SA-001 / AFR-SA-001."""
    run_case("TC-001", sa_principal, it_principal, stub_iam)


def test_tc_002_positive(sa_principal, it_principal, stub_iam):
    """TC-002; source_id: CFR-SA-001 / AFR-SA-002."""
    run_case("TC-002", sa_principal, it_principal, stub_iam)


def test_tc_007_positive(sa_principal, it_principal, stub_iam):
    """TC-007; source_id: CFR-SA-001 / AFR-SA-006."""
    run_case("TC-007", sa_principal, it_principal, stub_iam)


def test_tc_012_positive(sa_principal, it_principal, stub_iam):
    """TC-012; source_id: CFR-SA-002 / AFR-SA-011."""
    run_case("TC-012", sa_principal, it_principal, stub_iam)


def test_tc_013_positive(sa_principal, it_principal, stub_iam):
    """TC-013; source_id: CFR-SA-003 / AFR-SA-012."""
    run_case("TC-013", sa_principal, it_principal, stub_iam)


def test_tc_014_positive(sa_principal, it_principal, stub_iam):
    """TC-014; source_id: CFR-SA-003 / AFR-SA-013."""
    run_case("TC-014", sa_principal, it_principal, stub_iam)


def test_tc_016_positive(sa_principal, it_principal, stub_iam):
    """TC-016; source_id: CFR-SA-004 / AFR-SA-015."""
    run_case("TC-016", sa_principal, it_principal, stub_iam)


def test_tc_017_positive(sa_principal, it_principal, stub_iam):
    """TC-017; source_id: CFR-SA-004 / AFR-SA-016."""
    run_case("TC-017", sa_principal, it_principal, stub_iam)


def test_tc_018_positive(sa_principal, it_principal, stub_iam):
    """TC-018; source_id: CFR-SA-004 / AFR-SA-017."""
    run_case("TC-018", sa_principal, it_principal, stub_iam)


def test_tc_019_positive(sa_principal, it_principal, stub_iam):
    """TC-019; source_id: CFR-SA-004 / AFR-SA-018A."""
    run_case("TC-019", sa_principal, it_principal, stub_iam)


def test_tc_020_positive(sa_principal, it_principal, stub_iam):
    """TC-020; source_id: CFR-SA-004 / AFR-SA-018B."""
    run_case("TC-020", sa_principal, it_principal, stub_iam)


def test_tc_021_positive(sa_principal, it_principal, stub_iam):
    """TC-021; source_id: CFR-SA-004 / AFR-SA-019A."""
    run_case("TC-021", sa_principal, it_principal, stub_iam)


def test_tc_025_positive(sa_principal, it_principal, stub_iam):
    """TC-025; source_id: CFR-SA-006 / AFR-SA-022."""
    run_case("TC-025", sa_principal, it_principal, stub_iam)


def test_tc_026_positive(sa_principal, it_principal, stub_iam):
    """TC-026; source_id: CFR-SA-006 / AFR-SA-023."""
    run_case("TC-026", sa_principal, it_principal, stub_iam)


def test_tc_028_positive(sa_principal, it_principal, stub_iam):
    """TC-028; source_id: CFR-SA-006 / AFR-SA-025."""
    run_case("TC-028", sa_principal, it_principal, stub_iam)


def test_tc_029_positive(sa_principal, it_principal, stub_iam):
    """TC-029; source_id: CFR-SA-006 / AFR-SA-026."""
    run_case("TC-029", sa_principal, it_principal, stub_iam)


def test_tc_030_positive(sa_principal, it_principal, stub_iam):
    """TC-030; source_id: CFR-SA-006 / AFR-SA-027."""
    run_case("TC-030", sa_principal, it_principal, stub_iam)


def test_tc_031_positive(sa_principal, it_principal, stub_iam):
    """TC-031; source_id: CFR-SA-009 / AFR-SA-028."""
    run_case("TC-031", sa_principal, it_principal, stub_iam)


def test_tc_033_positive(sa_principal, it_principal, stub_iam):
    """TC-033; source_id: CFR-SA-010 / AFR-SA-030."""
    run_case("TC-033", sa_principal, it_principal, stub_iam)


def test_tc_035_positive(sa_principal, it_principal, stub_iam):
    """TC-035; source_id: CFR-SA-007 / AFR-SA-032."""
    run_case("TC-035", sa_principal, it_principal, stub_iam)


def test_tc_041_positive(sa_principal, it_principal, stub_iam):
    """TC-041; source_id: CFR-SA-007 / AFR-SA-037."""
    run_case("TC-041", sa_principal, it_principal, stub_iam)


def test_tc_042_positive(sa_principal, it_principal, stub_iam):
    """TC-042; source_id: CFR-SA-008 / AFR-SA-038."""
    run_case("TC-042", sa_principal, it_principal, stub_iam)


def test_tc_047_positive(sa_principal, it_principal, stub_iam):
    """TC-047; source_id: CFR-SA-009 / AFR-SA-040A."""
    run_case("TC-047", sa_principal, it_principal, stub_iam)


def test_tc_048_positive(sa_principal, it_principal, stub_iam):
    """TC-048; source_id: CFR-SA-008 / AFR-SA-040B."""
    run_case("TC-048", sa_principal, it_principal, stub_iam)


def test_tc_049_positive(sa_principal, it_principal, stub_iam):
    """TC-049; source_id: CFR-SA-009 / AFR-SA-041."""
    run_case("TC-049", sa_principal, it_principal, stub_iam)


def test_tc_051_positive(sa_principal, it_principal, stub_iam):
    """TC-051; source_id: CFR-SA-009 / AFR-SA-043."""
    run_case("TC-051", sa_principal, it_principal, stub_iam)


def test_tc_057_positive(sa_principal, it_principal, stub_iam):
    """TC-057; source_id: CFR-SA-011 / AFR-SA-048."""
    run_case("TC-057", sa_principal, it_principal, stub_iam)


def test_tc_063_positive(sa_principal, it_principal, stub_iam):
    """TC-063; source_id: CFR-SA-013 / AFR-SA-052."""
    run_case("TC-063", sa_principal, it_principal, stub_iam)


def test_tc_064_positive(sa_principal, it_principal, stub_iam):
    """TC-064; source_id: CFR-SA-013 / AFR-SA-053."""
    run_case("TC-064", sa_principal, it_principal, stub_iam)


def test_tc_068_positive(sa_principal, it_principal, stub_iam):
    """TC-068; source_id: CFR-SA-013 / AFR-SA-055B."""
    run_case("TC-068", sa_principal, it_principal, stub_iam)


def test_tc_080_positive(sa_principal, it_principal, stub_iam):
    """TC-080; source_id: CFR-SA-018 / AFR-SA-065A."""
    run_case("TC-080", sa_principal, it_principal, stub_iam)


def test_tc_082_positive(sa_principal, it_principal, stub_iam):
    """TC-082; source_id: CFR-SA-018 / AFR-SA-065C."""
    run_case("TC-082", sa_principal, it_principal, stub_iam)


def test_tc_094_positive(sa_principal, it_principal, stub_iam):
    """TC-094; source_id: CFR-SA-021 / AFR-SA-074A."""
    run_case("TC-094", sa_principal, it_principal, stub_iam)
