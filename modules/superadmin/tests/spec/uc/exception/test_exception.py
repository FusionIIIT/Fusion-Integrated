from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.uc._cases import run_case

pytestmark = pytest.mark.django_db


def test_tc_005_uc(sa_principal, it_principal, stub_iam):
    """TC-005; source_id: UC-SA-001 Exception E2."""
    run_case("TC-005", sa_principal, it_principal, stub_iam)


def test_tc_024_uc(sa_principal, it_principal, stub_iam):
    """TC-024; source_id: UC-SA-006 Exception E3."""
    run_case("TC-024", sa_principal, it_principal, stub_iam)


def test_tc_045_uc(sa_principal, it_principal, stub_iam):
    """TC-045; source_id: UC-SA-012 Exception E1."""
    run_case("TC-045", sa_principal, it_principal, stub_iam)


def test_tc_055_uc(sa_principal, it_principal, stub_iam):
    """TC-055; source_id: UC-SA-015 Exception E2."""
    run_case("TC-055", sa_principal, it_principal, stub_iam)


def test_tc_059_uc(sa_principal, it_principal, stub_iam):
    """TC-059; source_id: UC-SA-016 Exception E2."""
    run_case("TC-059", sa_principal, it_principal, stub_iam)


def test_tc_084_uc(sa_principal, it_principal, stub_iam):
    """TC-084; source_id: UC-SA-024 Exception E1."""
    run_case("TC-084", sa_principal, it_principal, stub_iam)


def test_tc_090_uc(sa_principal, it_principal, stub_iam):
    """TC-090; source_id: UC-SA-026 Exception E1."""
    run_case("TC-090", sa_principal, it_principal, stub_iam)


def test_tc_100_uc(sa_principal, it_principal, stub_iam):
    """TC-100; source_id: UC-SA-029 Exception E1."""
    run_case("TC-100", sa_principal, it_principal, stub_iam)


def test_tc_103_uc(sa_principal, it_principal, stub_iam):
    """TC-103; source_id: UC-SA-030 Exception E1."""
    run_case("TC-103", sa_principal, it_principal, stub_iam)


def test_tc_106_uc(sa_principal, it_principal, stub_iam):
    """TC-106; source_id: UC-SA-031 Exception E1."""
    run_case("TC-106", sa_principal, it_principal, stub_iam)


def test_tc_109_uc(sa_principal, it_principal, stub_iam):
    """TC-109; source_id: UC-SA-032 Exception E1."""
    run_case("TC-109", sa_principal, it_principal, stub_iam)


def test_tc_117_uc(sa_principal, it_principal, stub_iam):
    """TC-117; source_id: UC-SA-034 Exception E1."""
    run_case("TC-117", sa_principal, it_principal, stub_iam)


