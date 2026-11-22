from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.uc._cases import run_case

pytestmark = pytest.mark.django_db


def test_tc_004_uc(sa_principal, it_principal, stub_iam):
    """TC-004; source_id: UC-SA-001 Exception E1."""
    run_case("TC-004", sa_principal, it_principal, stub_iam)


def test_tc_008_uc(sa_principal, it_principal, stub_iam):
    """TC-008; source_id: UC-SA-002 Exception E1."""
    run_case("TC-008", sa_principal, it_principal, stub_iam)


def test_tc_011_uc(sa_principal, it_principal, stub_iam):
    """TC-011; source_id: UC-SA-003 Exception E1."""
    run_case("TC-011", sa_principal, it_principal, stub_iam)


def test_tc_012_uc(sa_principal, it_principal, stub_iam):
    """TC-012; source_id: UC-SA-003 Exception E2."""
    run_case("TC-012", sa_principal, it_principal, stub_iam)


def test_tc_015_uc(sa_principal, it_principal, stub_iam):
    """TC-015; source_id: UC-SA-004 Exception E1."""
    run_case("TC-015", sa_principal, it_principal, stub_iam)


def test_tc_018_uc(sa_principal, it_principal, stub_iam):
    """TC-018; source_id: UC-SA-005 Exception E1."""
    run_case("TC-018", sa_principal, it_principal, stub_iam)


def test_tc_022_uc(sa_principal, it_principal, stub_iam):
    """TC-022; source_id: UC-SA-006 Exception E1."""
    run_case("TC-022", sa_principal, it_principal, stub_iam)


def test_tc_023_uc(sa_principal, it_principal, stub_iam):
    """TC-023; source_id: UC-SA-006 Exception E2."""
    run_case("TC-023", sa_principal, it_principal, stub_iam)


def test_tc_027_uc(sa_principal, it_principal, stub_iam):
    """TC-027; source_id: UC-SA-007 Exception E1."""
    run_case("TC-027", sa_principal, it_principal, stub_iam)


def test_tc_031_uc(sa_principal, it_principal, stub_iam):
    """TC-031; source_id: UC-SA-008 Exception E1."""
    run_case("TC-031", sa_principal, it_principal, stub_iam)


def test_tc_035_uc(sa_principal, it_principal, stub_iam):
    """TC-035; source_id: UC-SA-009 Exception E1."""
    run_case("TC-035", sa_principal, it_principal, stub_iam)


def test_tc_039_uc(sa_principal, it_principal, stub_iam):
    """TC-039; source_id: UC-SA-010 Exception E1."""
    run_case("TC-039", sa_principal, it_principal, stub_iam)


def test_tc_042_uc(sa_principal, it_principal, stub_iam):
    """TC-042; source_id: UC-SA-011 Exception E1."""
    run_case("TC-042", sa_principal, it_principal, stub_iam)


def test_tc_048_uc(sa_principal, it_principal, stub_iam):
    """TC-048; source_id: UC-SA-013 Exception E1."""
    run_case("TC-048", sa_principal, it_principal, stub_iam)


def test_tc_051_uc(sa_principal, it_principal, stub_iam):
    """TC-051; source_id: UC-SA-014 Exception E1."""
    run_case("TC-051", sa_principal, it_principal, stub_iam)


def test_tc_054_uc(sa_principal, it_principal, stub_iam):
    """TC-054; source_id: UC-SA-015 Exception E1."""
    run_case("TC-054", sa_principal, it_principal, stub_iam)


def test_tc_058_uc(sa_principal, it_principal, stub_iam):
    """TC-058; source_id: UC-SA-016 Exception E1."""
    run_case("TC-058", sa_principal, it_principal, stub_iam)


def test_tc_062_uc(sa_principal, it_principal, stub_iam):
    """TC-062; source_id: UC-SA-017 Exception E1."""
    run_case("TC-062", sa_principal, it_principal, stub_iam)


def test_tc_065_uc(sa_principal, it_principal, stub_iam):
    """TC-065; source_id: UC-SA-018 Exception E1."""
    run_case("TC-065", sa_principal, it_principal, stub_iam)


def test_tc_066_uc(sa_principal, it_principal, stub_iam):
    """TC-066; source_id: UC-SA-018 Exception E2."""
    run_case("TC-066", sa_principal, it_principal, stub_iam)


def test_tc_069_uc(sa_principal, it_principal, stub_iam):
    """TC-069; source_id: UC-SA-019 Exception E1."""
    run_case("TC-069", sa_principal, it_principal, stub_iam)


def test_tc_072_uc(sa_principal, it_principal, stub_iam):
    """TC-072; source_id: UC-SA-020 Exception E1."""
    run_case("TC-072", sa_principal, it_principal, stub_iam)


def test_tc_075_uc(sa_principal, it_principal, stub_iam):
    """TC-075; source_id: UC-SA-021 Exception E1."""
    run_case("TC-075", sa_principal, it_principal, stub_iam)


def test_tc_078_uc(sa_principal, it_principal, stub_iam):
    """TC-078; source_id: UC-SA-022 Exception E1."""
    run_case("TC-078", sa_principal, it_principal, stub_iam)


def test_tc_081_uc(sa_principal, it_principal, stub_iam):
    """TC-081; source_id: UC-SA-023 Exception E1."""
    run_case("TC-081", sa_principal, it_principal, stub_iam)


def test_tc_087_uc(sa_principal, it_principal, stub_iam):
    """TC-087; source_id: UC-SA-025 Exception E1."""
    run_case("TC-087", sa_principal, it_principal, stub_iam)


def test_tc_093_uc(sa_principal, it_principal, stub_iam):
    """TC-093; source_id: UC-SA-027 Exception E1."""
    run_case("TC-093", sa_principal, it_principal, stub_iam)


def test_tc_094_uc(sa_principal, it_principal, stub_iam):
    """TC-094; source_id: UC-SA-027 Exception E2."""
    run_case("TC-094", sa_principal, it_principal, stub_iam)


def test_tc_097_uc(sa_principal, it_principal, stub_iam):
    """TC-097; source_id: UC-SA-028 Exception E1."""
    run_case("TC-097", sa_principal, it_principal, stub_iam)


def test_tc_113_uc(sa_principal, it_principal, stub_iam):
    """TC-113; source_id: UC-SA-033 Exception E1."""
    run_case("TC-113", sa_principal, it_principal, stub_iam)


def test_tc_114_uc(sa_principal, it_principal, stub_iam):
    """TC-114; source_id: UC-SA-033 Exception E2."""
    run_case("TC-114", sa_principal, it_principal, stub_iam)


