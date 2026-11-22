from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.fr.conftest import run_case

pytestmark = pytest.mark.django_db









def test_tc_097_validation(sa_principal, it_principal, stub_iam):
    """TC-097; source_id: CFR-SA-020 / AFR-SA-075."""
    run_case("TC-097", sa_principal, it_principal, stub_iam)


def test_tc_099_validation(sa_principal, it_principal, stub_iam):
    """TC-099; source_id: CFR-SA-023 / AFR-SA-077."""
    run_case("TC-099", sa_principal, it_principal, stub_iam)


def test_tc_100_validation(sa_principal, it_principal, stub_iam):
    """TC-100; source_id: CFR-SA-004 / AFR-SA-078."""
    run_case("TC-100", sa_principal, it_principal, stub_iam)
