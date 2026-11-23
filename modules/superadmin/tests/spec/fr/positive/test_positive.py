from __future__ import annotations

import pytest

from modules.superadmin.tests.spec.fr.conftest import run_case

pytestmark = pytest.mark.django_db




























def test_tc_057_positive(sa_principal, it_principal, stub_iam):
    """TC-057; source_id: CFR-SA-011 / AFR-SA-048."""
    run_case("TC-057", sa_principal, it_principal, stub_iam)


def test_tc_063_positive(sa_principal, it_principal, stub_iam):
    """TC-063; source_id: CFR-SA-013 / AFR-SA-052."""
    run_case("TC-063", sa_principal, it_principal, stub_iam)
