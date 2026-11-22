from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.fr.conftest import run_case

pytestmark = pytest.mark.django_db


def test_tc_010_notification(sa_principal, it_principal, stub_iam):
    """TC-010; source_id: CFR-SA-001 / AFR-SA-009."""
    run_case("TC-010", sa_principal, it_principal, stub_iam)


def test_tc_023_notification(sa_principal, it_principal, stub_iam):
    """TC-023; source_id: CFR-SA-004 / AFR-SA-020."""
    run_case("TC-023", sa_principal, it_principal, stub_iam)


def test_tc_032_notification(sa_principal, it_principal, stub_iam):
    """TC-032; source_id: CFR-SA-006 / AFR-SA-029."""
    run_case("TC-032", sa_principal, it_principal, stub_iam)


def test_tc_038_notification(sa_principal, it_principal, stub_iam):
    """TC-038; source_id: CFR-SA-007 / AFR-SA-035A."""
    run_case("TC-038", sa_principal, it_principal, stub_iam)


def test_tc_045_notification(sa_principal, it_principal, stub_iam):
    """TC-045; source_id: CFR-SA-008 / AFR-SA-039C."""
    run_case("TC-045", sa_principal, it_principal, stub_iam)


def test_tc_050_notification(sa_principal, it_principal, stub_iam):
    """TC-050; source_id: CFR-SA-009 / AFR-SA-042."""
    run_case("TC-050", sa_principal, it_principal, stub_iam)


def test_tc_052_notification(sa_principal, it_principal, stub_iam):
    """TC-052; source_id: CFR-SA-009 / AFR-SA-044A."""
    run_case("TC-052", sa_principal, it_principal, stub_iam)


def test_tc_053_notification(sa_principal, it_principal, stub_iam):
    """TC-053; source_id: CFR-SA-009 / AFR-SA-044B."""
    run_case("TC-053", sa_principal, it_principal, stub_iam)


def test_tc_085_notification(sa_principal, it_principal, stub_iam):
    """TC-085; source_id: CFR-SA-019 / AFR-SA-068."""
    run_case("TC-085", sa_principal, it_principal, stub_iam)


def test_tc_086_notification(sa_principal, it_principal, stub_iam):
    """TC-086; source_id: CFR-SA-019 / AFR-SA-069."""
    run_case("TC-086", sa_principal, it_principal, stub_iam)


def test_tc_087_notification(sa_principal, it_principal, stub_iam):
    """TC-087; source_id: CFR-SA-019 / AFR-SA-070."""
    run_case("TC-087", sa_principal, it_principal, stub_iam)


def test_tc_088_notification(sa_principal, it_principal, stub_iam):
    """TC-088; source_id: CFR-SA-019 / AFR-SA-071A."""
    run_case("TC-088", sa_principal, it_principal, stub_iam)


def test_tc_089_notification(sa_principal, it_principal, stub_iam):
    """TC-089; source_id: CFR-SA-019 / AFR-SA-071B."""
    run_case("TC-089", sa_principal, it_principal, stub_iam)


def test_tc_098_notification(sa_principal, it_principal, stub_iam):
    """TC-098; source_id: CFR-SA-023 / AFR-SA-076."""
    run_case("TC-098", sa_principal, it_principal, stub_iam)
